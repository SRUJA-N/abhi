from __future__ import annotations

import datetime as dt

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from events.models import Attendance, BudgetHistory, Event, EventFeedback, EventRegistration, Student


class Command(BaseCommand):
    help = "Seed demo students + events/budget/attendance for local SQLite runs."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        # Ensure demo users exist (created by seed_base_users, but keep this idempotent)
        users = {
            "admin_demo": None,
            "faculty_demo": None,
            "viewer_demo": None,
        }
        for username in users.keys():
            users[username] = (
                User.objects.filter(username=username).first()
                or User.objects.create(
                    username=username,
                    email=f"{username}@bit.local",
                    role=User.Role.ADMIN
                    if username == "admin_demo"
                    else (User.Role.VIEWER if username == "viewer_demo" else User.Role.FACULTY),
                    is_staff=username == "admin_demo",
                    is_active=True,
                )
            )

        admin = users["admin_demo"]
        faculty = users["faculty_demo"]
        viewer = users["viewer_demo"]

        # Students (from init.sql: 1BIT21CS001..120)
        # To keep this maintainable, generate programmatically.
        students = []
        for i in range(1, 121):
            usn = f"1BIT21CS{i:03d}"
            students.append(
                Student(
                    usn=usn,
                    name=f"Student {i:03d}",
                    semester=(3 + (i % 3)),  # cycles 3,4,5
                )
            )

        Student.objects.bulk_create(students, ignore_conflicts=True)

        def d(date_iso: str) -> dt.date:
            return dt.date.fromisoformat(date_iso)

        seed_events = [
            # (title, slug, event_type, venue, expected_participants, seat_limit, college_fund, sponsorship, status, event_date, approved)
            ("IoT Orientation Booth", "seed-2024-01-iot", "IOT", "IoT Lab", 28, 35, 1500, 500, "APPROVED", "2024-02-18", True),
            ("Blockchain Basics Talk", "seed-2024-02-blockchain", "BLOCKCHAIN", "Seminar Hall A", 45, 50, 2000, 500, "APPROVED", "2024-04-06", True),
            ("Cyber Hygiene Clinic", "seed-2024-03-cyber", "CYBER", "Lab B-204", 60, 70, 3000, 1000, "APPROVED", "2024-06-12", True),
            ("IoT Sensors Mini Hacknight", "seed-2024-04-iot", "IOT", "IoT Lab", 55, 60, 5000, 1500, "PENDING", "2024-08-24", False),
            ("Crypto Policy Debate", "seed-2024-05-blockchain", "BLOCKCHAIN", "Seminar Hall B", 50, 55, 8000, 2000, "REJECTED", "2024-10-03", False),
            ("Industrial IoT Demo Day", "seed-2025-06-iot", "IOT", "Main Auditorium", 90, 110, 10000, 3000, "APPROVED", "2025-01-21", True),
            ("Smart Contracts Studio", "seed-2025-07-blockchain", "BLOCKCHAIN", "Incubation Center", 70, 75, 15000, 5000, "APPROVED", "2025-03-09", True),
            ("Blue Team Workshop", "seed-2025-08-cyber", "CYBER", "Lab B-204", 110, 120, 22000, 8000, "APPROVED", "2025-05-17", True),
            ("Threat Hunting Sprint", "seed-2025-09-cyber", "CYBER", "Cyber Range", 105, 115, 30000, 10000, "PENDING", "2025-07-08", False),
            ("Blockchain Career Fair", "seed-2025-10-blockchain", "BLOCKCHAIN", "Open Arena", 220, 250, 45000, 55000, "APPROVED", "2025-09-30", True),
            ("Edge AI + IoT Symposium", "seed-2026-11-iot", "IOT", "Auditorium", 210, 240, 65000, 35000, "APPROVED", "2026-02-14", True),
            ("Post-Quantum Readiness", "seed-2026-12-cyber", "CYBER", "Seminar Hall B", 95, 100, 12000, 4000, "APPROVED", "2026-04-28", True),
            ("DeFi Risk Lab", "seed-2026-13-blockchain", "BLOCKCHAIN", "Lab C-105", 70, 75, 8000, 2500, "PENDING", "2026-06-06", False),
            ("Campus IoT Telemetry", "seed-2026-14-iot", "IOT", "IoT Innovation Lab", 65, 70, 5000, 1500, "APPROVED", "2026-08-19", True),
            ("SOC Automation Day", "seed-2026-15-cyber", "CYBER", "Cyber Range", 85, 90, 10000, 6000, "APPROVED", "2026-10-11", True),
        ]

        # Cleanup (idempotent reseed)
        Attendance.objects.filter(event__slug__startswith="seed-").delete()
        BudgetHistory.objects.filter(event__slug__startswith="seed-").delete()
        EventRegistration.objects.filter(event__slug__startswith="seed-").delete()
        EventFeedback.objects.filter(event__slug__startswith="seed-").delete()
        Event.objects.filter(slug__startswith="seed-").delete()

        now = timezone.now()

        for idx, (title, slug, etype, venue, expected, seat_limit, college_fund, sponsorship, status, event_date, approved) in enumerate(seed_events):
            attendance_token = ""
            rejected_reason = ""

            if status == "APPROVED":
                attendance_token = f"{idx+1:02d}{2024+idx:04d}abcdef0123456789".replace("2024", str(2024+idx))
                approved_at = now
                created_by = faculty
                approved_by = admin
            else:
                attendance_token = "" if status in {"PENDING", "REJECTED"} else ""
                approved_at = None
                created_by = faculty
                approved_by = None

            if status == "REJECTED":
                rejected_reason = "Not aligned with semester plan"

            # Match init.sql pattern: token like 012024..., 022024..., etc.
            # Use a deterministic token for each seed event.
            # Reconstruct the same tokens prefixing by sequence.
            token_suffix = "abcdef0123456789"
            token_prefix_year = 2024 if slug.startswith("seed-2024") else (2025 if slug.startswith("seed-2025") else 2026)
            seq = idx + 1
            attendance_token = f"{seq:02d}{token_prefix_year}{token_suffix}"

            ev = Event.objects.create(
                title=title,
                slug=slug,
                event_type=etype,
                venue=venue,
                expected_participants=expected,
                seat_limit=seat_limit,
                college_fund=college_fund,
                sponsorship=sponsorship,
                status=status,
                event_date=d(event_date),
                description="Synthetic departmental seed row",
                created_by=created_by,
                approved_by=approved_by,
                approved_at=approved_at,
                rejected_reason=rejected_reason,
                attendance_token=attendance_token if status == "APPROVED" else "",
            )

            if status == "APPROVED":
                BudgetHistory.objects.create(
                    event=ev,
                    college_fund=ev.college_fund,
                    sponsorship=ev.sponsorship,
                    note="Seed snapshot",
                )

        # Sample attendance: first three students on first approved seed event
        first_approved = (
            Event.objects.filter(slug__startswith="seed-", status=Event.Status.APPROVED)
            .order_by("event_date")
            .first()
        )
        if first_approved:
            seed_usn = ["1BIT21CS001", "1BIT21CS002", "1BIT21CS003"]
            qs = Student.objects.filter(usn__in=seed_usn)
            student_map = {s.usn: s for s in qs}
            for usn in seed_usn:
                EventRegistration.objects.get_or_create(
                    event=first_approved,
                    student=student_map[usn],
                    defaults={"registered_at": now},
                )
                Attendance.objects.get_or_create(
                    event=first_approved,
                    student=student_map[usn],
                    defaults={"registered_at": now},
                )

            EventFeedback.objects.get_or_create(
                event=first_approved,
                user=viewer,
                defaults={"rating": 5, "comment": "Well organized and useful for students."},
            )

        self.stdout.write(self.style.SUCCESS("Seeded demo students + events (SQLite)."))


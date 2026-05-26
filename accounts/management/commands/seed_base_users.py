from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create demo department accounts used by init.sql (idempotent)."

    def handle(self, *args, **options) -> None:
        demos = [
            ("admin_demo", User.Role.ADMIN, True, True),
            ("faculty_demo", User.Role.FACULTY, False, True),
            ("coordinator_demo", User.Role.STUDENT_COORDINATOR, False, True),
            ("viewer_demo", User.Role.VIEWER, False, True),
        ]
        password = "demo12345"
        for username, role, is_staff, is_active in demos:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@bit.local",
                    "role": role,
                    "is_staff": is_staff,
                    "is_active": is_active,
                },
            )
            # Avoid expensive password hashing on every rerun.
            # Only set password when it isn't already correct.
            if created or not user.check_password(password):
                user.set_password(password)
                # keep password predictable for local demos
                user.role = role
                user.is_staff = is_staff
                user.is_active = is_active
                user.save()
                msg = "Created" if created else "Updated password"
                self.stdout.write(self.style.SUCCESS(f"{msg} {username}"))
            else:
                # Idempotent: update RBAC flags if needed, but don't re-hash.
                user.role = role
                user.is_staff = is_staff
                user.is_active = is_active
                user.save()
                self.stdout.write(self.style.WARNING(f"Verified {username}"))


        self.stdout.write(self.style.SUCCESS("Demo password for all accounts: demo12345"))

"""Shared approval/rejection logic (MySQL-backed via Django ORM)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import BudgetHistory, Event


def approve_event(event: Event, approver) -> None:
    with transaction.atomic():
        event.status = Event.Status.APPROVED
        event.approved_by = approver
        event.approved_at = timezone.now()
        event.rejected_reason = ""
        event.assign_attendance_token_if_missing()
        event.save()
        BudgetHistory.objects.create(
            event=event,
            college_fund=event.college_fund,
            sponsorship=event.sponsorship,
            note="Snapshot on approval",
        )


def reject_event(event: Event, *, reason: str) -> None:
    if not (reason or "").strip():
        raise ValueError("Rejection requires a non-empty reason.")
    with transaction.atomic():
        event.status = Event.Status.REJECTED
        event.approved_by = None
        event.approved_at = None
        event.attendance_token = ""
        event.rejected_reason = reason.strip()
        event.save()

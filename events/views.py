from __future__ import annotations

import io
from typing import Any

import json
import qrcode
from django.db.models import Avg, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import User

from .analytics_sql import fetch_budget_variance_rows, student_usn_exists_raw
from .certificates import build_certificate_pdf
from .approval_workflow import approve_event, reject_event
from .decorators import ADMIN, APPROVAL_QUEUE_ROLES, COORD, CREATOR_ROLES, FACULTY, VIEWER, role_required
from .forms import EventFeedbackForm, EventForm, EventRegistrationForm, PredictForm, ScanForm
from .models import Attendance, Event, EventFeedback, EventMedia, EventRegistration, Student
from .predictor import predict_future_cost, train_from_events
from .views_media import (
    event_media_delete,
    event_media_download,
    event_media_list,
    event_media_upload,
)



def _visible_events_queryset(user: User):
    qs = Event.objects.select_related("created_by", "approved_by")
    if user.role == VIEWER:
        return qs.filter(status=Event.Status.APPROVED)
    return qs


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    variance_rows = fetch_budget_variance_rows()
    totals = {"college": 0.0, "sponsor": 0.0}
    for row in variance_rows:
        totals["college"] += float(row.get("college_fund") or 0)
        totals["sponsor"] += float(row.get("sponsorship") or 0)

    events = _visible_events_queryset(user)[:12]
    approved_events = Event.objects.filter(status=Event.Status.APPROVED)
    all_events = Event.objects.all()
    user_events = all_events.filter(created_by=user)
    registration_totals = EventRegistration.objects.filter(event__status=Event.Status.APPROVED).count()
    attendance_totals = Attendance.objects.filter(event__status=Event.Status.APPROVED).count()
    media_totals = EventMedia.objects.count()
    user_totals = User.objects.count()
    student_totals = Student.objects.count()
    feedback_avg = EventFeedback.objects.filter(event__status=Event.Status.APPROVED).aggregate(avg=Avg("rating"))["avg"]
    upcoming_slots = 0
    for event in approved_events.filter(event_date__gte=timezone.localdate()):
        if event.seat_limit:
            upcoming_slots += event.seats_available or 0
    pending_count = (
        Event.objects.filter(status=Event.Status.PENDING).count()
        if user.role in APPROVAL_QUEUE_ROLES
        else 0
    )
    approval_counts = {}
    if user.role in APPROVAL_QUEUE_ROLES:
        approval_counts = {
            "approved": Event.objects.filter(status=Event.Status.APPROVED).count(),
            "pending": pending_count,
            "rejected": Event.objects.filter(status=Event.Status.REJECTED).count(),
        }
    event_counts = {
        "total": all_events.count(),
        "approved": approved_events.count(),
        "pending": Event.objects.filter(status=Event.Status.PENDING).count(),
        "rejected": Event.objects.filter(status=Event.Status.REJECTED).count(),
        "mine": user_events.count(),
        "my_pending": user_events.filter(status=Event.Status.PENDING).count(),
    }
    chart_rows = variance_rows[:12]
    chart_json = json.dumps(chart_rows, default=str)
    return render(
        request,
        "events/dashboard.html",
        {
            "variance_rows": variance_rows[:8],
            "variance_rows_json": chart_json,
            "totals": totals,
            "events": events,
            "pending_count": pending_count,
            "approval_counts": approval_counts,
            "registration_totals": registration_totals,
            "attendance_totals": attendance_totals,
            "media_totals": media_totals,
            "user_totals": user_totals,
            "student_totals": student_totals,
            "feedback_avg": feedback_avg,
            "upcoming_slots": upcoming_slots,
            "event_counts": event_counts,
        },
    )


@login_required
def event_list(request: HttpRequest) -> HttpResponse:
    events = _visible_events_queryset(request.user)
    return render(request, "events/event_list.html", {"events": events})


@login_required
@role_required(*CREATOR_ROLES)
def event_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = EventForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Event submitted for administrative approval.")
            return redirect("events:event_list")
    else:
        form = EventForm(user=request.user)
    return render(request, "events/event_form.html", {"form": form, "title": "Create Event"})


@login_required
def event_detail(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(
        Event.objects.select_related("created_by", "approved_by").prefetch_related(
            "attendance_rows__student",
            "registration_rows__student",
            "feedback_rows__user",
        ),
        pk=pk,
    )
    if request.user.role == VIEWER and event.status != Event.Status.APPROVED:
        raise Http404()
    attendance_count = event.attendance_rows.count()
    registration_count = event.registration_rows.count()
    feedback_stats = event.feedback_rows.aggregate(avg=Avg("rating"), count=Count("id"))
    user_feedback = None
    if request.user.is_authenticated:
        user_feedback = event.feedback_rows.filter(user=request.user).first()
    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "attendance_count": attendance_count,
            "registration_count": registration_count,
            "registration_form": EventRegistrationForm(),
            "feedback_form": EventFeedbackForm(),
            "feedback_stats": feedback_stats,
            "user_feedback": user_feedback,
            "scan_url": request.build_absolute_uri(reverse("events:scan_public", args=[event.pk]))
            + f"?t={event.attendance_token}"
            if event.can_issue_qr
            else "",
        },
    )


@login_required
@require_http_methods(["POST"])
def event_register(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk, status=Event.Status.APPROVED)
    if event.event_date < timezone.localdate():
        messages.error(request, "Registration is closed for completed events.")
        return redirect("events:event_detail", pk=event.pk)
    form = EventRegistrationForm(request.POST)
    if form.is_valid():
        exists, student_id = student_usn_exists_raw(form.cleaned_data["usn"])
        if not exists or student_id is None:
            messages.error(request, "USN not found in CSE-ICB student registry.")
        elif not event.has_registration_slots:
            messages.error(request, "Registration is full for this event.")
        else:
            student = Student.objects.get(pk=student_id)
            _, created = EventRegistration.objects.get_or_create(event=event, student=student)
            if created:
                messages.success(request, f"Registered {student.usn}. Slots update is live.")
            else:
                messages.info(request, "This student is already registered for the event.")
    return redirect("events:event_detail", pk=event.pk)


@login_required
@require_http_methods(["POST"])
def event_feedback(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk, status=Event.Status.APPROVED)
    if request.user.role != VIEWER:
        messages.error(request, "Viewer accounts can submit event feedback.")
        return redirect("events:event_detail", pk=event.pk)
    if not event.is_completed:
        messages.error(request, "Feedback opens after the event is completed.")
        return redirect("events:event_detail", pk=event.pk)
    form = EventFeedbackForm(request.POST)
    if form.is_valid():
        feedback, created = EventFeedback.objects.get_or_create(
            event=event,
            user=request.user,
            defaults={
                "rating": int(form.cleaned_data["rating"]),
                "comment": form.cleaned_data["comment"],
            },
        )
        if created:
            messages.success(request, "Thanks for rating this event.")
        else:
            feedback.rating = int(form.cleaned_data["rating"])
            feedback.comment = form.cleaned_data["comment"]
            feedback.save(update_fields=["rating", "comment"])
            messages.success(request, "Your feedback has been updated.")
    return redirect("events:event_detail", pk=event.pk)


@login_required
@role_required(*CREATOR_ROLES)
def event_edit(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk)
    if event.is_locked:
        messages.error(request, "Approved events are locked and cannot be edited.")
        return redirect("events:event_detail", pk=pk)
    if request.user.role in (FACULTY, COORD) and event.created_by_id != request.user.id:
        raise Http404()
    if request.method == "POST":
        form = EventForm(request.POST, instance=event, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated.")
            return redirect("events:event_detail", pk=event.pk)
    else:
        form = EventForm(instance=event, user=request.user)
    return render(request, "events/event_form.html", {"form": form, "title": "Edit Event", "event": event})


@login_required
@role_required(*APPROVAL_QUEUE_ROLES)
def admin_queue(request: HttpRequest) -> HttpResponse:
    events = Event.objects.select_related("created_by", "approved_by").order_by("-event_date", "-id")
    can_decide = request.user.role == ADMIN
    status_counts = {
        "approved": Event.objects.filter(status=Event.Status.APPROVED).count(),
        "pending": Event.objects.filter(status=Event.Status.PENDING).count(),
        "rejected": Event.objects.filter(status=Event.Status.REJECTED).count(),
    }
    return render(
        request,
        "events/admin_queue.html",
        {"events": events, "can_decide": can_decide, "status_counts": status_counts},
    )


@login_required
@role_required(ADMIN)
@require_http_methods(["POST"])
def admin_decide(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk)
    action = request.POST.get("action")
    reason = (request.POST.get("rejected_reason") or "").strip()
    if action not in {"approve", "reject"}:
        messages.error(request, "Unknown decision.")
        return redirect("events_admin_approvals")
    try:
        if action == "approve":
            approve_event(event, request.user)
            messages.success(request, "Event approved and locked for budgeting.")
        else:
            reject_event(event, reason=reason)
            messages.warning(request, "Event rejected.")
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("events_admin_approvals")
    return redirect("events:event_detail", pk=event.pk)


@login_required
@role_required(*CREATOR_ROLES)
def event_qr(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk)
    if request.user.role in (FACULTY, COORD) and event.created_by_id != request.user.id:
        raise Http404()
    if not event.can_issue_qr:
        raise Http404()
    url = request.build_absolute_uri(reverse("events:scan_public", args=[event.pk]))
    url = f"{url}?t={event.attendance_token}"
    img = qrcode.make(url, box_size=6, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, filename=f"event-{event.pk}-qr.png")


@require_http_methods(["GET", "POST"])
def scan_public(request: HttpRequest, event_id: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=event_id)
    token = request.GET.get("t") or request.POST.get("t")
    if event.status != Event.Status.APPROVED or not event.attendance_token or token != event.attendance_token:
        return render(request, "events/scan_invalid.html", status=403)
    if request.method == "POST":
        form = ScanForm(request.POST)
        if form.is_valid():
            usn = form.cleaned_data["usn"]
            exists, student_id = student_usn_exists_raw(usn)
            if not exists or student_id is None:
                messages.error(request, "USN not found in CSE-ICB student registry.")
            else:
                student = Student.objects.get(pk=student_id)
                # Check if student is registered for this event
                is_registered = EventRegistration.objects.filter(event=event, student=student).exists()
                if not is_registered:
                    messages.error(request, "You must be registered for this event to mark attendance.")
                else:
                    att, created = Attendance.objects.get_or_create(event=event, student=student)
                    if created:
                        messages.success(request, f"Attendance recorded for {student.usn}.")
                    else:
                        messages.info(request, "Attendance already registered for this USN.")
            return redirect(f"{reverse('events:scan_public', args=[event.pk])}?t={event.attendance_token}")
    else:
        form = ScanForm()
    return render(
        request,
        "events/scan.html",
        {"form": form, "event": event, "token": event.attendance_token},
    )


@login_required
def predictor_view(request: HttpRequest) -> HttpResponse:
    model = train_from_events(Event.objects.filter(status=Event.Status.APPROVED))
    prediction: dict[str, Any] | None = None
    if request.method == "POST":
        form = PredictForm(request.POST)
        if form.is_valid():
            pred = predict_future_cost(
                model,
                event_type=form.cleaned_data["event_type"],
                expected_participants=form.cleaned_data["expected_participants"],
                venue=form.cleaned_data["venue"],
            )
            prediction = {
                "cost": round(pred.predicted_cost, 2),
                "beta0": round(pred.beta0, 4),
                "beta1": round(pred.beta1, 4),
                "beta2": round(pred.beta2, 4),
            }
    else:
        form = PredictForm()
    return render(
        request,
        "events/predictor.html",
        {"form": form, "prediction": prediction, "has_model": model is not None},
    )


@login_required
def certificate_pdf(request: HttpRequest, pk: int, usn: str) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk)
    if request.user.role == VIEWER:
        raise Http404()
    if event.status != Event.Status.APPROVED:
        raise Http404()
    exists, student_id = student_usn_exists_raw(usn)
    if not exists or student_id is None:
        raise Http404()
    student = Student.objects.get(pk=student_id)
    if not Attendance.objects.filter(event=event, student=student).exists():
        messages.error(request, "Certificate available only after QR attendance is recorded.")
        return redirect("events:event_detail", pk=pk)
    pdf_bytes = build_certificate_pdf(
        student_name=student.name,
        usn=student.usn,
        event_title=event.title,
        event_date=event.event_date.isoformat(),
    )
    filename = f"certificate-{student.usn}-{event.pk}.pdf"
    return FileResponse(io.BytesIO(pdf_bytes), as_attachment=True, filename=filename)


def health(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")

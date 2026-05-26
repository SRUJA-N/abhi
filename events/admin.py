from django.contrib import admin, messages

from accounts.models import User

from .approval_workflow import approve_event, reject_event
from .models import Attendance, BudgetHistory, Event, EventFeedback, EventRegistration, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    search_fields = ("usn", "name")
    list_display = ("usn", "name", "semester")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "status", "event_date", "seat_limit", "college_fund", "sponsorship", "created_by")
    list_filter = ("status", "event_type")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    actions = ("approve_pending_events", "reject_pending_events")

    @admin.action(description="Approve selected PENDING events (ADMIN role only)")
    def approve_pending_events(self, request, queryset):
        if getattr(request.user, "role", None) != User.Role.ADMIN:
            self.message_user(
                request,
                "Only department administrators (role ADMIN) may approve events.",
                level=messages.ERROR,
            )
            return
        pending = queryset.filter(status=Event.Status.PENDING)
        count = 0
        for event in pending:
            approve_event(event, request.user)
            count += 1
        self.message_user(request, f"Approved {count} pending event(s).")

    @admin.action(description="Reject selected PENDING events (ADMIN role only; audit note auto-filled)")
    def reject_pending_events(self, request, queryset):
        if getattr(request.user, "role", None) != User.Role.ADMIN:
            self.message_user(
                request,
                "Only department administrators (role ADMIN) may reject events.",
                level=messages.ERROR,
            )
            return
        pending = queryset.filter(status=Event.Status.PENDING)
        count = 0
        for event in pending:
            reject_event(event, reason="Rejected via Django Admin bulk action.")
            count += 1
        self.message_user(request, f"Rejected {count} pending event(s).")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("event", "student", "registered_at")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "student", "registered_at")
    search_fields = ("event__title", "student__usn", "student__name")


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "rating", "submitted_at")
    list_filter = ("rating",)
    search_fields = ("event__title", "user__username", "comment")


@admin.register(BudgetHistory)
class BudgetHistoryAdmin(admin.ModelAdmin):
    list_display = ("event", "recorded_at", "college_fund", "sponsorship")

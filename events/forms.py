from __future__ import annotations

from django import forms
from django.utils.text import slugify

from accounts.models import User

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "event_type",
            "venue",
            "expected_participants",
            "seat_limit",
            "college_fund",
            "sponsorship",
            "event_date",
            "description",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "cyber-input"}),
            "event_type": forms.Select(attrs={"class": "cyber-input"}),
            "venue": forms.TextInput(attrs={"class": "cyber-input"}),
            "expected_participants": forms.NumberInput(attrs={"class": "cyber-input"}),
            "seat_limit": forms.NumberInput(attrs={"class": "cyber-input", "min": 0}),
            "college_fund": forms.NumberInput(attrs={"class": "cyber-input"}),
            "sponsorship": forms.NumberInput(attrs={"class": "cyber-input"}),
            "event_date": forms.DateInput(attrs={"class": "cyber-input", "type": "date"}),
            "description": forms.Textarea(attrs={"class": "cyber-input", "rows": 4}),
        }

    def __init__(self, *args, user: User, **kwargs) -> None:
        self.user = user
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.is_locked:
            for name in ("college_fund", "sponsorship", "expected_participants", "seat_limit", "venue", "event_type"):
                if name in self.fields:
                    self.fields[name].disabled = True

    def save(self, commit: bool = True) -> Event:  # type: ignore[override]
        obj: Event = super().save(commit=False)
        if not obj.pk:
            base = slugify(obj.title)[:200] or "event"
            obj.slug = f"{base}-{self.user.id}"
            # ensure uniqueness cheaply for demo
            while Event.objects.filter(slug=obj.slug).exists():
                from uuid import uuid4

                obj.slug = f"{base}-{uuid4().hex[:8]}"
            obj.created_by = self.user
            obj.status = Event.Status.PENDING
            obj.approved_by = None
            obj.approved_at = None
            obj.attendance_token = ""
        if commit:
            obj.save()
        return obj


class ScanForm(forms.Form):
    usn = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"class": "cyber-input", "placeholder": "USN"}))


class EventRegistrationForm(forms.Form):
    usn = forms.CharField(
        label="Student USN",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "cyber-input", "placeholder": "1BIT21CS001"}),
    )


class EventFeedbackForm(forms.Form):
    rating = forms.ChoiceField(
        choices=[(str(i), f"{i} / 5") for i in range(5, 0, -1)],
        widget=forms.Select(attrs={"class": "cyber-input"}),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "cyber-input", "rows": 3, "placeholder": "Optional feedback"}),
    )


class PredictForm(forms.Form):
    event_type = forms.ChoiceField(choices=Event.EventType.choices, widget=forms.Select(attrs={"class": "cyber-input"}))
    expected_participants = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": "cyber-input"}))
    venue = forms.CharField(widget=forms.TextInput(attrs={"class": "cyber-input"}))


class EventMediaUploadForm(forms.Form):
    # multiple upload handled via request.FILES.getlist('files')
    files = forms.FileField(widget=forms.ClearableFileInput())



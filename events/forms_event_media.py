from __future__ import annotations

from django import forms


class EventMediaUploadForm(forms.Form):
    files = forms.FileField(widget=forms.ClearableFileInput(attrs={"multiple": True}))

    # (We infer type from upload; UI can remain simple.)


from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .decorators import ADMIN, COORD, FACULTY, role_required, VIEWER
from .models import Event, EventMedia


def _can_manage_media(role: str) -> bool:
    return role in {ADMIN, FACULTY, COORD}


@login_required
@require_http_methods(["POST"])
def event_media_upload(request: HttpRequest, pk: int) -> HttpResponse:
    if not _can_manage_media(request.user.role):
        raise Http404()

    event = get_object_or_404(Event, pk=pk)

    # allow multiple files in one request
    uploaded_files = request.FILES.getlist("files")
    if not uploaded_files:
        messages.error(request, "No files selected.")
        return redirect("events:event_detail", pk=event.pk)

    for f in uploaded_files:
        guess, _ = mimetypes.guess_type(f.name)
        guess = guess or ""
        if guess.startswith("image/"):
            file_type = EventMedia.MediaType.PHOTO
        elif guess.startswith("video/"):
            file_type = EventMedia.MediaType.VIDEO
        else:
            file_type = EventMedia.MediaType.DOCUMENT

        EventMedia.objects.create(
            event=event,
            uploaded_by=request.user,
            file_name=f.name,
            file_type=file_type,
            file_path=f,
        )

    messages.success(request, "Media uploaded.")
    return redirect("events:event_detail", pk=event.pk)


@login_required
def event_media_list(request: HttpRequest, pk: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk)
    can_manage = _can_manage_media(request.user.role)
    media_rows = event.media_rows.all()
    return render(
        request,
        "events/event_media_list.html",
        {
            "event": event,
            "media_rows": media_rows,
            "can_manage": can_manage,
        },
    )


@login_required
def event_media_download(request: HttpRequest, pk: int, media_id: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=pk)
    if request.user.role == VIEWER:
        # Viewer can view/download only.
        pass

    media = get_object_or_404(EventMedia, pk=media_id, event=event)
    if not media.file_path:
        raise Http404()

    # Serve via FileResponse; file is stored in MEDIA_ROOT under file_path.
    path = Path(media.file_path.path)
    if not path.exists():
        raise Http404()

    return FileResponse(open(path, "rb"), as_attachment=True, filename=media.file_name)


@login_required
@require_http_methods(["POST"])
def event_media_delete(request: HttpRequest, pk: int, media_id: int) -> HttpResponse:
    if not _can_manage_media(request.user.role):
        raise Http404()

    event = get_object_or_404(Event, pk=pk)
    media = get_object_or_404(EventMedia, pk=media_id, event=event)
    media.delete()
    messages.success(request, "Media deleted.")
    return redirect("events:event_detail", pk=event.pk)


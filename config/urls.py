from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from events import views as event_views

urlpatterns = [
    # Must be registered *before* ``admin/`` so they are not swallowed by ``admin.site.urls``.
    path("admin/approvals/", event_views.admin_queue, name="events_admin_approvals"),
    path("admin/events/<int:pk>/decide/", event_views.admin_decide, name="events_admin_decide"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("", include("events.urls", namespace="events")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

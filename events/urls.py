from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("health/", views.health, name="health"),
    path("events/", views.event_list, name="event_list"),
    path("events/create/", views.event_create, name="event_create"),
    path("events/<int:pk>/", views.event_detail, name="event_detail"),
    path("events/<int:pk>/register/", views.event_register, name="event_register"),
    path("events/<int:pk>/feedback/", views.event_feedback, name="event_feedback"),
    path("events/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("events/<int:pk>/media/", views.event_media_list, name="event_media_list"),
    path("events/<int:pk>/media/upload/", views.event_media_upload, name="event_media_upload"),
    path("events/<int:pk>/media/<int:media_id>/download/", views.event_media_download, name="event_media_download"),
    path("events/<int:pk>/media/<int:media_id>/delete/", views.event_media_delete, name="event_media_delete"),
    path("events/<int:pk>/qr.png", views.event_qr, name="event_qr"),
    path("events/<int:pk>/certificate/<str:usn>/", views.certificate_pdf, name="certificate"),
    path("events/<int:pk>/export/attendance/", views.export_attendance, name="export_attendance"),
    path("events/<int:pk>/export/registrations/", views.export_registrations, name="export_registrations"),
    path("predictor/", views.predictor_view, name="predictor"),
    path("scan/<int:event_id>/", views.scan_public, name="scan_public"),
]

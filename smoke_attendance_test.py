from django.test import Client

from events.models import Attendance, Event

event = Event.objects.filter(status="APPROVED").order_by("-event_date").first()
client = Client()
before = Attendance.objects.filter(event=event, student__usn="1BIT21CS005").count()
url = f"/scan/{event.pk}/?t={event.attendance_token}"
r1 = client.post(url, {"t": event.attendance_token, "usn": "1BIT21CS005"})
r2 = client.post(url, {"t": event.attendance_token, "usn": "1BIT21CS005"})
after = Attendance.objects.filter(event=event, student__usn="1BIT21CS005").count()
print({"statuses": (r1.status_code, r2.status_code), "attendance": (before, after)})

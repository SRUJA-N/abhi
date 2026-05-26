"""
PDF certificate generation using ReportLab with a placeholder HOD signature image.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def _ensure_placeholder_signature(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (520, 160), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 510, 150], outline=(16, 185, 129, 255), width=3)
    draw.text((24, 60), "HOD Digital Signature (Placeholder)", fill=(148, 163, 184, 255))
    img.save(path, format="PNG")


def build_certificate_pdf(*, student_name: str, usn: str, event_title: str, event_date: str) -> bytes:
    media_root = Path(settings.MEDIA_ROOT)
    sig_path = media_root / "assets" / "hod_signature_placeholder.png"
    _ensure_placeholder_signature(sig_path)

    buffer = BytesIO()
    page = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=page)
    width, height = page

    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setFillColorRGB(0.06, 0.73, 0.51)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 3.2 * cm, "BMS Institute of Technology — CSE-ICB")

    pdf.setFillColorRGB(0.23, 0.51, 0.96)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(width / 2, height - 4.6 * cm, "Certificate of Participation")

    pdf.setFillColorRGB(0.86, 0.89, 0.94)
    pdf.setFont("Helvetica", 14)
    body = (
        f"This is to certify that {student_name} ({usn}) successfully participated in "
        f"the departmental technical event titled “{event_title}” held on {event_date}."
    )
    text_obj = pdf.beginText(3 * cm, height - 7 * cm)
    text_obj.setFont("Helvetica", 14)
    for line in _wrap_lines(body, 92):
        text_obj.textLine(line)
    pdf.drawText(text_obj)

    pdf.drawImage(
        str(sig_path),
        width - 9.5 * cm,
        2.2 * cm,
        width=7 * cm,
        height=2 * cm,
        mask="auto",
    )
    pdf.setFillColorRGB(0.71, 0.76, 0.84)
    pdf.setFont("Helvetica-Oblique", 11)
    pdf.drawRightString(width - 2.5 * cm, 1.6 * cm, "Head of Department — CSE-ICB")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _wrap_lines(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = (" ".join(cur + [w])) if cur else w
        if len(trial) <= width:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

"""
Analytics helpers executed with ``connection.cursor()`` as required.
"""
from __future__ import annotations

from typing import Any

from django.db import connection


def fetch_budget_variance_rows() -> list[dict[str, Any]]:
    """
    Raw SQL dashboard: compare College Fund vs Sponsorship and compute variance metrics.

    Variance is calculated in Python as:
    abs(college_fund - sponsorship) / college_fund * 100
    """
    sql = """
        SELECT
            e.id AS event_id,
            e.title,
            e.event_date,
            e.status,
            e.college_fund,
            e.sponsorship,
            (e.college_fund + e.sponsorship) AS total_budget,
            ABS(e.college_fund - e.sponsorship) AS absolute_variance
        FROM cse_icb_events e
        WHERE e.status = 'APPROVED'
        ORDER BY e.event_date DESC, e.id DESC
        LIMIT 200;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        rows = []
        for record in cursor.fetchall():
            item = dict(zip(cols, record))
            for key in ("college_fund", "sponsorship", "total_budget", "absolute_variance", "variance_pct"):
                if key in item and item[key] is not None and not isinstance(item[key], (int, float)):
                    item[key] = float(item[key])
            college_amount = float(item.get("college_fund") or 0)
            sponsor_amount = float(item.get("sponsorship") or 0)
            variance = (
                abs(college_amount - sponsor_amount) / college_amount * 100
                if college_amount
                else 0.0
            )
            item["variance_pct"] = round(variance, 1)
            item["variance_pct_display"] = f"{item['variance_pct']:.1f}%"
            rows.append(item)
    return rows


def student_usn_exists_raw(usn: str) -> tuple[bool, int | None]:
    """
    Attendance validation: check Student master via raw SQL before QR registration.
    Returns (exists, student_id).
    """
    normalized = usn.strip().upper()
    sql = "SELECT id FROM cse_icb_students WHERE usn = %s LIMIT 1;"
    with connection.cursor() as cursor:
        cursor.execute(sql, [normalized])
        row = cursor.fetchone()
    if not row:
        return False, None
    return True, int(row[0])

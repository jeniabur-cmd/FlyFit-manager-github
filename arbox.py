"""אינטגרציה עם Arbox API v3: שליפת לוח שיעורים וסנכרון לטבלת arbox_classes.

מבוסס על התיעוד הרשמי (https://arboxserver.arboxapp.com/docs/api#/operations/Get%20Schedule):
GET https://arboxserver.arboxapp.com/api/public/v3/schedule, אימות בכותרת api-key.
כל שגיאת API (מפתח לא תקין, שירות לא זמין) נבלעת בשקט ב-maybe_sync_schedule -
האפליקציה ממשיכה לעבוד עם המשימות הרגילות גם בלי לוח שיעורים מעודכן.
"""
from datetime import datetime, timedelta

import httpx
import streamlit as st

import db

API_BASE = "https://arboxserver.arboxapp.com/api/public/v3"
SYNC_INTERVAL = timedelta(hours=1)
SCHEDULE_DAYS_AHEAD = 30
PAGE_LIMIT = 500


def _api_key() -> str | None:
    return st.secrets.get("ARBOX_API_KEY")


def fetch_schedule(from_date: str, to_date: str) -> list[dict]:
    """שולף מ-Arbox את כל השיעורים בטווח התאריכים (Y-m-d), כולל דפדוף."""
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("ARBOX_API_KEY לא מוגדר ב-secrets")

    headers = {"Accept": "application/json", "api-key": api_key}
    all_rows: list[dict] = []
    page = 1
    with httpx.Client(base_url=API_BASE, headers=headers, timeout=20) as client:
        while True:
            resp = client.get(
                "/schedule",
                params={
                    "from_date": from_date,
                    "to_date": to_date,
                    "limit": PAGE_LIMIT,
                    "page": page,
                    "registration_count": "1",
                    "sort": "asc",
                },
            )
            resp.raise_for_status()
            rows = (resp.json() or {}).get("data") or []
            all_rows.extend(rows)
            if len(rows) < PAGE_LIMIT:
                break
            page += 1
    return all_rows


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _staff_name(value) -> str | None:
    """staff_member/second_staff_member אמורים להיות מחרוזת לפי התיעוד, אבל
    בפועל Arbox מחזיר לעיתים אובייקט {user_id, phone, email, name} (למשל
    עבור הזמנות ניסיון). לוקחים רק את השם ולעולם לא את הטלפון/האימייל, כדי
    שלא לדלוף פרטי לקוח לעמודת instructor_name."""
    if isinstance(value, dict):
        return value.get("name")
    return value


def _map_row(row: dict) -> dict:
    return {
        "arbox_id": str(row.get("schedule_id")),
        "date": row.get("date"),
        "time": row.get("start_time"),
        "class_type": row.get("session_name"),
        "instructor_name": _staff_name(row.get("staff_member")),
        "capacity": _to_int(row.get("max_participants")),
        "booked_count": _to_int(row.get("registration_count")),
        "synced_at": datetime.now(db.TZ).isoformat(),
    }


def sync_schedule(days_ahead: int = SCHEDULE_DAYS_AHEAD) -> int:
    """שולף מ-Arbox ומבצע upsert (לפי arbox_id+date) לטבלת arbox_classes.
    לא מוחק שורות קיימות - רק מוסיף/מעדכן, כך שנשמרת היסטוריית תפוסה.
    מחזיר את מספר השורות שנשלחו לעדכון."""
    today = datetime.now(db.TZ).date()
    from_date = today.isoformat()
    to_date = (today + timedelta(days=days_ahead)).isoformat()

    raw_rows = fetch_schedule(from_date, to_date)
    rows = [_map_row(r) for r in raw_rows if r.get("schedule_id") and r.get("date")]
    if not rows:
        return 0

    db.get_client().table("arbox_classes").upsert(rows, on_conflict="arbox_id,date").execute()
    return len(rows)


def last_synced_at() -> datetime | None:
    res = (
        db.get_client()
        .table("arbox_classes")
        .select("synced_at")
        .order("synced_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return datetime.fromisoformat(res.data[0]["synced_at"])


def maybe_sync_schedule() -> None:
    """מריץ סנכרון אוטומטי אם עברה יותר משעה מאז הסנכרון האחרון (או שמעולם
    לא בוצע). לקרוא בראש כל טעינת עמוד. בולע כל שגיאה (מפתח חסר/לא תקין,
    טבלה שעוד לא נוצרה, שירות לא זמין) כדי שהאפליקציה תמשיך לעבוד כרגיל."""
    if not _api_key():
        return
    try:
        last = last_synced_at()
        if last and datetime.now(db.TZ) - last < SYNC_INTERVAL:
            return
        sync_schedule()
    except Exception:
        pass


def get_classes_for_date(date: str) -> list[dict]:
    return (
        db.get_client()
        .table("arbox_classes")
        .select("*")
        .eq("date", date)
        .order("time")
        .execute()
        .data
    )


def get_classes_between(date_from: str, date_to: str) -> list[dict]:
    return (
        db.get_client()
        .table("arbox_classes")
        .select("*")
        .gte("date", date_from)
        .lte("date", date_to)
        .order("date")
        .order("time")
        .execute()
        .data
    )

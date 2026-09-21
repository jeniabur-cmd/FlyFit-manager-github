"""גישה ליומנים ב-Google Calendar (אישי + סטודיו) דרך Service Account (נבדק
ועובד - ראו scripts/test_google_calendar.py). פרטי ההזדהות נקראים אך ורק
ממשתנה הסביבה GCP_SERVICE_ACCOUNT_JSON (מחרוזת JSON עם כל שדות ה-Service
Account, בשורה אחת) - אותו מקור מקומית (.env) ובענן (env vars של הפלטפורמה),
כך שאין שני נתיבים שונים לתחזק. תוכנם לעולם לא מודפס/נשמר במקום אחר.

הפונקציות כאן מעלות חריגה בכשל (env var חסר, אין הרשאה, בעיית רשת) - הבליעה
וההודעה הידידותית על "מקור נתונים לא זמין" מתבצעות מרוכז ב-advisor.py, כדי
שאפשר יהיה להציג בממשק אילו מקורות התנוונו.
"""
import json
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

from . import db
from .config import env, ttl_cache

PERSONAL_CALENDAR_ID = "jeniabur@gmail.com"
STUDIO_CALENDAR_ID = "flyfit03@gmail.com"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@ttl_cache()
def _get_service():
    raw = env("GCP_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError(
            "חסר משתנה הסביבה GCP_SERVICE_ACCOUNT_JSON (מקומית: .env, בענן: "
            "הגדרות משתני הסביבה של הפלטפורמה)."
        )
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_events(calendar_id: str, date_from: str, date_to: str) -> list[dict]:
    """מחזיר אירועים מיומן נתון בטווח התאריכים, בפורמט
    [{"start": iso-str, "end": iso-str, "summary": str}]. מעלה חריגה בכשל."""
    service = _get_service()
    # date_from/date_to הם תאריכים לפי שעון ישראל (Asia/Jerusalem) - חייבים
    # להיות מתויגים כך, לא כ-UTC, אחרת חצות/סוף-יום מקומיים זזים בשעתיים-שלוש
    # (הפרש UTC+2/+3) והחלון בפועל מפספס אירועים מוקדמים ב-date_from.
    time_min = datetime.fromisoformat(date_from).replace(tzinfo=db.TZ).isoformat()
    time_max = datetime.fromisoformat(date_to).replace(
        hour=23, minute=59, second=59, tzinfo=db.TZ
    ).isoformat()
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
        )
        .execute()
    )
    return [
        {
            "start": ev["start"].get("dateTime", ev["start"].get("date")),
            "end": ev["end"].get("dateTime", ev["end"].get("date")),
            "summary": ev.get("summary", "(ללא כותרת)"),
        }
        for ev in result.get("items", [])
    ]


def get_personal_events(date_from: str, date_to: str) -> list[dict]:
    return get_events(PERSONAL_CALENDAR_ID, date_from, date_to)


def get_studio_events(date_from: str, date_to: str) -> list[dict]:
    return get_events(STUDIO_CALENDAR_ID, date_from, date_to)

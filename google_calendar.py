"""גישה ליומנים ב-Google Calendar (אישי + סטודיו) דרך Service Account (נבדק
ועובד - ראו scripts/test_google_calendar.py). פרטי ההזדהות נקראים אך ורק
מ-st.secrets["gcp_service_account"] - אותו מקור מקומית (.streamlit/secrets.toml)
ובענן (Streamlit Cloud secrets), כך שאין שני נתיבים שונים לתחזק. תוכנם לעולם
לא מודפס/נשמר במקום אחר.

הפונקציות כאן מעלות חריגה בכשל (secrets חסר, אין הרשאה, בעיית רשת) - הבליעה
וההודעה הידידותית על "מקור נתונים לא זמין" מתבצעות מרוכז ב-advisor.py, כדי
שאפשר יהיה להציג בממשק אילו מקורות התנוונו.
"""
from datetime import datetime, timezone

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

PERSONAL_CALENDAR_ID = "jeniabur@gmail.com"
STUDIO_CALENDAR_ID = "flyfit03@gmail.com"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@st.cache_resource
def _get_service():
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError('חסר בלוק [gcp_service_account] ב-secrets (מקומית: .streamlit/secrets.toml, בענן: Streamlit Cloud secrets).')
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_events(calendar_id: str, date_from: str, date_to: str) -> list[dict]:
    """מחזיר אירועים מיומן נתון בטווח התאריכים, בפורמט
    [{"start": iso-str, "end": iso-str, "summary": str}]. מעלה חריגה בכשל."""
    service = _get_service()
    time_min = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc).isoformat()
    time_max = datetime.fromisoformat(date_to).replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc
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

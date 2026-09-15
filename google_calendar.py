"""גישה ליומן ה-Google Calendar של הסטודיו דרך Service Account (נבדק ועובד -
ראו scripts/test_google_calendar.py). פרטי ההזדהות נקראים אך ורק מהקובץ
.streamlit/gcp_service_account.json - תוכנו לעולם לא מודפס/נשמר במקום אחר.

היומן האישי (jeniabur@gmail.com) לא משותף עם ה-Service Account בכוונה ולכן
אינו נתמך כאן. כל שגיאה (קובץ חסר, אין הרשאה, בעיית רשת) נבלעת ומוחזרת
כרשימה ריקה, כדי שהיועץ ימשיך לעבוד גם בלי נתון זה.
"""
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

STUDIO_CALENDAR_ID = "flyfit03@gmail.com"
SERVICE_ACCOUNT_FILE = Path(__file__).resolve().parent / ".streamlit" / "gcp_service_account.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@st.cache_resource
def _get_service():
    if not SERVICE_ACCOUNT_FILE.exists():
        return None
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_studio_events(date_from: str, date_to: str) -> list[dict]:
    """מחזיר אירועים מיומן הסטודיו בטווח התאריכים, בפורמט
    [{"start": iso-str, "end": iso-str, "summary": str}]. מחזיר [] בכל כשל."""
    try:
        service = _get_service()
        if service is None:
            return []
        time_min = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc).isoformat()
        time_max = datetime.fromisoformat(date_to).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        ).isoformat()
        result = (
            service.events()
            .list(
                calendarId=STUDIO_CALENDAR_ID,
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
    except Exception:
        return []

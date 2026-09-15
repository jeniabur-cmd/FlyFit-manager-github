"""בדיקת גישה ל-Google Calendar API דרך Service Account: שולף את 5 האירועים
הקרובים מהיומן האישי ומיומן הסטודיו, כדי לוודא שהחיבור והשיתוף מוגדרים נכון
לפני שבונים עליו את הצ'אטבוט.

פרטי ה-Service Account נקראים אך ורק מהקובץ .streamlit/gcp_service_account.json
(לא מ-secrets.toml, ולא מוזנים בקוד) - הקובץ מכיל מפתח פרטי ותוכנו לעולם לא
מודפס.

הרצה: python scripts/test_google_calendar.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SERVICE_ACCOUNT_FILE = Path(__file__).resolve().parent.parent / ".streamlit" / "gcp_service_account.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

CALENDARS = {
    "אישי (jeniabur@gmail.com)": "jeniabur@gmail.com",
    "סטודיו (flyfit03@gmail.com)": "flyfit03@gmail.com",
}


def get_service():
    if not SERVICE_ACCOUNT_FILE.exists():
        raise RuntimeError(
            f"קובץ ה-Service Account לא נמצא ב-{SERVICE_ACCOUNT_FILE}. "
            "שמרו שם את קובץ ה-JSON שהורדתם מ-Google Cloud Console."
        )
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def list_upcoming_events(service, calendar_id: str, max_results: int = 5) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def describe_http_error(calendar_id: str, error: HttpError) -> str:
    status = error.resp.status if error.resp else None
    if status == 404:
        return (
            f'יומן "{calendar_id}" לא נמצא (404 Not Found). Google Calendar '
            "מחזיר 404 גם כשה-Calendar ID נכון אבל היומן פשוט לא שותף עם "
            "ה-Service Account בכלל (כדי לא לחשוף קיום של יומנים פרטיים). בדקו "
            "שתיים: (1) שיתפתם את היומן הזה עם כתובת ה-Service Account (שדה "
            "client_email בקובץ ה-JSON), (2) שה-Calendar ID מדויק (בהגדרות "
            "היומן -> Integrate calendar -> Calendar ID)."
        )
    if status in (401, 403):
        return (
            f'אין הרשאה ליומן "{calendar_id}" ({status}). ודאו שהיומן שותף עם '
            "כתובת ה-Service Account (שדה client_email בקובץ ה-JSON) עם לפחות "
            'הרשאת "לראות את כל פרטי האירוע", דרך Google Calendar -> הגדרות '
            "היומן הזה -> שיתוף עם אנשים ספציפיים."
        )
    return f'שגיאה ביומן "{calendar_id}": HTTP {status} - {error}'


def main() -> int:
    try:
        service = get_service()
    except Exception as e:
        print(f"שגיאה באתחול החיבור ל-Google Calendar API: {e}", file=sys.stderr)
        return 1

    exit_code = 0
    for label, calendar_id in CALENDARS.items():
        print(f"\n--- {label} ---")
        try:
            events = list_upcoming_events(service, calendar_id)
        except HttpError as e:
            print(describe_http_error(calendar_id, e), file=sys.stderr)
            exit_code = 1
            continue
        except Exception as e:
            print(
                f'שגיאה לא צפויה ביומן "{calendar_id}": {type(e).__name__}: {e}',
                file=sys.stderr,
            )
            exit_code = 1
            continue

        if not events:
            print("אין אירועים קרובים ביומן זה.")
            continue

        for ev in events:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            print(f"- {ev.get('summary', '(ללא כותרת)')} | {start}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

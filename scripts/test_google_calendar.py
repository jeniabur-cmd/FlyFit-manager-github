"""בדיקת גישה ל-Google Calendar API דרך Service Account: שולף עד אירוע אחד
מהיומן האישי ומיומן הסטודיו, ומדפיס לכל יומן בנפרד הצלחה/כישלון ברור, כדי
לוודא שהחיבור והשיתוף מוגדרים נכון לפני שבונים עליו את הצ'אטבוט.

פרטי ה-Service Account נקראים אך ורק מ-st.secrets["gcp_service_account"] - אותו
מקור בדיוק שממנו google_calendar.py קורא אותם (מקומית: .streamlit/secrets.toml,
בענן: Streamlit Cloud secrets), כדי שהבדיקה תשקף את הנתיב האמיתי. תוכנם לעולם
לא מודפס.

הרצה: python scripts/test_google_calendar.py
"""
import sys
from datetime import datetime, timezone

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# זהים בכוונה לקבועים PERSONAL_CALENDAR_ID / STUDIO_CALENDAR_ID ב-google_calendar.py
# (שם הם קבועים בקוד, לא נקראים מ-st.secrets - אין אפשרות להחלפה/טעות-הקלדה דרך secrets).
CALENDARS = {
    "אישי (jeniabur@gmail.com)": "jeniabur@gmail.com",
    "סטודיו (flyfit03@gmail.com)": "flyfit03@gmail.com",
}


def get_service():
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            'חסר בלוק [gcp_service_account] ב-secrets. מקומית: הוסיפו אותו ל-'
            ".streamlit/secrets.toml. בענן: הגדירו אותו תחת Settings -> Secrets "
            "באפליקציה ב-Streamlit Cloud."
        )
    info = dict(st.secrets["gcp_service_account"])
    client_email = info.get("client_email", "(לא נמצא שדה client_email ב-secrets)")
    print(f"client_email שנטען מ-st.secrets['gcp_service_account']: {client_email}")

    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    # לא משתמשים ב-st.cache_resource כאן בכוונה - זהו סקריפט חד-פעמי, לא ריצת
    # Streamlit, כדי לוודא שאין שום קאש חוצץ בין ריצה לריצה בבדיקה הזו.
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def list_upcoming_events(service, calendar_id: str, max_results: int = 1) -> list[dict]:
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
            "client_email ב-secrets), (2) שה-Calendar ID מדויק (בהגדרות "
            "היומן -> Integrate calendar -> Calendar ID)."
        )
    if status in (401, 403):
        return (
            f'אין הרשאה ליומן "{calendar_id}" ({status}). ודאו שהיומן שותף עם '
            "כתובת ה-Service Account (שדה client_email ב-secrets) עם לפחות "
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
        print(f"Calendar ID שנשלח בבקשה: {calendar_id!r}")
        try:
            events = list_upcoming_events(service, calendar_id)
        except HttpError as e:
            print(f"❌ נכשל: {describe_http_error(calendar_id, e)}")
            print(f"   שגיאה מלאה: HTTP {e.resp.status if e.resp else '?'} - {e.content!r}")
            exit_code = 1
            continue
        except Exception as e:
            print(f"❌ נכשל: שגיאה לא צפויה ({type(e).__name__}): {e}")
            exit_code = 1
            continue

        print(f"✅ הצלחה: החיבור ליומן \"{calendar_id}\" עובד, נמצאו {len(events)} אירוע/ים קרוב/ים.")
        for ev in events:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            print(f"  - {ev.get('summary', '(ללא כותרת)')} | {start}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

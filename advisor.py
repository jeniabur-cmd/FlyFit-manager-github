"""עוזר תכנון מבוסס OpenAI: אוסף חלון נתונים מתגלגל (ברירת מחדל 90 יום קדימה)
מכל המקורות - משימות, לוח שיעורים מ-Arbox, שני יומני Google (אישי + סטודיו),
וחגים משלושת הדתות - ובונה מהם system prompt לכל פנייה בצ'אט. כל מקור נתפס
בנפרד: כשל באחד (שגיאת רשת, הרשאה, קובץ חסר) לא מפיל את השאר, רק מצטרף
לרשימת "מקורות לא זמינים" שהעמוד מציג כהערה לא-חוסמת.

אם OPENAI_API_KEY לא מוגדר, is_configured() מחזיר False והעמוד לא מציג צ'אט.
"""
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    _log_stream = sys.stderr
    if hasattr(_log_stream, "reconfigure"):
        _log_stream.reconfigure(encoding="utf-8")  # אחרת עברית בלוג יוצאת כ-\uXXXX בקונסולת Windows
    _handler = logging.StreamHandler(_log_stream)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

import arbox
import db
import google_calendar
import religious_calendar

MODEL = "gpt-4o-mini"  # מודל זול ומהיר, מספיק ליכולות ניתוח/סיכום טקסט כאן
CONTEXT_DAYS_AHEAD = 90
NOTES_FILE = Path(__file__).resolve().parent / "DATA" / "mydates.docx"


def is_configured() -> bool:
    return bool(st.secrets.get("OPENAI_API_KEY"))


@st.cache_resource
def _client() -> OpenAI:
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def _read_studio_notes() -> str:
    if not NOTES_FILE.exists():
        return ""
    try:
        import docx

        doc = docx.Document(str(NOTES_FILE))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines)
    except Exception:
        return ""


def _safe(label: str, fn, *args):
    try:
        return fn(*args), None
    except Exception as e:
        return None, f"{label}: {type(e).__name__}: {e}"


# מוצג למודל כשמקור נתונים נכשל בשליפה - חייב להיות שונה בבירור מ"(אין ...
# בטווח)" (שמשמעו נשלף בהצלחה ופשוט ריק), אחרת המודל עלול לפרש כשל שקט כאילו
# היומן/הטבלה באמת ריקים, ולומר בטעות "אין לך שום דבר מתוזמן".
_FETCH_FAILED = "(שגיאה בשליפה - המקור הזה לא היה זמין הפעם, אין להניח שהוא ריק)"


def _format_tasks(tasks: list[dict] | None, err: str | None) -> str:
    if err:
        return _FETCH_FAILED
    if not tasks:
        return "(אין משימות בטווח)"
    lines = []
    for t in tasks:
        status = "בוצע" if t.get("completed") else "פתוח"
        time_part = f" {str(t['scheduled_time'])[:5]}" if t.get("scheduled_time") else ""
        lines.append(f"- {t['scheduled_date']}{time_part}: {t['title']} ({status})")
    return "\n".join(lines)


def _format_arbox(classes: list[dict] | None, err: str | None) -> str:
    if err:
        return _FETCH_FAILED
    if not classes:
        return "(אין שיעורי Arbox בטווח)"
    lines = []
    for c in classes:
        time_part = f" {str(c['time'])[:5]}" if c.get("time") else ""
        occ = ""
        if c.get("capacity") is not None and c.get("booked_count") is not None:
            occ = f" ({c['booked_count']}/{c['capacity']})"
        instructor = f" עם {c['instructor_name']}" if c.get("instructor_name") else ""
        lines.append(f"- {c['date']}{time_part}: {c.get('class_type') or 'שיעור'}{instructor}{occ}")
    return "\n".join(lines)


def _format_events(events: list[dict] | None, err: str | None) -> str:
    if err:
        return _FETCH_FAILED
    if not events:
        return "(אין אירועים בטווח)"
    return "\n".join(f"- {e['start']}: {e['summary']}" for e in events)


def _format_holidays(holidays_list: list[dict]) -> str:
    if not holidays_list:
        return "(אין חגים בטווח)"
    return "\n".join(f"- {h['date']}: {h['name']} ({h['religion']})" for h in holidays_list)


@st.cache_data(ttl=3600, show_spinner=False)
def _gather_context(date_from: str, date_to: str) -> tuple[str, list[str]]:
    """אוסף מכל המקורות, כל אחד בנפרד כדי שכשל אחד לא יפיל את השאר.
    מוחזר ומטמון ל-שעה (ttl) - אין טעם לתשאל את כל המקורות בכל הודעת צ'אט."""
    tasks, tasks_err = _safe("משימות", db.get_tasks, date_from, date_to)
    arbox_classes, arbox_err = _safe("שיעורי Arbox", arbox.get_classes_between, date_from, date_to)
    personal_events, personal_err = _safe(
        "יומן Google אישי", google_calendar.get_personal_events, date_from, date_to
    )
    studio_events, studio_err = _safe(
        "יומן Google של הסטודיו", google_calendar.get_studio_events, date_from, date_to
    )
    all_holidays, holidays_degraded = religious_calendar.get_all_holidays(date_from, date_to)

    notes = _read_studio_notes()
    notes_block = (
        f"\n\nהערות קבועות שבעלת הסטודיו תיעדה מראש (חשוב להתייחס אליהן):\n{notes}"
        if notes
        else ""
    )

    now = datetime.now(db.TZ)
    system_prompt = (
        "את/ה עוזר/ת תכנון ולו\"ז לסטודיו כושר אווירי בשם FlyFit. עונה בעברית, "
        "תמציתי וממוקד.\n\n"
        "יש לך גישה אמיתית ומעודכנת (נשלפה ממש עכשיו, ברגע הזה, לפני כתיבת "
        "ההודעה הזו) לנתוני הלו\"ז שלמטה: משימות הסטודיו מה-DB, לוח שיעורי "
        "Arbox, יומן Google האישי, יומן Google של הסטודיו, וחגים. זו אינה "
        "ידיעה כללית או ניחוש - אלו הנתונים בפועל, ואת/ה אמור/ה להתייחס אליהם "
        "כאילו יש לך גישה חיה ליומנים ולמשימות, כי יש לך. לעולם אל תגיד/י "
        "שאין לך גישה ליומן Google או למשימות - יש לך, והנתונים למטה הם היא. "
        "אם קטע מסוים ריק (למשל \"(אין אירועים בטווח)\") המשמעות היא שאין "
        "בו אירועים בטווח שנבדק, ולא שאין לך גישה אליו - חשוב להבחין בין השניים "
        "כשעונים על שאלה כמו \"יש לך גישה ליומן שלי?\".\n\n"
        "מתבסס/ת אך ורק על הנתונים שסופקו למטה - אסור להמציא פרטי לו\"ז שלא "
        "מופיעים כאן. אם פרט ספציפי לא מופיע בנתונים - יש לומר זאת במפורש "
        "(\"זה לא מופיע בנתונים שיש לי\") ולא לנחש או להמציא.\n\n"
        f"התאריך הנוכחי (עכשיו ממש): {now.strftime('%Y-%m-%d')} ({now.strftime('%A')}).\n"
        f"חלון הנתונים שנאסף: {date_from} עד {date_to}.\n\n"
        f"משימות הסטודיו:\n{_format_tasks(tasks, tasks_err)}\n\n"
        f"לוח שיעורים (Arbox):\n{_format_arbox(arbox_classes, arbox_err)}\n\n"
        f"יומן Google אישי:\n{_format_events(personal_events, personal_err)}\n\n"
        f"יומן Google של הסטודיו:\n{_format_events(studio_events, studio_err)}\n\n"
        f"חגים (יהודיים/נוצריים/מוסלמיים):\n{_format_holidays(all_holidays)}"
        f"{notes_block}"
    )

    degraded = [
        e for e in (tasks_err, arbox_err, personal_err, studio_err) if e
    ] + holidays_degraded
    return system_prompt, degraded


def clear_context_cache() -> None:
    """מנקה את מטמון _gather_context (ttl=3600) - יש לקרוא לזה אחרי שינוי
    שרלוונטי לאחד המקורות (למשל שיתוף יומן Google מחדש), כדי שלא להמתין
    לפקיעת ה-cache כדי לראות את הנתונים המעודכנים."""
    _gather_context.clear()


def chat(history: list[dict], user_message: str) -> tuple[str, list[str], str]:
    """history: הודעות עבר בפורמט {"role": "user"/"assistant", "content": str}.
    מחזיר (תשובת הטקסט הסופית, רשימת מקורות שהתנוונו בקריאה הזו, ה-system
    prompt המלא שנשלח - למטרות דיבוג/תצוגה בממשק)."""
    now = datetime.now(db.TZ)
    date_from = now.date().isoformat()
    date_to = (now.date() + timedelta(days=CONTEXT_DAYS_AHEAD)).isoformat()
    system_prompt, degraded = _gather_context(date_from, date_to)
    logger.info("advisor system prompt for this request:\n%s", system_prompt)
    if degraded:
        logger.warning("advisor degraded sources this request: %s", degraded)

    client = _client()
    messages = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_message}]
    )
    response = client.chat.completions.create(model=MODEL, messages=messages)
    reply = response.choices[0].message.content or ""
    return reply, degraded, system_prompt

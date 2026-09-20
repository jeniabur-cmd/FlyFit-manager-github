"""עוזר תכנון מבוסס OpenAI: אוסף חלון נתונים מתגלגל (ברירת מחדל 90 יום קדימה)
מכל המקורות - משימות, לוח שיעורים מ-Arbox, שני יומני Google (אישי + סטודיו),
וחגים משלושת הדתות - ובונה מהם system prompt לכל פנייה בצ'אט. כל מקור נתפס
בנפרד: כשל באחד (שגיאת רשת, הרשאה, קובץ חסר) לא מפיל את השאר, רק מצטרף
לרשימת "מקורות לא זמינים" שהעמוד מציג כהערה לא-חוסמת.

אם OPENAI_API_KEY לא מוגדר, is_configured() מחזיר False והעמוד לא מציג צ'אט.
"""
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
from openai import OpenAI

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


def _format_tasks(tasks: list[dict]) -> str:
    if not tasks:
        return "(אין משימות בטווח)"
    lines = []
    for t in tasks:
        status = "בוצע" if t.get("completed") else "פתוח"
        time_part = f" {str(t['scheduled_time'])[:5]}" if t.get("scheduled_time") else ""
        lines.append(f"- {t['scheduled_date']}{time_part}: {t['title']} ({status})")
    return "\n".join(lines)


def _format_arbox(classes: list[dict]) -> str:
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


def _format_events(events: list[dict]) -> str:
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
        "תמציתי וממוקד, ומתבסס אך ורק על הנתונים שסופקו למטה - אסור להמציא "
        "פרטי לו\"ז שלא מופיעים כאן. אם משהו לא ידוע מהנתונים - יש לומר זאת "
        "במפורש ולא לנחש.\n\n"
        f"התאריך הנוכחי: {now.strftime('%Y-%m-%d')} ({now.strftime('%A')}).\n"
        f"חלון הנתונים שנאסף: {date_from} עד {date_to}.\n\n"
        f"משימות הסטודיו:\n{_format_tasks(tasks or [])}\n\n"
        f"לוח שיעורים (Arbox):\n{_format_arbox(arbox_classes or [])}\n\n"
        f"יומן Google אישי:\n{_format_events(personal_events or [])}\n\n"
        f"יומן Google של הסטודיו:\n{_format_events(studio_events or [])}\n\n"
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


def chat(history: list[dict], user_message: str) -> tuple[str, list[str]]:
    """history: הודעות עבר בפורמט {"role": "user"/"assistant", "content": str}.
    מחזיר (תשובת הטקסט הסופית, רשימת מקורות שהתנוונו בקריאה הזו)."""
    now = datetime.now(db.TZ)
    date_from = now.date().isoformat()
    date_to = (now.date() + timedelta(days=CONTEXT_DAYS_AHEAD)).isoformat()
    system_prompt, degraded = _gather_context(date_from, date_to)

    client = _client()
    messages = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_message}]
    )
    response = client.chat.completions.create(model=MODEL, messages=messages)
    reply = response.choices[0].message.content or ""
    return reply, degraded

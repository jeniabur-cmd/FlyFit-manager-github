"""יועץ תכנון מבוסס OpenAI (function calling): עונה על שאלות תכנון ולו"ז
לסטודיו FlyFit תוך שליפת נתונים אמיתיים - משימות, לוח שיעורים מ-Arbox, יומן
הסטודיו ב-Google, וחגים - דרך כלי מאוחד אחד (get_studio_context) שה-LLM קורא
לו עם טווח התאריכים הרלוונטי לשאלה.

אם OPENAI_API_KEY לא מוגדר, is_configured() מחזיר False והעמוד לא מציג צ'אט -
שאר האפליקציה ממשיכה לעבוד רגיל.
"""
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI

import arbox
import db
import google_calendar
import religious_calendar

MODEL = "gpt-4o-mini"
MAX_TOOL_ROUNDS = 5
NOTES_FILE = Path(__file__).resolve().parent / "DATA" / "mydates.docx"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_studio_context",
            "description": (
                "מחזיר את כל מה שידוע על הסטודיו בטווח תאריכים נתון: משימות "
                "פתוחות/מתוכננות, שיעורים מלוח הזמנים של Arbox (כולל תפוסה), "
                "אירועים מיומן הסטודיו ב-Google Calendar, וחגים יהודיים/"
                "מוסלמיים/נוצריים. יש לקרוא לכלי הזה בכל פעם שנדרש מידע על "
                "תאריכים ספציפיים או טווח תאריכים כדי לתכנן משהו."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "תאריך התחלה, פורמט YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "תאריך סיום, פורמט YYYY-MM-DD"},
                },
                "required": ["date_from", "date_to"],
            },
        },
    }
]


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


def _build_system_prompt() -> str:
    now = datetime.now(db.TZ)
    notes = _read_studio_notes()
    notes_block = f"\nהערות קבועות שבעלת הסטודיו תיעדה מראש:\n{notes}\n" if notes else ""
    return (
        "את/ה יועץ/ת תכנון ולו\"ז לסטודיו כושר אווירי בשם FlyFit. עונה בעברית, "
        "תמציתי וממוקד. כשנדרש מידע על תאריכים - משימות, שיעורים, אירועי יומן "
        "או חגים - יש לקרוא לכלי get_studio_context עם טווח התאריכים הרלוונטי "
        "לפני שעונים; אסור להמציא נתוני לו\"ז שלא הגיעו מהכלי. "
        f"התאריך הנוכחי: {now.strftime('%Y-%m-%d')} ({now.strftime('%A')})."
        f"{notes_block}"
    )


def _run_tool(name: str, arguments: dict) -> dict:
    if name != "get_studio_context":
        return {"error": f"כלי לא מוכר: {name}"}

    date_from = arguments.get("date_from")
    date_to = arguments.get("date_to")
    result: dict = {}

    try:
        result["tasks"] = db.get_tasks(date_from, date_to)
    except Exception as e:
        result["tasks"] = []
        result["tasks_error"] = str(e)

    try:
        result["arbox_classes"] = arbox.get_classes_between(date_from, date_to)
    except Exception as e:
        result["arbox_classes"] = []
        result["arbox_classes_error"] = str(e)

    try:
        events = google_calendar.get_studio_events(date_from, date_to)
        result["studio_calendar_events"] = events
        if not events:
            result["studio_calendar_note"] = "יומן הסטודיו החזיר 0 אירועים או שאינו זמין כרגע"
    except Exception as e:
        result["studio_calendar_events"] = []
        result["studio_calendar_error"] = str(e)

    try:
        result["holidays"] = religious_calendar.get_holidays(date_from, date_to)
    except Exception as e:
        result["holidays"] = []
        result["holidays_error"] = str(e)

    return result


def chat(history: list[dict], user_message: str) -> str:
    """history: רשימת הודעות עבר בפורמט {"role": "user"/"assistant", "content": str}
    (בלי scaffolding של tool calls - זה נבנה מחדש כל קריאה). מחזיר את תשובת
    הטקסט הסופית של העוזר."""
    client = _client()
    messages = (
        [{"role": "system", "content": _build_system_prompt()}]
        + history
        + [{"role": "user", "content": user_message}]
    )

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or ""

        messages.append(msg.model_dump(exclude_none=True))
        for tool_call in msg.tool_calls:
            arguments = json.loads(tool_call.function.arguments or "{}")
            result = _run_tool(tool_call.function.name, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    return "מצטער/ת, לקח יותר מדי צעדים לענות על זה. אפשר לנסח מחדש או לצמצם את הטווח?"

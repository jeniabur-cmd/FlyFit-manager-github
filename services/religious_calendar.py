"""חגים לטווח תאריכים, משלושה מקורות נפרדים לפי מה שנבדק בפועל בשיחה:

- יהודיים: Hebcal REST API (hebcal.com) - ללא מפתח.
- נוצריים: Nager.Date public holidays API (date.nager.at) - ללא מפתח, דרך
  לוח החגים הדתיים של איטליה (קתולי) כמקור מייצג.
- מוסלמיים: Aladhan API (api.aladhan.com) התגלה כלא נגיש מסביבת הפיתוח (חיבור
  נתקע לגמרי, לא רק איטי) - הוחלף בבקשת המשתמש בחבילת holidays המקומית
  (ללא תלות ברשת), דרך לוח השנה הסעודי מסונן לחגי Eid בלבד.

get_jewish_holidays/get_christian_holidays/get_muslim_holidays מעלות חריגה
בכשל. get_all_holidays היא הפונקציה המשותפת שקוראת לשלושתן בנפרד (כשל באחת
לא מפיל את השאר) - זו הפונקציה שיש לייבא ולהשתמש בה בכל מקום שצריך "כל
החגים", כדי לא לשכפל את לוגיקת האיסוף/הבליעה.
"""
import datetime as dt

import holidays
import httpx

from .config import ttl_cache

HEBCAL_URL = "https://www.hebcal.com/hebcal"
NAGER_URL = "https://date.nager.at/api/v3/publicholidays"
CHRISTIAN_COUNTRY = "IT"

_MUSLIM_KEYWORDS = ("Eid", "Arafah")

# מטא-דאטה תצוגתית לכל דת - צבע וסמל לשימוש עקבי בכל מקום שמציג חגים.
RELIGION_META = {
    "jewish": {"label": "יהודי", "icon": "✡️", "color": "#2563eb"},
    "muslim": {"label": "מוסלמי", "icon": "☪️", "color": "#16a34a"},
    "christian": {"label": "נוצרי", "icon": "✝️", "color": "#dc2626"},
}


def get_jewish_holidays(date_from: str, date_to: str) -> list[dict]:
    resp = httpx.get(
        HEBCAL_URL,
        params={
            "v": "1",
            "cfg": "json",
            "maj": "on",
            "min": "on",
            "mod": "on",
            "i": "on",  # לוח חגים כפי שנהוג בישראל
            "start": date_from,
            "end": date_to,
        },
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        {"date": it["date"], "name": it.get("title", ""), "religion": "jewish"}
        for it in items
        if it.get("category") == "holiday"
    ]


def get_christian_holidays(date_from: str, date_to: str) -> list[dict]:
    start = dt.date.fromisoformat(date_from)
    end = dt.date.fromisoformat(date_to)
    results: list[dict] = []
    with httpx.Client(timeout=10) as client:
        for year in range(start.year, end.year + 1):
            resp = client.get(f"{NAGER_URL}/{year}/{CHRISTIAN_COUNTRY}")
            resp.raise_for_status()
            for item in resp.json():
                d = dt.date.fromisoformat(item["date"])
                if start <= d <= end:
                    results.append(
                        {
                            "date": item["date"],
                            "name": item.get("localName") or item.get("name"),
                            "religion": "christian",
                        }
                    )
    return results


def get_muslim_holidays(date_from: str, date_to: str) -> list[dict]:
    start = dt.date.fromisoformat(date_from)
    end = dt.date.fromisoformat(date_to)
    years = list(range(start.year, end.year + 1))
    results = []
    for date_, name in holidays.SaudiArabia(years=years).items():
        if start <= date_ <= end and any(kw in name for kw in _MUSLIM_KEYWORDS):
            results.append({"date": date_.isoformat(), "name": name, "religion": "muslim"})
    return results


@ttl_cache(ttl_seconds=3600)
def get_all_holidays(date_from: str, date_to: str) -> tuple[list[dict], list[str]]:
    """קורא לשלושת המקורות בנפרד - כשל באחד (רשת, API לא זמין) לא מונע
    מהשאר. מחזיר (חגים ממוינים לפי תאריך, רשימת תיאורי כשל למקורות שנכשלו)."""
    sources = [
        ("חגים יהודיים (Hebcal)", get_jewish_holidays),
        ("חגים נוצריים (Nager.Date)", get_christian_holidays),
        ("חגים מוסלמיים", get_muslim_holidays),
    ]
    results: list[dict] = []
    degraded: list[str] = []
    for label, fn in sources:
        try:
            results.extend(fn(date_from, date_to))
        except Exception as e:
            degraded.append(f"{label}: {type(e).__name__}: {e}")
    results.sort(key=lambda h: h["date"])
    return results, degraded

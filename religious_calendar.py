"""חגים יהודיים/מוסלמיים/נוצריים לטווח תאריכים, מבוסס על חבילת holidays
(ללא צורך במפתח API). משמש את היועץ כדי להימנע מהצעת תאריכים שמתנגשים עם חג.
"""
import datetime as dt

import holidays

# שמות באנגלית של חגי איסלאם היחידים שרלוונטיים לנו מתוך לוח השנה של
# ערב הסעודית (המנוע החישובי בחבילה זהה לכל המדינות המוסלמיות) - שאר
# הרשומות שם הן חגים אזרחיים/לאומיים שלא נוגעים לענייננו.
_MUSLIM_KEYWORDS = ("Eid", "Arafah")

# שמות חגים אזרחיים איטלקיים שיש לסנן החוצה, כדי להשאיר רק חגים נוצריים-דתיים.
_CHRISTIAN_CIVIL_NAMES = {
    "New Year's Day",
    "Liberation Day",
    "Labor Day",
    "Republic Day",
}


def _years_in_range(date_from: dt.date, date_to: dt.date) -> list[int]:
    return list(range(date_from.year, date_to.year + 1))


def get_holidays(date_from: str, date_to: str) -> list[dict]:
    """מחזיר רשימת חגים ממוינת לפי תאריך, בפורמט
    [{"date": "YYYY-MM-DD", "name": str, "religion": "jewish"|"muslim"|"christian"}]."""
    start = dt.date.fromisoformat(date_from)
    end = dt.date.fromisoformat(date_to)
    years = _years_in_range(start, end)

    results: list[dict] = []

    for date_, name in holidays.Israel(years=years).items():
        if start <= date_ <= end:
            results.append({"date": date_.isoformat(), "name": name, "religion": "jewish"})

    for date_, name in holidays.SaudiArabia(years=years).items():
        if start <= date_ <= end and any(kw in name for kw in _MUSLIM_KEYWORDS):
            results.append({"date": date_.isoformat(), "name": name, "religion": "muslim"})

    for date_, name in holidays.Italy(years=years).items():
        if start <= date_ <= end and name not in _CHRISTIAN_CIVIL_NAMES:
            results.append({"date": date_.isoformat(), "name": name, "religion": "christian"})

    results.sort(key=lambda r: r["date"])
    return results

"""טעינת משתני סביבה (.env) ותחליף קל-משקל ל-st.cache_resource/st.cache_data.

env() הוא תחליף ישיר ל-st.secrets[...]/st.secrets.get(...): קורא ממשתני
הסביבה, אחרי שה-.env נטען ל-os.environ פעם אחת (load_dotenv למטה).

ttl_cache() הוא תחליף ל-@st.cache_resource (בלי ttl_seconds - נשמר לתמיד,
בדיוק כמו singleton של Streamlit) ול-@st.cache_data(ttl=...) (עם ttl_seconds -
אותה סמנטיקה: התוצאה מחושבת מחדש רק אחרי שפג תוקפה). ל-Flask (מרובה-workers
בפרודקשן) זה מטמון בזיכרון התהליך בלבד - מספיק לשלב הזה של המעבר.
"""
import functools
import os
import time

from dotenv import load_dotenv

load_dotenv()


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def ttl_cache(ttl_seconds: float | None = None):
    """דקורטור: מטמין לפי הארגומנטים שהפונקציה נקראה איתם.
    ttl_seconds=None => לתמיד (כמו st.cache_resource).
    ttl_seconds=N => פג תוקף אחרי N שניות (כמו st.cache_data(ttl=N)).
    מוסיף .cache_clear() לניקוי ידני (כמו .clear() ב-Streamlit)."""

    def decorator(fn):
        cache: dict[tuple, tuple] = {}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            if key in cache:
                value, cached_at = cache[key]
                if ttl_seconds is None or (now - cached_at) < ttl_seconds:
                    return value
            value = fn(*args, **kwargs)
            cache[key] = (value, now)
            return value

        wrapper.cache_clear = cache.clear
        return wrapper

    return decorator

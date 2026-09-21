"""שכבת הלוגיקה העסקית - קוד פייתון טהור, בלי שום תלות ב-Streamlit.

כל מודול כאן זהה בעיקרו למקבילו שהיה בשורש הפרויקט לפני מעבר ל-Flask
(db.py, arbox.py, google_calendar.py, religious_calendar.py, advisor.py):
אותה לוגיקה בדיוק, רק ש-st.secrets הוחלף במשתני סביבה (config.py, דרך .env)
ו-st.cache_resource/st.cache_data הוחלפו ב-ttl_cache המקומי (גם ב-config.py).
"""

# FlyFit Manager

אפליקציית ניהול משימות יומיות לסטודיו FlyFit. Streamlit + Supabase (Postgres),
משתמשת יחידה, בלי מערכת התחברות.

## הרצה מקומית

1. התקנת תלויות (מומלץ בתוך סביבה וירטואלית):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. יצירת הסכימה ב-Supabase: פתחו את **SQL Editor** בפרויקט ה-Supabase שלכם
   (https://hhwtbnzltbwfchcplqwr.supabase.co) והריצו את הקובץ
   `migrations/001_init.sql`.

3. הגדרת secrets: העתיקו את `.streamlit/secrets.toml.example` ל-
   `.streamlit/secrets.toml` ומלאו את הערכים האמיתיים:

   ```toml
   SUPABASE_URL = "https://hhwtbnzltbwfchcplqwr.supabase.co"
   SUPABASE_ANON_KEY = "..."
   SUPABASE_SERVICE_ROLE_KEY = "..."
   ```

   קובץ זה לא נשלח ל-GitHub (מוגדר ב-`.gitignore`). האפליקציה משתמשת ב-
   `SUPABASE_SERVICE_ROLE_KEY` בלבד לכל קריאות ה-DB, מכיוון שהיא רצה על שרת
   Streamlit בלבד ולא חושפת את המפתח לדפדפן. בהתאם, Row Level Security כבוי
   בטבלאות (ראו סוף קובץ ה-migration).

4. הרצה:

   ```bash
   streamlit run app.py
   ```

## פריסה ל-Streamlit Community Cloud

1. ודאו שהקוד נמצא ב-GitHub (ראו למטה) וש-`.streamlit/secrets.toml` **לא**
   נכלל ב-repo.
2. בכתובת https://share.streamlit.io לחצו על **New app**, בחרו את ה-repo
   `jeniabur-cmd/FlyFit-manager-github`, branch `main`, וקובץ ראשי `app.py`.
3. לפני ההרצה הראשונה (או דרך **⚙️ Settings → Secrets** אחרי היצירה), הדביקו
   את תוכן `secrets.toml` המלא (עם הערכים האמיתיים) לתוך תיבת ה-Secrets.
4. Deploy. בכל עדכון קוד ב-branch `main` האפליקציה תתעדכן אוטומטית.

## פתרון בעיות

אם בהרצה מקומית מקבלים שגיאת `ImportError: DLL load failed ... Application
Control policy has blocked this file` (בד"כ מ-numpy) — זו הגבלת אבטחה של
Windows על קובצי DLL שהורדו לאחרונה לתוך venv חדש, ולא קשורה לקוד. פתרונות:
התקינו את התלויות בסביבת Python קיימת ומהימנה (למשל base של Anaconda) במקום
ב-venv חדש, או אשרו את הקובץ המדובר במדיניות ה-Application Control /
Smart App Control של המערכת. בפריסה ל-Streamlit Community Cloud (Linux) הבעיה
לא רלוונטית.

## מבנה הפרויקט

```
app.py                  עמוד ראשי: באנר משימות פתוחות + רשימת משימות היום
pages/1_משימות.py       כל המשימות, סינון, הוספה, עריכה, מחיקה
pages/2_לוח_שנה.py      תצוגת לוח שנה חודשי אינטראקטיבית
pages/3_תבניות.py       ניהול משימות חוזרות (templates)
db.py                   שכבת גישה ל-Supabase + לוגיקת גלגול/יצירה יומית
common.py               רכיבי UI משותפים ו-RTL CSS
migrations/001_init.sql סכימת בסיס הנתונים
```

## לוגיקה עסקית

- **גלגול משימות**: בכל טעינת עמוד, כל משימה עם `completed=false` ו-
  `scheduled_date` בעבר מתעדכנת בפועל (UPDATE) ל-`scheduled_date` = היום.
  כדי לעצור את הגלגול פשוט מוחקים את המשימה (יש כפתור מחיקה בכל שורה).
- **תבניות**: בכל טעינת עמוד, לכל תבנית פעילה נוצרת (אם עוד לא קיימת) משימה
  עם `scheduled_date` = היום, בצורה אידמפוטנטית (בדיקה לפי `template_id` +
  תאריך לפני יצירה).
- התאריך "היום" מחושב באזור הזמן `Asia/Jerusalem`, כדי שהגלגול יעבוד נכון גם
  כששרת הענן של Streamlit Cloud רץ ב-UTC.

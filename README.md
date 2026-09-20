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
   (https://hhwtbnzltbwfchcplqwr.supabase.co) והריצו את `migrations/001_init.sql`
   ולאחריו `migrations/002_arbox_classes.sql`.

3. הגדרת secrets: העתיקו את `.streamlit/secrets.toml.example` ל-
   `.streamlit/secrets.toml` ומלאו את הערכים האמיתיים:

   ```toml
   SUPABASE_URL = "https://hhwtbnzltbwfchcplqwr.supabase.co"
   SUPABASE_ANON_KEY = "..."
   SUPABASE_SERVICE_ROLE_KEY = "..."
   ARBOX_API_KEY = "..."   # אופציונלי - ראו "סנכרון לו\"ז מ-Arbox" למטה
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
common.py               רכיבי UI משותפים, RTL CSS, והפעלת תחזוקה/סנכרון בכל עמוד
arbox.py                אינטגרציה עם Arbox API - שליפת לו"ז וסנכרון ל-arbox_classes
migrations/001_init.sql סכימת בסיס הנתונים
migrations/002_arbox_classes.sql סכימת טבלת לוח השיעורים מ-Arbox
```

## סנכרון לו"ז מ-Arbox

- מבוסס על ה-API הרשמי של Arbox (v3, מפתח קבוע בכותרת `api-key`), התיעוד
  ב-https://arboxserver.arboxapp.com/docs/api (לא developers.arboxapp.com -
  דומיין זה לא קיים).
- כל טעינת עמוד מפעילה את `common.init_page`, וזו קוראת ל-
  `arbox.maybe_sync_schedule()` - אם עברה יותר משעה מאז השדה `synced_at`
  העדכני ביותר בטבלת `arbox_classes` (או שמעולם לא בוצע סנכרון), מתבצעת שליפה
  מלאה של 30 הימים הקרובים ו-upsert לטבלה. שגיאות API (מפתח לא תקין, שירות לא
  זמין, הטבלה עוד לא נוצרה) נבלעות בשקט - האפליקציה ממשיכה לעבוד רגיל עם
  המשימות בלבד.
- כפתור **"🔄 רענן לו"ז עכשיו"** בעמוד "לוח שנה" מפעיל סנכרון מיידי (ללא תלות
  בזמן שעבר).
- מפתח הייחוד ל-upsert הוא הזוג `(arbox_id, date)` ולא `arbox_id` בלבד, כי
  התיעוד של Arbox לא מבטיח ש-`schedule_id` ייחודי למופע שיעור ספציפי (הוא עשוי
  להיות מזהה של הגדרת שיעור חוזר, שחוזר על עצמו בכל שבוע). כך נשמרת השורה של
  כל תאריך בנפרד ולעולם לא נמחקת - מה שמאפשר בהמשך ניתוח תפוסה היסטורי.
- מיפוי שדות מתשובת ה-API (`session_name`→class_type, `staff_member`→
  instructor_name, `max_participants`→capacity, `registration_count`→
  booked_count) הוא הקרוב ביותר סמנטית לשמות שביקשתם; אין ב-API שדה בשם מפורש
  "סוג שיעור" - `session_name` הוא שם/כותרת השיעור כפי שמוגדר ב-Arbox.
- שימו לב: בפועל `staff_member`/`second_staff_member` מוחזרים לעיתים כאובייקט
  `{user_id, phone, email, name}` ולא כמחרוזת כמתועד (למשל בהזמנות ניסיון).
  `arbox.py` שולף מהאובייקט רק את `name` - לעולם לא טלפון/אימייל - כדי שלא
  לדלוף פרטי לקוח לעמודת `instructor_name`.

## עמוד "יועץ תכנון" (`pages/4_יועץ_תכנון.py`)

צ'אטבוט (OpenAI, מודל `gpt-4o-mini`, function calling) שעוזר בתכנון עתידי של
הסטודיו - שבועות פתוחים, מופעים, ריטריטים.

- `advisor.py` מגדיר כלי OpenAI **אחד מאוחד**, `get_studio_context(date_from,
  date_to)`, שמרכז לפי בקשת המודל: משימות (`db.get_tasks`), לוח שיעורים מ-
  Arbox (`arbox.get_classes_between`), אירועים מיומן הסטודיו ב-Google
  (`google_calendar.get_studio_events`), וחגים (`religious_calendar.
  get_holidays`). כלי מאוחד אחד עם טווח תאריכים חופשי נבחר על פני 4 כלים
  נפרדים (מורכב מדי) או context קבוע (לא מכסה שאלות על טווחים רחוקים).
- הערות קבועות מ-`DATA/mydates.docx` (ימים/תקופות חשובות לסטודיו) נכללות
  ישירות ב-system prompt בכל שיחה.
- `google_calendar.py`: גישה ליומן האישי (`jeniabur@gmail.com`) וליומן הסטודיו
  (`flyfit03@gmail.com`), דרך Service Account שפרטיו נקראים מ-
  `st.secrets["gcp_service_account"]` (זהה בין מקומי לענן - ראו
  `.streamlit/secrets.toml.example`). כל יומן רלוונטי חייב להיות משותף עם
  כתובת ה-`client_email` של ה-Service Account.
- `religious_calendar.py`: חגים יהודיים/מוסלמיים/נוצריים דרך חבילת `holidays`
  (ללא מפתח API) - `Israel()`, `SaudiArabia()` מסונן ל-Eid, `Italy()` מסונן
  לחגים דתיים.
- היסטוריית השיחה נשמרת רק ב-`st.session_state` (לא ב-DB) - מתאפסת בין
  הפעלות שרת/סשן.
- טיפול שגיאות: בלי `OPENAI_API_KEY` העמוד מציג הודעה ועוצר, בלי לקרוס; כל
  מקור נתונים בכלי המאוחד עטוף בנפרד ב-try/except כך שכשל באחד (למשל Google
  Calendar לא זמין) לא מפיל את שאר הנתונים.

## לוגיקה עסקית

- **גלגול משימות**: בכל טעינת עמוד, כל משימה עם `completed=false` ו-
  `scheduled_date` בעבר מתעדכנת בפועל (UPDATE) ל-`scheduled_date` = היום.
  כדי לעצור את הגלגול פשוט מוחקים את המשימה (יש כפתור מחיקה בכל שורה).
- **תבניות**: בכל טעינת עמוד, לכל תבנית פעילה נוצרת (אם עוד לא קיימת) משימה
  עם `scheduled_date` = היום, בצורה אידמפוטנטית (בדיקה לפי `template_id` +
  תאריך לפני יצירה).
- התאריך "היום" מחושב באזור הזמן `Asia/Jerusalem`, כדי שהגלגול יעבוד נכון גם
  כששרת הענן של Streamlit Cloud רץ ב-UTC.

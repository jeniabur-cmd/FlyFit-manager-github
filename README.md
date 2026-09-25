# FlyFit Manager

אפליקציית ניהול משימות יומיות לסטודיו FlyFit. שרת **Flask** + **Supabase**
(Postgres), משתמשת יחידה, בלי מערכת התחברות.

## הרצה מקומית

1. התקנת תלויות (מומלץ בתוך סביבה וירטואלית):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. יצירת הסכימה ב-Supabase: פתחו את **SQL Editor** בפרויקט ה-Supabase שלכם
   והריצו לפי הסדר את `migrations/001_init.sql`, `002_arbox_classes.sql`,
   `003_arbox_classes_status.sql` (או `python scripts/run_migrations.py` שמריץ
   אוטומטית כל migration חדש - דורש גם את `SUPABASE_DB_URL`, ראו למטה).

3. הגדרת משתני סביבה: העתיקו את `.env.example` ל-`.env` בשורש הפרויקט ומלאו
   ערכים אמיתיים. `.env` לא נשלח ל-GitHub (`.gitignore`), ונטען אוטומטית
   ע"י `services/config.py` (`load_dotenv()`) בעליית השרת - אין קובץ secrets
   נפרד, גם מקומית וגם בענן זהו אותו מנגנון (משתני סביבה של מערכת ההפעלה /
   הפלטפורמה).

   המשתנים בפועל (לפי `services/config.py` וקוד ה-`services/*.py`):

   | משתנה | חובה? | לשם מה |
   |---|---|---|
   | `SUPABASE_URL` | כן | חיבור ל-Supabase (`services/db.py`) |
   | `SUPABASE_SERVICE_ROLE_KEY` | כן | אותו חיבור - מפתח שרת בלבד, אף פעם לא נחשף לדפדפן |
   | `OPENAI_API_KEY` | לא (בלעדיו עמוד הבית פשוט לא מציג את הצ'אט) | עוזר התכנון (`services/advisor.py`) |
   | `ARBOX_API_KEY` | לא (בלעדיו פשוט אין לוח שיעורים מ-Arbox בלוח השנה) | סנכרון שיעורים (`services/arbox.py`) |
   | `GCP_SERVICE_ACCOUNT_JSON` | לא (בלעדיו עוזר התכנון עובד בלי אירועי Google Calendar) | Service Account ליומן Google, JSON תקין בשורה אחת (`services/google_calendar.py`) |
   | `SUPABASE_DB_URL` | רק ל-`scripts/run_migrations.py` | לא בשימוש ע"י שרת ה-Flask עצמו |
   | `PORT` | לא (ברירת מחדל 5000) | פורט ההאזנה - מוזרק אוטומטית ע"י Render בפרודקשן |

   הכל מתועד עם דוגמאות ב-`.env.example`.

4. הרצה:

   ```bash
   python app.py
   ```

   האפליקציה זמינה ב-<http://127.0.0.1:5000>.

## פריסה ל-Render

האפליקציה בפרודקשן זמינה ב-<https://flyfit-manager-github.onrender.com>.

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT` (מוגדר גם ב-
  `Procfile` שבשורש הפרויקט)
- **Branch**: `main` - כל push ל-branch הזה מפעיל deploy אוטומטי
- משתני הסביבה (הטבלה שלמעלה, חוץ מ-`SUPABASE_DB_URL`) מוגדרים תחת
  **Environment** בדשבורד של Render, לא בקובץ בתוך ה-repo

**מגבלת ה-tier החינמי**: השירות "נרדם" אחרי כ-15 דקות בלי בקשות; הבקשה
הראשונה אחרי שינה כזו לוקחת כ-30-60 שניות (cold start) עד שהשרת עולה מחדש.

## פתרון בעיות

אם בהרצה מקומית מקבלים שגיאת `ImportError: DLL load failed ... Application
Control policy has blocked this file` (בד"כ מ-numpy) — זו הגבלת אבטחה של
Windows על קובצי DLL שהורדו לאחרונה לתוך venv חדש, ולא קשורה לקוד. פתרונות:
התקינו את התלויות בסביבת Python קיימת ומהימנה (למשל base של Anaconda) במקום
ב-venv חדש, או אשרו את הקובץ המדובר במדיניות ה-Application Control /
Smart App Control של המערכת. בפריסה ל-Render (Linux) הבעיה לא רלוונטית.

## מבנה הפרויקט

```
app.py                          שרת Flask: routes לדפים (/,‏ /tasks,‏ /task-templates)
                                 ול-API (/api/...) שה-JS קורא אליהם עם fetch
services/db.py                  גישה ל-Supabase + לוגיקת גלגול משימות/יצירה מתבניות
services/arbox.py               אינטגרציה עם Arbox API - שליפת לו"ז וסנכרון ל-arbox_classes
services/advisor.py             עוזר תכנון (OpenAI) - איסוף context ובניית system prompt
services/google_calendar.py     גישה ליומני Google (Service Account)
services/religious_calendar.py  חגים יהודיים/נוצריים/מוסלמיים לצ'אט העוזר
services/config.py              טעינת .env ומטמון קל-משקל (תחליף ל-st.cache_*)
templates/base.html             שלד משותף + ניווט לשלושת הדפים
templates/index.html            עמוד בית: לוח שנה (FullCalendar), פאנל משימות ליום, צ'אט העוזר, טופס הוספה
templates/tasks.html            עמוד כל המשימות - סינון, הוספה, עריכה, מחיקה
templates/task_templates.html   ניהול משימות חוזרות (templates)
static/js/app.js                לוגיקת עמוד הבית (לוח שנה, פאנל יום, צ'אט)
static/js/tasks.js              לוגיקת עמוד המשימות
static/js/task_templates.js     לוגיקת עמוד התבניות
static/js/common.js             קוד JS משותף (טעינת קטגוריות וכו')
static/style.css                עיצוב האפליקציה (RTL)
migrations/001_init.sql         סכימת בסיס הנתונים
migrations/002_arbox_classes.sql סכימת טבלת לוח השיעורים מ-Arbox
migrations/003_arbox_classes_status.sql עדכון סטטוס לטבלת arbox_classes
scripts/run_migrations.py       מריץ migrations חדשים מול Supabase
Procfile                        פקודת ההרצה בפרודקשן (gunicorn)
```

## סנכרון לו"ז מ-Arbox

- מבוסס על ה-API הרשמי של Arbox (v3, מפתח קבוע בכותרת `api-key`), התיעוד
  ב-https://arboxserver.arboxapp.com/docs/api (לא developers.arboxapp.com -
  דומיין זה לא קיים).
- כל טעינה של עמוד הבית (`/`) קוראת ל-`arbox.maybe_sync_schedule()` - אם עברה
  יותר משעה מאז השדה `synced_at` העדכני ביותר בטבלת `arbox_classes` (או
  שמעולם לא בוצע סנכרון), מתבצעת שליפה מלאה של 30 הימים הקרובים ו-upsert
  לטבלה. שגיאות API (מפתח לא תקין, שירות לא זמין, הטבלה עוד לא נוצרה) נבלעות
  בשקט - האפליקציה ממשיכה לעבוד רגיל עם המשימות בלבד.
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

## עוזר תכנון (`services/advisor.py`, מוצג בעמוד הבית)

צ'אטבוט (OpenAI, מודל `gpt-4o-mini`, function calling) שעוזר בתכנון עתידי של
הסטודיו - שבועות פתוחים, מופעים, ריטריטים.

- כלי OpenAI **אחד מאוחד**, `get_studio_context(date_from, date_to)`, שמרכז
  לפי בקשת המודל: משימות (`db.get_tasks`), לוח שיעורים מ-Arbox
  (`arbox.get_classes_between`), אירועים מיומן הסטודיו ב-Google
  (`google_calendar.get_studio_events`), וחגים (`religious_calendar.
  get_all_holidays`). כלי מאוחד אחד עם טווח תאריכים חופשי (ברירת מחדל 90 יום
  קדימה) נבחר על פני כלים נפרדים (מורכב מדי) או context קבוע (לא מכסה שאלות
  על טווחים רחוקים).
- הערות קבועות מ-`DATA/mydates.docx` (ימים/תקופות חשובות לסטודיו) נכללות
  ישירות ב-system prompt בכל שיחה.
- `google_calendar.py`: גישה ליומן האישי (`jeniabur@gmail.com`) וליומן הסטודיו
  (`flyfit03@gmail.com`) דרך Service Account שפרטיו נקראים ממשתנה הסביבה
  `GCP_SERVICE_ACCOUNT_JSON`. כל יומן רלוונטי חייב להיות משותף עם כתובת
  ה-`client_email` של ה-Service Account.
- `religious_calendar.py`: חגים יהודיים דרך Hebcal API, נוצריים דרך Nager.Date
  API (שניהם ללא מפתח), ומוסלמיים (Eid בלבד) דרך חבילת `holidays` המקומית -
  Aladhan API הוחלף בזו האחרונה כי התגלה כלא נגיש מסביבת הפיתוח.
- היסטוריית השיחה מנוהלת בצד הלקוח (נשלחת מחדש בכל בקשת `/api/chat`) - אין
  session בצד השרת, ולכן היא מתאפסת ברענון דף.
- טיפול שגיאות: בלי `OPENAI_API_KEY`, `advisor.is_configured()` מחזיר `False`
  ועמוד הבית פשוט לא מציג את הצ'אט; כל מקור נתונים בכלי המאוחד עטוף בנפרד
  ב-try/except כך שכשל באחד (למשל Google Calendar לא זמין) לא מפיל את שאר
  הנתונים.

## לוגיקה עסקית

- **גלגול משימות**: בכל טעינת עמוד הבית, כל משימה עם `completed=false` ו-
  `scheduled_date` בעבר מתעדכנת בפועל (UPDATE) ל-`scheduled_date` = היום.
  כדי לעצור את הגלגול פשוט מוחקים את המשימה (יש כפתור מחיקה בכל שורה).
- **תבניות**: בכל טעינת עמוד הבית, לכל תבנית פעילה נוצרת (אם עוד לא קיימת)
  משימה עם `scheduled_date` = היום, בצורה אידמפוטנטית (בדיקה לפי `template_id`
  + תאריך לפני יצירה).
- התאריך "היום" מחושב באזור הזמן `Asia/Jerusalem`, כדי שהגלגול יעבוד נכון גם
  כששרת הענן (Render) רץ ב-UTC.

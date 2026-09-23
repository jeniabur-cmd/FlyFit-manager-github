-- FlyFit Manager - שכבת נתונים פיננסית
-- Run this in the Supabase SQL editor after 003_arbox_classes_status.sql
--
-- שכבה נפרדת לגמרי ממשימות/לוח השנה (הטבלאות tasks/task_templates/categories
-- ו-arbox_classes אינן נוגעות כאן). המטרה: להשלים את מה ש-Arbox לא נותן -
-- הוצאות, רווחיות לפי פעילות/פרויקט, פריסת הכנסה חשבונאית, גבייה והתחשבנות
-- שותפות. sales_transactions/leads/classes הן "חומר גלם" שיסונכרן מ-Arbox
-- בשלב מאוחר יותר - לא טבלאות תצוגה עצמאיות.
--
-- אין RLS (כמו שאר הפרויקט): גישה רק מהשרת עם service_role key.
--
-- שלב זה הוא סכימה בלבד - אין views מחושבים (מלבד partner_balances שהתבקש
-- במפורש), אין endpoints, אין סנכרון בפועל.

-- ============================================================
-- ישויות בסיס
-- ============================================================

create table if not exists clients (
    id bigint generated always as identity primary key,
    name text not null,
    phone text,
    email text,
    -- מזהה הלקוח ב-Arbox, לסנכרון עתידי בלי כפילויות (upsert לפי השדה הזה).
    arbox_client_id text unique,
    created_at timestamptz not null default now()
);

create table if not exists instructors (
    id bigint generated always as identity primary key,
    name text not null,
    arbox_instructor_id text unique,
    active boolean not null default true,
    created_at timestamptz not null default now()
);

-- שורה אחת לרוב למדריך, אבל אין unique על instructor_id בכוונה: מודל תשלום
-- יכול להשתנות עם הזמן, ו-effective_from מאפשר לשמור היסטוריה של שינויים
-- במקום לדרוס. "הנוכחי" = השורה עם effective_from הכי גבוה לאותו מדריך.
create table if not exists instructor_payment_config (
    id bigint generated always as identity primary key,
    instructor_id bigint not null references instructors(id) on delete cascade,
    payment_type text not null check (payment_type in ('hourly', 'per_class', 'percentage', 'mixed')),
    rate_value numeric,
    effective_from date not null default current_date,
    notes text,
    created_at timestamptz not null default now()
);

create table if not exists products (
    id bigint generated always as identity primary key,
    name text not null,
    -- סטודיו/ילדים/אירועים/הכשרות/ריטריטים/השכרה/חנות
    domain text not null check (domain in ('studio', 'kids', 'events', 'trainings', 'retreats', 'rental', 'shop')),
    active boolean not null default true,
    created_at timestamptz not null default now()
);

-- כרטיס פרויקט לפעילות מיוחדת - מחבר בין הכנסות (sales_transactions.project_id)
-- להוצאות ישירות (expenses.project_id) כדי לחשב רווחיות לפי פעילות.
create table if not exists projects (
    id bigint generated always as identity primary key,
    name text not null,
    type text not null check (type in ('camp', 'event', 'retreat', 'workshop', 'teacher_course')),
    start_date date,
    end_date date,
    status text not null default 'active',
    notes text,
    created_at timestamptz not null default now()
);

-- ============================================================
-- מכירות (חומר גלם מ-Arbox)
-- ============================================================

create table if not exists sales_transactions (
    id bigint generated always as identity primary key,
    client_id bigint not null references clients(id),
    date date not null,
    product_id bigint references products(id),
    payment_method text,
    amount numeric not null,
    discount numeric not null default 0,
    refund numeric not null default 0,
    cancelled boolean not null default false,
    project_id bigint references projects(id),
    -- מזהה העסקה ב-Arbox עצמו, למניעת כפילויות בסנכרון עתידי (upsert).
    arbox_transaction_id text unique,
    created_at timestamptz not null default now()
);

-- פריסת הכנסה ממנוי רב-חודשי על פני חודשי הפעילות בפועל, לצורך P&L - נפרד
-- מ-sales_transactions כי ההכנסה מוצגת בשתי דרכים: מלאה בחודש המכירה
-- (sales_transactions.amount/date), ופרוסה כאן על חודשי הפעילות.
create table if not exists revenue_recognition_schedule (
    id bigint generated always as identity primary key,
    sales_transaction_id bigint not null references sales_transactions(id) on delete cascade,
    -- היום בתאריך תמיד 01 - השדה מייצג חודש, לא תאריך ספציפי.
    recognition_month date not null,
    recognized_amount numeric not null,
    created_at timestamptz not null default now(),
    unique (sales_transaction_id, recognition_month)
);

create table if not exists subscriptions (
    id bigint generated always as identity primary key,
    client_id bigint not null references clients(id),
    -- העסקה שיצרה את המנוי, אם ידועה (לחיבור עם revenue_recognition_schedule
    -- דרך sales_transaction_id המשותף).
    sales_transaction_id bigint references sales_transactions(id),
    start_date date not null,
    months integer not null,
    total_amount numeric not null,
    status text not null default 'active',
    created_at timestamptz not null default now()
);

-- ============================================================
-- לידים (חומר גלם, למדידת CAC לפי מקור בהמשך)
-- ============================================================

create table if not exists leads (
    id bigint generated always as identity primary key,
    source text,
    created_at timestamptz not null default now(),
    product_interested_id bigint references products(id),
    converted_client_id bigint references clients(id),
    converted_at timestamptz,
    ad_cost_allocated numeric
);

-- ============================================================
-- שיעורים ומדריכים
--
-- בכוונה טבלה נפרדת מ-arbox_classes הקיימת (המשמשת ללוח השנה/משימות):
-- arbox_classes היא מטמון סנכרון דחוס מ-Arbox (upsert שעתי, instructor_name
-- כטקסט חופשי בלי FK, מפתח ייחוד arbox_id+date) - לא מיועדת לחישובים
-- פיננסיים. classes כאן דורשת שלמות רפרנציאלית אמיתית (instructor_id FK
-- למודל תשלום, capacity+הרשמות ל-instructor_payments) שסנכרון שעתי גולמי
-- לא אמור לדרוס. המלצה: להשאיר נפרד, ובשלב מאוחר יותר לבנות ETL מפורש
-- שממלא classes מתוך arbox_classes/Arbox API עם matching מבוקר של מדריכים
-- (לא merge ישיר של שתי הטבלאות).
-- ============================================================

create table if not exists classes (
    id bigint generated always as identity primary key,
    date date not null,
    time time,
    type text,
    instructor_id bigint references instructors(id),
    capacity integer,
    created_at timestamptz not null default now()
);

create table if not exists class_registrations (
    id bigint generated always as identity primary key,
    class_id bigint not null references classes(id) on delete cascade,
    client_id bigint not null references clients(id),
    status text not null check (status in ('registered', 'attended', 'no_show', 'cancelled', 'waitlist')),
    created_at timestamptz not null default now(),
    unique (class_id, client_id)
);

create table if not exists instructor_payments (
    id bigint generated always as identity primary key,
    instructor_id bigint not null references instructors(id),
    -- מייצג חודש (יום=01), כמו revenue_recognition_schedule.recognition_month.
    period date not null,
    computed_amount numeric not null,
    basis text,
    created_at timestamptz not null default now()
);

-- ============================================================
-- הוצאות
-- ============================================================

create table if not exists expenses (
    id bigint generated always as identity primary key,
    date date not null,
    -- מבנה/כוח אדם/שיווק/תפעול/ציוד/חנות/פרויקטים/פיננסי/מקצועי/מיסים
    category text not null check (category in (
        'structure', 'hr', 'marketing', 'operations', 'equipment',
        'shop', 'projects', 'financial', 'professional', 'taxes'
    )),
    subcategory text,
    amount numeric not null,
    -- עלות ישירה משויכת לפרויקט - יחד עם sales_transactions.project_id
    -- מאפשר רווח לכל פעילות = הכנסות משויכות פחות עלויות ישירות משויכות.
    project_id bigint references projects(id),
    source text,
    created_at timestamptz not null default now()
);

-- ============================================================
-- גבייה והתאמות
-- ============================================================

-- ארבעת השדות מייצגים ארבעה מקורות שצריך להתאים ביניהם: עסקת Arbox, חשבונית,
-- סליקה, ובנק. יש לנו טבלה בפועל רק למקור הראשון (sales_transactions), לכן
-- arbox_transaction_id הוא FK אליה; invoice_id/clearing_id/bank_id הם מזהים
-- חיצוניים (טקסט) למערכות שאין להן טבלה משלהן בסכימה הזו. אם הכוונה הייתה
-- למזהה הגולמי מ-Arbox ולא לשורת sales_transactions שלנו - תגידי ואתקן.
create table if not exists reconciliation_records (
    id bigint generated always as identity primary key,
    arbox_transaction_id bigint references sales_transactions(id),
    invoice_id text,
    clearing_id text,
    bank_id text,
    status text not null check (status in (
        'matched', 'missing', 'duplicate', 'refund', 'fee', 'unassigned', 'uncollected'
    )),
    amount numeric,
    notes text,
    created_at timestamptz not null default now()
);

-- ============================================================
-- התחשבנות שותפות
-- ============================================================

-- סימן ה-amount (חיובי/שלילי) הוא זה שקובע כיוון היתרה - לא ה-type. החלטה
-- עסקית (למשל: האם personal_expense מגדיל או מקטין את מה שהעסק חייב לשותפה)
-- נשארת ברמת ההזנה, לא מקודדת בסכימה - "וודא שהסכימה מאפשרת, לא תממש את
-- החישוב המלא" כפי שהתבקש.
create table if not exists partner_ledger (
    id bigint generated always as identity primary key,
    partner_name text not null,
    date date not null,
    type text not null check (type in ('personal_expense', 'withdrawal', 'transfer', 'reimbursement')),
    amount numeric not null,
    note text,
    created_at timestamptz not null default now()
);

-- יתרה רצה לכל שותפה, מחושבת אוטומטית מתוך partner_ledger (סכום כל התנועות).
create or replace view partner_balances as
select
    partner_name,
    sum(amount) as balance
from partner_ledger
group by partner_name;

-- ============================================================
-- אינדקסים
-- ============================================================

create index if not exists idx_sales_transactions_date on sales_transactions(date);
create index if not exists idx_sales_transactions_client_id on sales_transactions(client_id);
create index if not exists idx_sales_transactions_project_id on sales_transactions(project_id);

create index if not exists idx_revenue_recognition_month on revenue_recognition_schedule(recognition_month);

create index if not exists idx_subscriptions_client_id on subscriptions(client_id);

create index if not exists idx_leads_created_at on leads(created_at);
create index if not exists idx_leads_source on leads(source);

create index if not exists idx_classes_date on classes(date);
create index if not exists idx_classes_instructor_id on classes(instructor_id);

create index if not exists idx_class_registrations_class_id on class_registrations(class_id);
create index if not exists idx_class_registrations_client_id on class_registrations(client_id);

create index if not exists idx_instructor_payments_instructor_period on instructor_payments(instructor_id, period);

create index if not exists idx_expenses_date on expenses(date);
create index if not exists idx_expenses_category on expenses(category);
create index if not exists idx_expenses_project_id on expenses(project_id);

create index if not exists idx_reconciliation_status on reconciliation_records(status);

create index if not exists idx_partner_ledger_partner_name on partner_ledger(partner_name);
create index if not exists idx_partner_ledger_date on partner_ledger(date);

-- ============================================================
-- RLS - כבוי בכל הטבלאות, כמו שאר הפרויקט (שרת בלבד, service_role key)
-- ============================================================

alter table clients disable row level security;
alter table instructors disable row level security;
alter table instructor_payment_config disable row level security;
alter table products disable row level security;
alter table projects disable row level security;
alter table sales_transactions disable row level security;
alter table revenue_recognition_schedule disable row level security;
alter table subscriptions disable row level security;
alter table leads disable row level security;
alter table classes disable row level security;
alter table class_registrations disable row level security;
alter table instructor_payments disable row level security;
alter table expenses disable row level security;
alter table reconciliation_records disable row level security;
alter table partner_ledger disable row level security;

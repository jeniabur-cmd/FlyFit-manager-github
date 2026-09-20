-- FlyFit Manager - Arbox schedule cancellation tracking
-- Run this in the Supabase SQL editor after 002_arbox_classes.sql

-- ה-API של Arbox (GET /schedule) לא מחזיר שום שדה שמציין ביטול - שיעור שבוטל
-- פשוט נעלם מהתשובה. לכן sync_schedule (arbox.py) מסמן שורה כ"cancelled" אם
-- היא הייתה קיימת בטווח שסונכרן אבל לא הופיעה יותר בתשובת ה-API, במקום
-- למחוק אותה (כדי לשמור היסטוריה).
alter table arbox_classes add column if not exists status text not null default 'scheduled';

create index if not exists idx_arbox_classes_status on arbox_classes(status);

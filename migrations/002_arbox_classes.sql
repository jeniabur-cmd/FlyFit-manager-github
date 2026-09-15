-- FlyFit Manager - Arbox schedule sync
-- Run this in the Supabase SQL editor after 001_init.sql

-- arbox_id (schedule_id מ-Arbox) אינו בהכרח ייחודי לבדו: אם הוא מזהה הגדרת
-- שיעור חוזר (לא מופע ספציפי), אותו arbox_id יחזור על עצמו בכל שבוע. לכן
-- מפתח הייחוד הוא הזוג (arbox_id, date) ולא arbox_id בלבד - כך נשמרת ההיסטוריה
-- של כל מופע שיעור בנפרד, וה-upsert מעדכן שורה קיימת באותו יום בלבד.
create table if not exists arbox_classes (
    id bigint generated always as identity primary key,
    arbox_id text not null,
    date date not null,
    time time,
    class_type text,
    instructor_name text,
    capacity integer,
    booked_count integer,
    synced_at timestamptz not null default now(),
    unique (arbox_id, date)
);

create index if not exists idx_arbox_classes_date on arbox_classes(date);

alter table arbox_classes disable row level security;

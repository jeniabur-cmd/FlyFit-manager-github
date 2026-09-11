-- FlyFit Manager - Initial schema
-- Run this in the Supabase SQL editor (project: hhwtbnzltbwfchcplqwr)
-- No RLS is enabled: the app is single-user and talks to Supabase only from the
-- Streamlit server using the service_role key (never exposed to the browser).

create table if not exists categories (
    id bigint generated always as identity primary key,
    name text not null unique
);

create table if not exists task_templates (
    id bigint generated always as identity primary key,
    title text not null,
    category_id bigint references categories(id) on delete set null,
    default_time time,
    active boolean not null default true
);

create table if not exists tasks (
    id bigint generated always as identity primary key,
    title text not null,
    category_id bigint references categories(id) on delete set null,
    scheduled_date date not null,
    scheduled_time time,
    notes text,
    completed boolean not null default false,
    completed_at timestamptz,
    template_id bigint references task_templates(id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_tasks_scheduled_date on tasks(scheduled_date);
create index if not exists idx_tasks_completed on tasks(completed);
create index if not exists idx_tasks_template_id_date on tasks(template_id, scheduled_date);

alter table categories disable row level security;
alter table task_templates disable row level security;
alter table tasks disable row level security;

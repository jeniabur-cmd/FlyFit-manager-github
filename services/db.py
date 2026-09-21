"""שכבת גישה ל-Supabase: חיבור, לוגיקת גלגול משימות, ויצירת משימות מתבניות."""
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client, Client

from .config import env, ttl_cache

TZ = ZoneInfo("Asia/Jerusalem")


def today_str() -> str:
    return datetime.now(TZ).date().isoformat()


@ttl_cache()
def get_client() -> Client:
    return create_client(
        env("SUPABASE_URL"),
        env("SUPABASE_SERVICE_ROLE_KEY"),
    )


def rollover_overdue_tasks() -> int:
    """מעדכן בפועל כל משימה לא-מבוצעת עם תאריך עבר ל-scheduled_date = היום."""
    client = get_client()
    today = today_str()
    overdue = (
        client.table("tasks")
        .select("id")
        .eq("completed", False)
        .lt("scheduled_date", today)
        .execute()
    )
    ids = [row["id"] for row in overdue.data]
    if ids:
        client.table("tasks").update({"scheduled_date": today}).in_("id", ids).execute()
    return len(ids)


def generate_today_tasks_from_templates() -> int:
    """יוצר task לכל template פעיל שעדיין אין לו משימה עם scheduled_date=היום (idempotent)."""
    client = get_client()
    today = today_str()

    templates = client.table("task_templates").select("*").eq("active", True).execute().data
    if not templates:
        return 0

    existing = (
        client.table("tasks")
        .select("template_id")
        .eq("scheduled_date", today)
        .not_.is_("template_id", "null")
        .execute()
    )
    existing_template_ids = {row["template_id"] for row in existing.data}

    created = 0
    for tmpl in templates:
        if tmpl["id"] in existing_template_ids:
            continue
        client.table("tasks").insert(
            {
                "title": tmpl["title"],
                "category_id": tmpl["category_id"],
                "scheduled_date": today,
                "scheduled_time": tmpl["default_time"],
                "template_id": tmpl["id"],
            }
        ).execute()
        created += 1
    return created


def run_daily_maintenance() -> None:
    """להריץ בראש כל טעינת עמוד: גלגול משימות שעברו + יצירת משימות מתבניות פעילות."""
    rollover_overdue_tasks()
    generate_today_tasks_from_templates()


# ---------- categories ----------

def get_categories() -> list[dict]:
    return get_client().table("categories").select("*").order("name").execute().data


def create_category(name: str) -> dict:
    return get_client().table("categories").insert({"name": name}).execute().data[0]


# ---------- tasks ----------

def get_tasks(date_from: str | None = None, date_to: str | None = None,
              category_id: int | None = None) -> list[dict]:
    query = get_client().table("tasks").select("*, categories(name)")
    if date_from:
        query = query.gte("scheduled_date", date_from)
    if date_to:
        query = query.lte("scheduled_date", date_to)
    if category_id:
        query = query.eq("category_id", category_id)
    return query.order("scheduled_date").order("scheduled_time").execute().data


def get_tasks_for_date(date: str) -> list[dict]:
    return (
        get_client()
        .table("tasks")
        .select("*, categories(name)")
        .eq("scheduled_date", date)
        .order("scheduled_time")
        .execute()
        .data
    )


def count_incomplete_today() -> int:
    today = today_str()
    res = (
        get_client()
        .table("tasks")
        .select("id", count="exact")
        .eq("scheduled_date", today)
        .eq("completed", False)
        .execute()
    )
    return res.count or 0


def create_task(title: str, category_id: int | None, scheduled_date: str,
                 scheduled_time: str | None = None, notes: str | None = None,
                 template_id: int | None = None) -> dict:
    payload = {
        "title": title,
        "category_id": category_id,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "notes": notes,
        "template_id": template_id,
    }
    return get_client().table("tasks").insert(payload).execute().data[0]


def update_task(task_id: int, **fields) -> dict:
    return get_client().table("tasks").update(fields).eq("id", task_id).execute().data[0]


def set_task_completed(task_id: int, completed: bool) -> dict:
    fields = {
        "completed": completed,
        "completed_at": datetime.now(TZ).isoformat() if completed else None,
    }
    return update_task(task_id, **fields)


def delete_task(task_id: int) -> None:
    get_client().table("tasks").delete().eq("id", task_id).execute()


# ---------- task templates ----------

def get_templates(active_only: bool = False) -> list[dict]:
    query = get_client().table("task_templates").select("*, categories(name)")
    if active_only:
        query = query.eq("active", True)
    return query.order("title").execute().data


def create_template(title: str, category_id: int | None,
                     default_time: str | None = None) -> dict:
    payload = {"title": title, "category_id": category_id, "default_time": default_time}
    return get_client().table("task_templates").insert(payload).execute().data[0]


def update_template(template_id: int, **fields) -> dict:
    return (
        get_client()
        .table("task_templates")
        .update(fields)
        .eq("id", template_id)
        .execute()
        .data[0]
    )


def delete_template(template_id: int) -> None:
    get_client().table("task_templates").delete().eq("id", template_id).execute()

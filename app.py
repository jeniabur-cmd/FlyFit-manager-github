"""FlyFit Manager - Flask app.

שלב 2: עמוד בית מאוחד - לוח שנה (משימות + שיעורי Arbox), פאנל ניהול משימות
ליום שנלחץ, צ'אט עוזר תכנון, וטופס הוספת משימה.
שלב 4: עמודי משימות ותבניות נפרדים (routes+templates, עם base.html משותף
לניווט). כל האינטראקציה בכל העמודים דרך endpoints ב-/api/... שה-JS קורא
להם עם fetch - בלי רענון עמוד מלא.
"""
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request

from services import advisor, arbox, db

app = Flask(__name__)


# ---------- עזרי תאריך/JSON ----------

def _parse_date_param(value: str) -> str:
    """מקבל תאריך או datetime מלא (כמו ש-FullCalendar שולח ב-start/end,
    כולל timezone offset) ומחזיר תאריך Y-m-d בלבד."""
    if "T" in value:
        value = value.split("T", 1)[0]
    return value


def _task_event(task: dict) -> dict:
    time_part = str(task["scheduled_time"])[:5] if task.get("scheduled_time") else None
    return {
        "id": f"task-{task['id']}",
        "title": task["title"],
        "start": f"{task['scheduled_date']}T{time_part}" if time_part else task["scheduled_date"],
        "allDay": time_part is None,
        "color": "#2563eb",
        "extendedProps": {"type": "task"},
    }


def _arbox_event(cls: dict) -> dict:
    time_part = str(cls["time"])[:5] if cls.get("time") else None
    title = cls.get("class_type") or "שיעור"
    return {
        "id": f"arbox-{cls['id']}",
        "title": title,
        "start": f"{cls['date']}T{time_part}" if time_part else cls["date"],
        "allDay": time_part is None,
        "color": "#a855f7",
        "extendedProps": {
            "type": "arbox",
            "instructor_name": cls.get("instructor_name"),
            "capacity": cls.get("capacity"),
            "booked_count": cls.get("booked_count"),
        },
    }


def _task_json(task: dict) -> dict:
    category = task.get("categories") or {}
    return {
        "id": task["id"],
        "title": task["title"],
        "scheduled_date": task["scheduled_date"],
        "scheduled_time": str(task["scheduled_time"])[:5] if task.get("scheduled_time") else None,
        "notes": task.get("notes"),
        "completed": task["completed"],
        "category_id": task.get("category_id"),
        "category_name": category.get("name"),
    }


def _template_json(tmpl: dict) -> dict:
    category = tmpl.get("categories") or {}
    return {
        "id": tmpl["id"],
        "title": tmpl["title"],
        "category_id": tmpl.get("category_id"),
        "category_name": category.get("name"),
        "default_time": str(tmpl["default_time"])[:5] if tmpl.get("default_time") else None,
        "active": tmpl["active"],
    }


# ---------- עמוד הבית ----------

@app.route("/")
def index():
    db.run_daily_maintenance()
    arbox.maybe_sync_schedule()
    categories = db.get_categories()
    return render_template(
        "index.html",
        categories=categories,
        advisor_enabled=advisor.is_configured(),
        today=db.today_str(),
    )


@app.route("/tasks")
def tasks_page():
    return render_template("tasks.html", categories=db.get_categories(), today=db.today_str())


@app.route("/task-templates")
def templates_page():
    return render_template("task_templates.html", categories=db.get_categories())


# ---------- API: לוח שנה ----------

@app.route("/api/calendar-events")
def api_calendar_events():
    """FullCalendar קורא לזה עם start/end (ISO, כולל טווח השבועות המוצגים
    בפועל בתצוגת החודש - לא רק החודש הנקי). מחזיר משימות פתוחות (לא
    בוצעו - ראו _task_event/get_tasks) + שיעורי Arbox לא-מבוטלים, כ-events
    בפורמט ש-FullCalendar מבין ישירות."""
    date_from = _parse_date_param(request.args.get("start", db.today_str()))
    date_to = _parse_date_param(request.args.get("end", db.today_str()))

    tasks = [t for t in db.get_tasks(date_from, date_to) if not t["completed"]]
    classes = arbox.get_classes_between(date_from, date_to)

    events = [_task_event(t) for t in tasks] + [_arbox_event(c) for c in classes]
    return jsonify(events)


@app.route("/api/tasks-for-date/<date_str>")
def api_tasks_for_date(date_str: str):
    """הרשימה המלאה למשימות היום שנלחץ בלוח - לפאנל הניהול. משימות שבוצעו
    לא כלולות (הן 'נעלמות מהתצוגה', לא נמחקות מה-DB)."""
    tasks = [t for t in db.get_tasks_for_date(date_str) if not t["completed"]]
    return jsonify([_task_json(t) for t in tasks])


# ---------- API: משימות (CRUD) ----------

@app.route("/api/tasks", methods=["GET"])
def api_list_tasks():
    """הרשימה המלאה (כולל משימות שבוצעו - להצגה עם קו חוצה, לא הסתרה)
    לעמוד /tasks, עם סינון אופציונלי לפי טווח תאריכים/קטגוריה."""
    date_from = request.args.get("date_from") or None
    date_to = request.args.get("date_to") or None
    category_id = request.args.get("category_id", type=int) or None
    tasks = db.get_tasks(date_from=date_from, date_to=date_to, category_id=category_id)
    return jsonify([_task_json(t) for t in tasks])


@app.route("/api/tasks", methods=["POST"])
def api_create_task():
    body = request.get_json(force=True)
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "כותרת המשימה חובה"}), 400
    scheduled_date = body.get("scheduled_date") or db.today_str()

    task = db.create_task(
        title=title,
        category_id=body.get("category_id") or None,
        scheduled_date=scheduled_date,
        scheduled_time=body.get("scheduled_time") or None,
        notes=(body.get("notes") or "").strip() or None,
    )
    return jsonify(_task_json(task)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def api_update_task(task_id: int):
    body = request.get_json(force=True)
    fields = {}
    if "title" in body:
        fields["title"] = body["title"].strip()
    if "category_id" in body:
        fields["category_id"] = body["category_id"] or None
    if "scheduled_date" in body:
        fields["scheduled_date"] = body["scheduled_date"]
    if "scheduled_time" in body:
        fields["scheduled_time"] = body["scheduled_time"] or None
    if "notes" in body:
        fields["notes"] = (body["notes"] or "").strip() or None

    task = db.update_task(task_id, **fields)
    return jsonify(_task_json(task))


@app.route("/api/tasks/<int:task_id>/complete", methods=["PATCH"])
def api_complete_task(task_id: int):
    body = request.get_json(silent=True) or {}
    completed = bool(body.get("completed", True))
    task = db.set_task_completed(task_id, completed)
    return jsonify(_task_json(task))


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def api_delete_task(task_id: int):
    db.delete_task(task_id)
    return "", 204


# ---------- API: קטגוריות ----------

@app.route("/api/categories", methods=["GET"])
def api_list_categories():
    return jsonify(db.get_categories())


@app.route("/api/categories", methods=["POST"])
def api_create_category():
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "שם הקטגוריה חובה"}), 400
    category = db.create_category(name)
    return jsonify(category), 201


# ---------- API: תבניות משימות חוזרות ----------

@app.route("/api/templates", methods=["GET"])
def api_list_templates():
    return jsonify([_template_json(t) for t in db.get_templates()])


@app.route("/api/templates", methods=["POST"])
def api_create_template():
    body = request.get_json(force=True)
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "כותרת חובה"}), 400
    tmpl = db.create_template(
        title=title,
        category_id=body.get("category_id") or None,
        default_time=body.get("default_time") or None,
    )
    return jsonify(_template_json(tmpl)), 201


@app.route("/api/templates/<int:template_id>", methods=["PUT"])
def api_update_template(template_id: int):
    body = request.get_json(force=True)
    fields = {}
    if "title" in body:
        fields["title"] = body["title"].strip()
    if "category_id" in body:
        fields["category_id"] = body["category_id"] or None
    if "default_time" in body:
        fields["default_time"] = body["default_time"] or None
    tmpl = db.update_template(template_id, **fields)
    return jsonify(_template_json(tmpl))


@app.route("/api/templates/<int:template_id>/toggle", methods=["PATCH"])
def api_toggle_template(template_id: int):
    templates = {t["id"]: t for t in db.get_templates()}
    current = templates.get(template_id)
    if current is None:
        return jsonify({"error": "תבנית לא נמצאה"}), 404
    tmpl = db.update_template(template_id, active=not current["active"])
    return jsonify(_template_json(tmpl))


@app.route("/api/templates/<int:template_id>", methods=["DELETE"])
def api_delete_template(template_id: int):
    db.delete_template(template_id)
    return "", 204


# ---------- API: עוזר תכנון ----------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    if not advisor.is_configured():
        return jsonify({"error": "OPENAI_API_KEY לא מוגדר"}), 400

    body = request.get_json(force=True)
    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    if not message:
        return jsonify({"error": "הודעה ריקה"}), 400

    try:
        reply, degraded, _system_prompt = advisor.chat(history, message)
    except Exception as e:
        return jsonify({"error": f"שגיאה בפנייה ל-OpenAI: {e}"}), 502

    return jsonify({"reply": reply, "degraded": degraded})


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)

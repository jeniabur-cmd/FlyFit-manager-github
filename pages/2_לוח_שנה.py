"""תצוגת לוח שנה חודשי - כל יום מציג כמות משימות, לחיצה מציגה את הרשימה המלאה."""
import datetime as dt

import streamlit as st
from streamlit_calendar import calendar

import arbox
import db
from common import init_page, category_creator, category_options, render_task_row

init_page("לוח שנה", "📅")

st.title("📅 לוח שנה")

all_tasks = db.get_tasks()

counts: dict[str, int] = {}
for t in all_tasks:
    counts[t["scheduled_date"]] = counts.get(t["scheduled_date"], 0) + 1

events = [
    {
        "title": "משימה אחת" if count == 1 else f"{count} משימות",
        "start": date_str,
        "allDay": True,
    }
    for date_str, count in counts.items()
]

calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "",
    },
    "initialView": "dayGridMonth",
    "initialDate": db.today_str(),
    "locale": "he",
    "direction": "rtl",
    "height": 650,
}

state = calendar(
    events=events,
    options=calendar_options,
    callbacks=["dateClick"],
    key="flyfit_calendar",
)

date_click = state.get("dateClick") if isinstance(state, dict) else None
if date_click and date_click.get("date"):
    utc_instant = dt.datetime.fromisoformat(date_click["date"].replace("Z", "+00:00"))
    clicked_date = utc_instant.astimezone(db.TZ).date().isoformat()
    st.session_state["calendar_selected_date"] = clicked_date

selected_date = st.session_state.get("calendar_selected_date", db.today_str())

st.divider()
st.subheader(f"משימות ליום {selected_date}")

categories = db.get_categories()
category_creator(key_prefix="calendar_page")
labels, mapping = category_options(categories)

with st.form("calendar_add_task_form", clear_on_submit=True):
    title = st.text_input("כותרת משימה חדשה")
    cat_label = st.selectbox("קטגוריה", labels)
    col1, col2 = st.columns(2)
    has_time = col1.checkbox("להגדיר שעה")
    scheduled_time = col2.time_input("שעה", value=dt.time(9, 0), disabled=not has_time)
    notes = st.text_area("הערות")
    submitted = st.form_submit_button("הוסף ליום זה")
    if submitted:
        if not title.strip():
            st.error("יש להזין כותרת למשימה")
        else:
            db.create_task(
                title=title.strip(),
                category_id=mapping.get(cat_label),
                scheduled_date=selected_date,
                scheduled_time=scheduled_time.isoformat() if has_time else None,
                notes=notes.strip() or None,
            )
            st.success("המשימה נוספה")
            st.rerun()

day_tasks = db.get_tasks_for_date(selected_date)
if not day_tasks:
    st.info("אין משימות ליום זה")
else:
    for task in day_tasks:
        render_task_row(task, key_prefix="cal")
        st.divider()

# --- שכבת לוח שיעורים מ-Arbox (לצד המשימות, לא במקומן) ---
try:
    day_classes = arbox.get_classes_for_date(selected_date)
    last_sync = arbox.last_synced_at()
except Exception:
    day_classes = None
    last_sync = None

if day_classes is not None:
    st.divider()
    header_col, btn_col = st.columns([0.7, 0.3])
    header_col.subheader(f"🏋️ שיעורים - {selected_date}")
    if last_sync:
        header_col.caption(f"עדכון אחרון: {last_sync.astimezone(db.TZ).strftime('%d/%m %H:%M')}")
    if btn_col.button("🔄 רענן לו\"ז עכשיו", key="arbox_refresh_btn"):
        try:
            count = arbox.sync_schedule()
            st.success(f"סונכרנו {count} שיעורים מ-Arbox")
        except Exception as e:
            st.error(f"סנכרון מול Arbox נכשל: {e}")
        st.rerun()

    if not day_classes:
        st.caption("אין שיעורים רשומים ביום זה")
    else:
        for c in day_classes:
            time_str = str(c["time"])[:5] if c.get("time") else None
            capacity, booked = c.get("capacity"), c.get("booked_count")
            occupancy = f"{booked}/{capacity}" if capacity is not None and booked is not None else None
            bits = [b for b in [
                f"🕒 {time_str}" if time_str else None,
                f"🧑‍🏫 {c['instructor_name']}" if c.get("instructor_name") else None,
                f"👥 {occupancy}" if occupancy else None,
            ] if b]
            st.markdown(
                f"**{c.get('class_type') or 'שיעור'}**"
                + (f"  \n<small>{'  '.join(bits)}</small>" if bits else ""),
                unsafe_allow_html=True,
            )

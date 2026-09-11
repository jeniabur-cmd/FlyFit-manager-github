"""רשימת כל המשימות עם סינון, טופס הוספה, ועריכה/מחיקה."""
import datetime as dt

import streamlit as st

import db
from common import init_page, category_creator, category_options, render_task_row

init_page("משימות", "📋")

st.title("📋 כל המשימות")

# ---------- הוספת משימה חדשה ----------
st.subheader("הוספת משימה")

categories = db.get_categories()
category_creator(key_prefix="tasks_page")
labels, mapping = category_options(categories)

with st.form("add_task_form", clear_on_submit=True):
    title = st.text_input("כותרת המשימה *")
    cat_label = st.selectbox("קטגוריה", labels)
    col1, col2 = st.columns(2)
    scheduled_date = col1.date_input("תאריך *", value=dt.date.today())
    has_time = col2.checkbox("להגדיר שעה")
    scheduled_time = col2.time_input("שעה", value=dt.time(9, 0), disabled=not has_time)
    notes = st.text_area("הערות")

    submitted = st.form_submit_button("הוסף משימה")
    if submitted:
        if not title.strip():
            st.error("יש להזין כותרת למשימה")
        else:
            db.create_task(
                title=title.strip(),
                category_id=mapping.get(cat_label),
                scheduled_date=scheduled_date.isoformat(),
                scheduled_time=scheduled_time.isoformat() if has_time else None,
                notes=notes.strip() or None,
            )
            st.success("המשימה נוספה")
            st.rerun()

st.divider()

# ---------- סינון ----------
st.subheader("סינון")

filter_cols = st.columns(3)
date_from = filter_cols[0].date_input("מתאריך", value=None)
date_to = filter_cols[1].date_input("עד תאריך", value=None)
filter_labels = ["(הכל)"] + [c["name"] for c in categories]
filter_cat_label = filter_cols[2].selectbox("קטגוריה", filter_labels)
filter_cat_id = mapping.get(filter_cat_label) if filter_cat_label != "(הכל)" else None

tasks = db.get_tasks(
    date_from=date_from.isoformat() if date_from else None,
    date_to=date_to.isoformat() if date_to else None,
    category_id=filter_cat_id,
)

st.divider()
st.subheader(f"רשימת משימות ({len(tasks)})")

if not tasks:
    st.info("לא נמצאו משימות")
else:
    grouped: dict[str, list[dict]] = {}
    for t in tasks:
        grouped.setdefault(t["scheduled_date"], []).append(t)
    for date_key in sorted(grouped.keys()):
        st.markdown(f"### {date_key}")
        for task in grouped[date_key]:
            render_task_row(task, key_prefix="list")
        st.divider()

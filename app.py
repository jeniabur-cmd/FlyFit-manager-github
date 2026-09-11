"""FlyFit Manager - עמוד ראשי: באנר משימות פתוחות להיום + רשימת משימות היום."""
import streamlit as st

import db
from common import init_page, render_task_row

init_page("FlyFit Manager", "🗓️")

st.title("🗓️ FlyFit Manager")

incomplete_count = db.count_incomplete_today()
if incomplete_count > 0:
    st.warning(f"יש {incomplete_count} משימות שלא בוצעו היום")

st.subheader("משימות היום")

today_tasks = db.get_tasks_for_date(db.today_str())

if not today_tasks:
    st.info("אין משימות מתוכננות להיום 🎉")
else:
    for task in today_tasks:
        render_task_row(task, key_prefix="home")
        st.divider()

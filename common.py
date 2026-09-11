"""רכיבי UI משותפים לכל עמודי האפליקציה: RTL, אתחול עמוד, בחירת קטגוריה, שורת משימה."""
import datetime as dt

import streamlit as st

import db

RTL_CSS = """
<style>
    html, body, [class*="css"] {
        direction: rtl;
    }
    .stApp {
        direction: rtl;
    }
    [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    .stTextInput input, .stTextArea textarea, .stNumberInput input,
    .stDateInput input, .stTimeInput input {
        direction: rtl;
        text-align: right;
    }
    .stSelectbox div[data-baseweb="select"] {
        direction: rtl;
        text-align: right;
    }
    .stButton button {
        direction: rtl;
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        direction: rtl;
    }
    div[role="radiogroup"] {
        direction: rtl;
    }
    .stDataFrame {
        direction: rtl;
    }
    .stMarkdown, .stAlert, .stExpander {
        direction: rtl;
        text-align: right;
    }
</style>
"""

NEW_CATEGORY_LABEL = "➕ קטגוריה חדשה..."


def init_page(page_title: str, page_icon: str = "🗂️") -> None:
    st.set_page_config(page_title=page_title, page_icon=page_icon, layout="centered")
    st.markdown(RTL_CSS, unsafe_allow_html=True)
    db.run_daily_maintenance()


def category_creator(key_prefix: str) -> None:
    """תיבת יצירת קטגוריה חדשה. להציב מעל טופס שבו רוצים לבחור קטגוריה."""
    with st.expander("➕ קטגוריה חדשה", expanded=False):
        new_name = st.text_input("שם הקטגוריה", key=f"{key_prefix}_new_cat_name")
        if st.button("צור קטגוריה", key=f"{key_prefix}_new_cat_btn"):
            if new_name.strip():
                try:
                    db.create_category(new_name.strip())
                    st.success(f"הקטגוריה \"{new_name.strip()}\" נוצרה")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה ביצירת הקטגוריה: {e}")
            else:
                st.warning("יש להזין שם קטגוריה")


def category_options(categories: list[dict]) -> tuple[list[str], dict[str, int]]:
    """מחזיר רשימת תוויות לתיבת בחירה ומיפוי תווית -> category_id."""
    labels = ["(ללא קטגוריה)"] + [c["name"] for c in categories]
    mapping = {c["name"]: c["id"] for c in categories}
    return labels, mapping


def render_task_row(task: dict, key_prefix: str) -> None:
    """שורת משימה: checkbox לביצוע, פרטים, וכפתור מחיקה. תמיד יש כפתור מחיקה."""
    cols = st.columns([0.08, 0.62, 0.15, 0.15])
    task_id = task["id"]

    done = cols[0].checkbox("בוצע", value=task["completed"], key=f"{key_prefix}_done_{task_id}",
                             label_visibility="collapsed")
    if done != task["completed"]:
        db.set_task_completed(task_id, done)
        st.rerun()

    category_name = (task.get("categories") or {}).get("name") if task.get("categories") else None
    title_text = task["title"]
    if task["completed"]:
        title_text = f"~~{title_text}~~"
    detail_bits = []
    if task.get("scheduled_time"):
        detail_bits.append(f"🕒 {str(task['scheduled_time'])[:5]}")
    if category_name:
        detail_bits.append(f"🏷️ {category_name}")
    detail = "  ".join(detail_bits)
    cols[1].markdown(f"{title_text}" + (f"  \n<small>{detail}</small>" if detail else ""),
                      unsafe_allow_html=True)
    if task.get("notes"):
        cols[1].caption(task["notes"])

    if cols[2].button("✏️", key=f"{key_prefix}_edit_{task_id}", help="עריכה"):
        st.session_state[f"editing_task_{task_id}"] = True

    if cols[3].button("🗑️", key=f"{key_prefix}_del_{task_id}", help="מחיקה"):
        db.delete_task(task_id)
        st.rerun()

    if st.session_state.get(f"editing_task_{task_id}"):
        render_task_edit_form(task, key_prefix)


def render_task_edit_form(task: dict, key_prefix: str) -> None:
    task_id = task["id"]
    categories = db.get_categories()
    labels, mapping = category_options(categories)
    current_cat_name = (task.get("categories") or {}).get("name") if task.get("categories") else None
    current_index = labels.index(current_cat_name) if current_cat_name in labels else 0

    with st.form(key=f"{key_prefix}_edit_form_{task_id}"):
        title = st.text_input("כותרת", value=task["title"])
        cat_label = st.selectbox("קטגוריה", labels, index=current_index)
        sched_date = st.date_input("תאריך", value=dt.date.fromisoformat(task["scheduled_date"]))
        current_time = None
        if task.get("scheduled_time"):
            current_time = dt.time.fromisoformat(str(task["scheduled_time"])[:8])
        has_time = st.checkbox("שעה מוגדרת", value=current_time is not None)
        sched_time = st.time_input("שעה", value=current_time or dt.time(9, 0))
        notes = st.text_area("הערות", value=task.get("notes") or "")

        col_a, col_b = st.columns(2)
        submitted = col_a.form_submit_button("שמור")
        cancelled = col_b.form_submit_button("ביטול")

        if submitted:
            db.update_task(
                task_id,
                title=title,
                category_id=mapping.get(cat_label),
                scheduled_date=sched_date.isoformat(),
                scheduled_time=sched_time.isoformat() if has_time else None,
                notes=notes or None,
            )
            st.session_state[f"editing_task_{task_id}"] = False
            st.rerun()
        if cancelled:
            st.session_state[f"editing_task_{task_id}"] = False
            st.rerun()

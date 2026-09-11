"""ניהול משימות חוזרות (templates): הוספה, עריכה, השבתה/הפעלה."""
import datetime as dt

import streamlit as st

import db
from common import init_page, category_creator, category_options

init_page("תבניות", "🔁")

st.title("🔁 תבניות משימות חוזרות")
st.caption("כל תבנית פעילה יוצרת אוטומטית משימה חדשה בכל יום.")

categories = db.get_categories()
category_creator(key_prefix="templates_page")
labels, mapping = category_options(categories)

st.subheader("תבנית חדשה")
with st.form("add_template_form", clear_on_submit=True):
    title = st.text_input("כותרת *")
    cat_label = st.selectbox("קטגוריה", labels)
    has_time = st.checkbox("להגדיר שעת ברירת מחדל")
    default_time = st.time_input("שעה", value=dt.time(9, 0), disabled=not has_time)

    submitted = st.form_submit_button("הוסף תבנית")
    if submitted:
        if not title.strip():
            st.error("יש להזין כותרת")
        else:
            db.create_template(
                title=title.strip(),
                category_id=mapping.get(cat_label),
                default_time=default_time.isoformat() if has_time else None,
            )
            st.success("התבנית נוספה")
            st.rerun()

st.divider()
st.subheader("כל התבניות")

templates = db.get_templates()
if not templates:
    st.info("אין תבניות עדיין")
else:
    for tmpl in templates:
        tmpl_id = tmpl["id"]
        cols = st.columns([0.45, 0.2, 0.12, 0.11, 0.12])
        cat_name = (tmpl.get("categories") or {}).get("name") if tmpl.get("categories") else None
        status = "✅ פעיל" if tmpl["active"] else "⏸️ מושבת"
        cols[0].markdown(f"**{tmpl['title']}**  \n<small>{cat_name or ''} {status}</small>",
                          unsafe_allow_html=True)
        time_display = str(tmpl["default_time"])[:5] if tmpl.get("default_time") else "—"
        cols[1].markdown(f"🕒 {time_display}")

        if cols[2].button("✏️", key=f"edit_tmpl_{tmpl_id}", help="עריכה"):
            st.session_state[f"editing_tmpl_{tmpl_id}"] = not st.session_state.get(
                f"editing_tmpl_{tmpl_id}", False)

        toggle_label = "השבת" if tmpl["active"] else "הפעל"
        if cols[3].button(toggle_label, key=f"toggle_{tmpl_id}"):
            db.update_template(tmpl_id, active=not tmpl["active"])
            st.rerun()

        if cols[4].button("🗑️", key=f"del_tmpl_{tmpl_id}", help="מחיקת תבנית"):
            db.delete_template(tmpl_id)
            st.rerun()

        if st.session_state.get(f"editing_tmpl_{tmpl_id}"):
            current_cat_name = cat_name
            current_index = labels.index(current_cat_name) if current_cat_name in labels else 0
            current_time = (dt.time.fromisoformat(str(tmpl["default_time"])[:8])
                             if tmpl.get("default_time") else None)
            with st.form(key=f"edit_tmpl_form_{tmpl_id}"):
                e_title = st.text_input("כותרת", value=tmpl["title"])
                e_cat_label = st.selectbox("קטגוריה", labels, index=current_index)
                e_has_time = st.checkbox("שעת ברירת מחדל", value=current_time is not None)
                e_time = st.time_input("שעה", value=current_time or dt.time(9, 0))
                c1, c2 = st.columns(2)
                save = c1.form_submit_button("שמור")
                cancel = c2.form_submit_button("ביטול")
                if save:
                    db.update_template(
                        tmpl_id,
                        title=e_title.strip() or tmpl["title"],
                        category_id=mapping.get(e_cat_label),
                        default_time=e_time.isoformat() if e_has_time else None,
                    )
                    st.session_state[f"editing_tmpl_{tmpl_id}"] = False
                    st.rerun()
                if cancel:
                    st.session_state[f"editing_tmpl_{tmpl_id}"] = False
                    st.rerun()

        st.divider()

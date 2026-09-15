"""יועץ תכנון: צ'אט עם עוזר AI שמכיר את לוח הזמנים של הסטודיו (משימות, לוח
שיעורים מ-Arbox, יומן הסטודיו ב-Google, חגים) כדי לעזור בתכנון עתידי."""
import streamlit as st

import advisor
from common import init_page

init_page("יועץ תכנון", "🤖")

st.title("🤖 יועץ תכנון")
st.caption("שאלו על תכנון עתידי לסטודיו - שבועות פתוחים, מופעים, ריטריטים וכו'.")

if not advisor.is_configured():
    st.info("כדי להפעיל את היועץ יש להגדיר OPENAI_API_KEY ב-.streamlit/secrets.toml.")
    st.stop()

if "advisor_history" not in st.session_state:
    st.session_state["advisor_history"] = []

if st.button("🗑️ נקה שיחה"):
    st.session_state["advisor_history"] = []
    st.rerun()

for msg in st.session_state["advisor_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_message = st.chat_input("כתבו כאן שאלה על תכנון הסטודיו...")
if user_message:
    st.session_state["advisor_history"].append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("חושב..."):
            try:
                reply = advisor.chat(st.session_state["advisor_history"][:-1], user_message)
            except Exception as e:
                reply = None
                st.error(f"שגיאה בפנייה ל-OpenAI: {e}")
        if reply:
            st.markdown(reply)

    if reply:
        st.session_state["advisor_history"].append({"role": "assistant", "content": reply})

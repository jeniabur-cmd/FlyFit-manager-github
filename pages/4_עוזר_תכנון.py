"""עוזר תכנון: צ'אט עם עוזר AI שאוסף מראש חלון נתונים מתגלגל (90 יום קדימה)
מכל המקורות - משימות, לוח שיעורים מ-Arbox, יומני Google (אישי + סטודיו),
וחגים - כדי לעזור בתכנון עתידי של הסטודיו."""
import streamlit as st

import advisor
from common import init_page

init_page("עוזר תכנון", "🤖")

st.title("🤖 עוזר תכנון")
st.caption("שאלו על תכנון עתידי לסטודיו - שבועות פתוחים, מופעים, ריטריטים וכו'.")

if not advisor.is_configured():
    st.info("כדי להפעיל את העוזר יש להגדיר OPENAI_API_KEY ב-.streamlit/secrets.toml.")
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

    reply = None
    degraded: list[str] = []
    with st.chat_message("assistant"):
        with st.spinner("אוסף נתונים ומנסח תשובה..."):
            try:
                reply, degraded = advisor.chat(st.session_state["advisor_history"][:-1], user_message)
            except Exception as e:
                st.error(f"שגיאה בפנייה ל-OpenAI: {e}")
        if reply:
            st.markdown(reply)
        if degraded:
            st.caption("⚠️ מקורות שלא היו זמינים הפעם: " + " | ".join(degraded))

    if reply:
        st.session_state["advisor_history"].append({"role": "assistant", "content": reply})

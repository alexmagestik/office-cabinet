"""«Рабочий кабинет» — приложение координатора компании «Северная линия».

Запуск:  python3 -m streamlit run app.py
"""

import streamlit as st

from cabinet import model, theme
from cabinet.sections import backup, calendar, materials, overview, reports, tasks

st.set_page_config(
    page_title="Рабочий кабинет — Северная линия",
    page_icon="🗂️",
    layout="wide",
)
st.markdown(theme.CSS, unsafe_allow_html=True)

state = model.get_state()

SECTIONS = {
    "Обзор": overview.render,
    "Задачи": tasks.render,
    "Календарь": calendar.render,
    "Материалы": materials.render,
    "Отчёты": reports.render,
    "Резервная копия": backup.render,
}

REMINDER = ("Перед выходом скачайте резервную копию. При следующем посещении "
            "загрузите её. Автосохранения между посещениями нет.")

# --- Боковая навигация ------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"""
        <div style="padding:4px 4px 16px 4px;">
          <div style="font-size:22px;font-weight:800;color:{theme.ACCENT};">
            Северная линия</div>
          <div style="font-size:13px;color:{theme.MUTED};margin-top:4px;">
            Операционное сопровождение<br>Рабочий кабинет</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    current = st.radio("Разделы", list(SECTIONS), label_visibility="collapsed")
    st.divider()
    st.markdown(
        f"""
        <div style="background:{theme.WARNING_BG};border-radius:10px;
                    padding:10px 12px;font-size:13px;color:{theme.TEXT};
                    line-height:1.5;">
          <b>Перед выходом скачайте резервную копию.</b> При следующем
          посещении загрузите её. Автосохранения между посещениями нет.
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Содержимое раздела ------------------------------------------------------
st.markdown(f'<div class="cab-mobile-reminder">{REMINDER}</div>',
            unsafe_allow_html=True)
SECTIONS[current](state)

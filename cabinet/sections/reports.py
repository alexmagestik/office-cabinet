"""Раздел «Отчёты»: выгрузка текущей выборки задач в CSV (UTF-8 BOM, «;»)."""

import pandas as pd
import streamlit as st

from .. import model
from ..components import empty_state, header, style_status_column


def render(state: dict) -> None:
    header(
        "Рабочий кабинет",
        "Отчёты",
        "Выгрузка выборки задач в CSV с разделителем «;»",
    )

    if not state["задачи"]:
        empty_state(
            "🧾",
            "Отчёты появятся после загрузки данных",
            "Загрузите рабочий план в разделе «Задачи» — после этого выборку "
            "можно будет выгрузить в CSV.",
        )
        return

    columns = st.columns(3)
    with columns[0]:
        project = st.selectbox(
            "Проект", ["Все проекты"] + sorted(state["проекты"]),
            format_func=lambda code: code if code == "Все проекты"
            else model.project_title(state, code),
        )
    with columns[1]:
        employee = st.selectbox(
            "Сотрудник", ["Все сотрудники"] + sorted(state["сотрудники"]),
            format_func=lambda code: code if code == "Все сотрудники"
            else model.employee_title(state, code),
        )
    with columns[2]:
        status = st.multiselect("Статус", model.STATUS_TASK)

    tasks = model.tasks_for(
        state,
        project=None if project == "Все проекты" else project,
        employee=None if employee == "Все сотрудники" else employee,
        status=status or None,
    )

    st.markdown(f'<div class="cab-card"><h3>В выборке задач: {len(tasks)}</h3>'
                '<div class="cab-note">Файл открывается в Excel: кодировка UTF-8, '
                "разделитель «;»</div></div>", unsafe_allow_html=True)
    if not tasks:
        st.info("Под выбранные фильтры не попала ни одна задача.")
        return
    st.download_button(
        "⬇️ Скачать выборку (CSV)",
        data=model.tasks_to_csv(state, tasks),
        file_name="zadachi_vygruzka.csv",
        mime="text/csv",
        type="primary",
    )
    rows = [{
        "Код": task["код"],
        "Задача": task.get("название") or "—",
        "Проект": model.project_title(state, task.get("код_проекта")),
        "Ответственный": model.employee_title(state, task.get("код_ответственного")),
        "Статус": task.get("статус") or "—",
        "Срок": task.get("срок") or "—",
    } for task in tasks]
    st.dataframe(style_status_column(pd.DataFrame(rows)),
                 width='stretch', hide_index=True)

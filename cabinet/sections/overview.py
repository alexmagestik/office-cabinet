"""Раздел «Обзор»: три показателя по отфильтрованным задачам."""

from datetime import date

import streamlit as st

from .. import model
from ..components import empty_state, header, metric


def render(state: dict) -> None:
    header(
        "Рабочий кабинет",
        "Обзор",
        "Показатели по задачам с учётом контрольной даты",
    )

    if not state["задачи"]:
        empty_state(
            "📊",
            "Пока нечего показывать",
            "Показатели заполнятся после загрузки рабочего плана в разделе «Задачи».",
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
        try:
            current = date.fromisoformat(state["контрольная_дата"])
        except (TypeError, ValueError):
            current = date(2026, 11, 9)
        control_date = st.date_input("Контрольная дата", value=current)

    tasks = model.tasks_for(
        state,
        project=None if project == "Все проекты" else project,
        employee=None if employee == "Все сотрудники" else employee,
    )
    control_iso = control_date.isoformat()
    state["контрольная_дата"] = control_iso
    overdue = [task for task in tasks if model.is_overdue(task, control_iso)]
    done = [task for task in tasks if task.get("статус") == "Выполнена"]

    columns = st.columns(3)
    with columns[0]:
        metric("Всего задач", str(len(tasks)),
               f"В выбранной области · контрольная дата {control_date.strftime('%d.%m.%Y')}")
    with columns[1]:
        metric("Выполнено задач", str(len(done)), "Статус «Выполнена»")
    with columns[2]:
        metric("Просрочено задач", str(len(overdue)),
               f"Срок строго раньше {control_date.strftime('%d.%m.%Y')}")

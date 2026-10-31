"""Раздел «Задачи»: загрузка рабочего плана (XLSX), фильтры, таблица
и изменение статуса выбранной задачи. Исходные коды записей сохраняются."""

import pandas as pd
import streamlit as st

from .. import model
from ..components import empty_state, header, status_chip, style_status_column


def render(state: dict) -> None:
    header(
        "Рабочий кабинет",
        "Задачи",
        "Реестр задач по проектам с кодами записей TSK-XXX",
    )

    _upload_block(state)

    if not state["задачи"]:
        empty_state(
            "🗂️",
            "Список задач пуст",
            "Загрузите рабочий план XLSX с листами «Проекты», «Сотрудники», "
            "«Задачи» и «Встречи». Данные хранятся только в этом сеансе.",
        )
        return

    left, right = st.columns(2)
    with left:
        project = st.selectbox(
            "Проект", ["Все проекты"] + sorted(state["проекты"]),
            format_func=lambda code: code if code == "Все проекты"
            else model.project_title(state, code),
        )
    with right:
        employee = st.selectbox(
            "Сотрудник", ["Все сотрудники"] + sorted(state["сотрудники"]),
            format_func=lambda code: code if code == "Все сотрудники"
            else model.employee_title(state, code),
        )

    tasks = model.tasks_for(
        state,
        project=None if project == "Все проекты" else project,
        employee=None if employee == "Все сотрудники" else employee,
    )

    rows = [{
        "Код": task["код"],
        "Задача": task.get("название") or "—",
        "Проект": model.project_title(state, task.get("код_проекта")),
        "Ответственный": model.employee_title(state, task.get("код_ответственного")),
        "Статус": task.get("статус") or "—",
        "Приоритет": task.get("приоритет") or "—",
        "Дата плана": task.get("дата_плана") or "—",
        "Срок": task.get("срок") or "—",
    } for task in tasks]
    st.markdown(f'<div class="cab-card"><h3>Найдено задач: {len(rows)}</h3>'
                '<div class="cab-note">Цвет строки статуса: серо-голубой — новая, '
                "синий — в работе, янтарный — ожидает, зелёный — выполнена, "
                "серый — отменена</div>"
                "</div>", unsafe_allow_html=True)
    if rows:
        st.dataframe(style_status_column(pd.DataFrame(rows)),
                     width='stretch', hide_index=True)
    else:
        st.info("Под выбранные фильтры не попала ни одна задача.")

    _status_change_block(state, tasks)


def _upload_block(state: dict) -> None:
    with st.expander("⬆️ Загрузка рабочего плана (XLSX) — заменяет текущий набор",
                     expanded=not state["задачи"]):
        uploaded = st.file_uploader(
            "Файл плана с листами «Проекты», «Сотрудники», «Задачи», «Встречи»",
            type=["xlsx"], key="plan_xlsx",
        )
        if uploaded and st.button("Проверить и заменить данные", type="primary"):
            errors, parsed = model.parse_workbook(uploaded.getvalue())
            if errors:
                for message in errors[:15]:
                    st.error(message)
                if len(errors) > 15:
                    st.error(f"Всего ошибок: {len(errors)}. Текущие данные не изменены.")
            else:
                counts = ", ".join(f"{name}: {len(parsed[key])}" for name, key in
                                   (("проектов", "проекты"), ("сотрудников", "сотрудники"),
                                    ("задач", "задачи"), ("встреч", "встречи")))
                model.apply_workbook(state, parsed)
                st.success(f"Данные заменены из файла «{uploaded.name}» ({counts}).")
                st.rerun()


def _status_change_block(state: dict, tasks: list[dict]) -> None:
    st.markdown('<div class="cab-card"><h3>Изменение статуса</h3>'
                '<div class="cab-note">Код задачи сохраняется, меняется только статус</div>'
                "</div>", unsafe_allow_html=True)
    if not tasks:
        st.caption("Нет задач в выбранной области.")
        return
    columns = st.columns([3, 2, 2])
    with columns[0]:
        codes = [task["код"] for task in tasks]
        selected_code = st.selectbox(
            "Задача", codes,
            format_func=lambda code: (
                f"{code} · {state['задачи'][code].get('название') or '—'}"
                if code in state["задачи"] else code),
        )
        selected = state["задачи"][selected_code]
        st.markdown(
            f"Текущий статус: {status_chip(selected.get('статус') or '—')}.",
            unsafe_allow_html=True,
        )
    with columns[1]:
        new_status = st.selectbox("Новый статус", model.STATUS_TASK,
                                  index=model.STATUS_TASK.index(selected["статус"])
                                  if selected.get("статус") in model.STATUS_TASK else 0)
    with columns[2]:
        apply_clicked = st.button("Изменить статус", type="primary",
                                  width='stretch')
    if apply_clicked:
        if new_status == selected.get("статус"):
            st.info(f"У задачи {selected['код']} уже статус «{new_status}».")
        else:
            state["задачи"][selected["код"]]["статус"] = new_status
            st.success(f"Статус задачи {selected['код']} изменён на «{new_status}».")
            st.rerun()

"""Раздел «Материалы»: загрузка DOCX/TXT, привязка к проекту, список
и скачивание оригинала. Содержимое файлов не исполняется и не разбирается."""

import streamlit as st

from .. import model
from ..components import empty_state, header


def render(state: dict) -> None:
    header(
        "Рабочий кабинет",
        "Материалы",
        "Документы сеанса, привязанные к проектам по кодам PR-XXX",
    )

    _upload_block(state)

    if not state["материалы"]:
        empty_state(
            "📎",
            "Материалы ещё не добавлены",
            "Поддерживаются файлы DOCX и TXT до 5 МБ каждый, всего до 20 МБ. "
            "Оригиналы хранятся только в сеансе и попадают в резервную копию.",
        )
        return

    st.markdown(f'<div class="cab-card"><h3>Материалов: {len(state["материалы"])}</h3>'
                f'<div class="cab-note">Занято '
                f"{model.materials_total_bytes(state) / 1024 / 1024:.1f} МБ из 20 МБ</div>"
                "</div>", unsafe_allow_html=True)

    rows = [{
        "Файл": name,
        "Проект": model.project_title(state, item.get("код_проекта")),
        "Размер": f"{item['размер_байт'] / 1024:.0f} КБ",
    } for name, item in sorted(state["материалы"].items())]
    st.dataframe(rows, width='stretch', hide_index=True)

    columns = st.columns(2)
    with columns[0]:
        selected = st.selectbox("Файл для скачивания", sorted(state["материалы"]))
    with columns[1]:
        project = st.selectbox(
            "Привязать к проекту",
            ["—"] + sorted(state["проекты"]),
            index=(sorted(state["проекты"]).index(state["материалы"][selected]["код_проекта"]) + 1
                   if state["материалы"][selected].get("код_проекта") in state["проекты"] else 0),
            format_func=lambda code: code if code == "—"
            else model.project_title(state, code),
        )
    st.download_button(
        "⬇️ Скачать оригинал",
        data=state["файлы"][selected],
        file_name=selected,
        width='stretch',
    )
    if st.button("Сохранить привязку к проекту"):
        model.set_material_project(
            state, selected, None if project == "—" else project)
        st.success("Привязка сохранена.")
        st.rerun()


def _upload_block(state: dict) -> None:
    with st.expander("⬆️ Добавить материалы (DOCX, TXT)", expanded=not state["материалы"]):
        if not state["проекты"]:
            st.warning("Сначала загрузите рабочий план в разделе «Задачи», "
                       "чтобы привязывать материалы к проектам.")
        project = None
        if state["проекты"]:
            project = st.selectbox(
                "Проект для загружаемых файлов", ["—"] + sorted(state["проекты"]),
                format_func=lambda code: code if code == "—"
                else model.project_title(state, code),
            )
        uploaded = st.file_uploader(
            "Файлы DOCX и TXT, до 5 МБ каждый (всего до 20 МБ)",
            type=["docx", "txt"], accept_multiple_files=True, key="material_files",
        )
        if uploaded and st.button("Загрузить материалы", type="primary"):
            added, failed = 0, []
            for file in uploaded:
                error = model.add_material(
                    state, file.name, file.getvalue(),
                    None if project in (None, "—") else project)
                if error:
                    failed.append(error)
                else:
                    added += 1
            if added:
                st.success(f"Загружено файлов: {added}.")
            for message in failed:
                st.error(message)
            if added:
                st.rerun()

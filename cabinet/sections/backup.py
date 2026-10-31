"""Раздел «Резервная копия»: ZIP со всеми данными и материалами,
проверка и подтверждение при восстановлении. Архив обрабатывается в памяти."""

import streamlit as st

from .. import model
from ..components import header

REMINDER = ("Перед выходом скачайте резервную копию. При следующем посещении "
            "загрузите её. Автосохранения между посещениями нет.")


def render(state: dict) -> None:
    header(
        "Рабочий кабинет",
        "Резервная копия",
        REMINDER,
    )

    st.markdown('<div class="cab-warning" style="margin-bottom:16px;">'
                f"{REMINDER}</div>", unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<div class="cab-card"><h3>Скачивание</h3>'
                    '<div class="cab-note">В архиве: все данные, оригиналы материалов '
                    "и их связи — независимо от фильтров</div></div>", unsafe_allow_html=True)
        if model.has_data(state):
            st.caption(
                f"Проектов: {len(state['проекты'])}, сотрудников: {len(state['сотрудники'])}, "
                f"задач: {len(state['задачи'])}, встреч: {len(state['встречи'])}, "
                f"материалов: {len(state['материалы'])} "
                f"({model.materials_total_bytes(state) / 1024 / 1024:.1f} МБ).")
        else:
            st.caption("Кабинет пуст — архив будет содержать только пустую структуру.")
        st.download_button(
            "⬇️ Скачать резервную копию (ZIP)",
            data=model.build_backup(state),
            file_name="kabinet_rezervnaya_kopiya.zip",
            mime="application/zip",
            type="primary",
            width='stretch',
        )

    with right:
        st.markdown('<div class="cab-card"><h3>Восстановление</h3>'
                    '<div class="cab-note">Проверяются структура, коды, связи и лимиты '
                    "размера; замена — только после подтверждения</div></div>",
                    unsafe_allow_html=True)
        uploaded = st.file_uploader("Файл резервной копии (ZIP)", type=["zip"],
                                    key="backup_zip")
        if uploaded:
            errors, restored = model.validate_backup(uploaded.getvalue())
            if errors:
                for message in errors[:10]:
                    st.error(message)
                st.caption("Некорректный архив — текущие данные не изменены.")
            else:
                st.caption(
                    f"В архиве: проектов {len(restored['проекты'])}, сотрудников "
                    f"{len(restored['сотрудники'])}, задач {len(restored['задачи'])}, "
                    f"встреч {len(restored['встречи'])}, материалов "
                    f"{len(restored['материалы'])}.")
                st.warning("Восстановление заменит все данные текущего сеанса.")
                if st.button("Подтвердить замену данных", type="primary",
                             width='stretch'):
                    st.session_state[model.STATE_KEY] = restored
                    st.success("Данные восстановлены из резервной копии.")
                    st.rerun()

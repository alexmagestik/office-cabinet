"""Раздел «Календарь»: выбор недели и список встреч по дням."""

from datetime import date, timedelta

import streamlit as st

from .. import model
from ..components import empty_state, header

_MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
               "августа", "сентября", "октября", "ноября", "декабря"]
_WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница",
             "суббота", "воскресенье"]


def render(state: dict) -> None:
    header(
        "Рабочий кабинет",
        "Календарь",
        "Встречи проектов по дням выбранной недели",
    )

    meetings = [m for m in state["встречи"].values() if m.get("дата")]
    if not meetings:
        empty_state(
            "📅",
            "Встреч пока нет",
            "Встречи попадают в кабинет вместе с рабочим планом (лист «Встречи») "
            "в разделе «Задачи».",
        )
        return

    mondays = sorted({date.fromisoformat(m["дата"]) - timedelta(
        days=date.fromisoformat(m["дата"]).weekday()) for m in meetings})
    label_to_monday = {_week_label(monday): monday for monday in mondays}
    selected = st.selectbox("Неделя", list(label_to_monday))
    monday = label_to_monday[selected]

    project_filter = st.selectbox(
        "Проект", ["Все проекты"] + sorted(state["проекты"]),
        format_func=lambda code: code if code == "Все проекты"
        else model.project_title(state, code),
    )

    week_meetings = [m for m in meetings
                     if monday <= date.fromisoformat(m["дата"]) <= monday + timedelta(days=6)]
    if project_filter != "Все проекты":
        week_meetings = [m for m in week_meetings if m.get("код_проекта") == project_filter]
    week_meetings.sort(key=lambda m: (m["дата"], m.get("время_начала") or ""))

    st.markdown(f'<div class="cab-card"><h3>Встреч за неделю: {len(week_meetings)}</h3>'
                '<div class="cab-note">Время указано в часовом поясе плана</div>'
                "</div>", unsafe_allow_html=True)
    if not week_meetings:
        st.info("В выбранной неделе встреч нет — выберите другую неделю или проект.")
        return

    current_day = None
    for meeting in week_meetings:
        if meeting["дата"] != current_day:
            current_day = meeting["дата"]
            day = date.fromisoformat(current_day)
            st.markdown(
                f'<div style="font-weight:700;margin:14px 0 4px 0;">'
                f"{_WEEKDAYS[day.weekday()].capitalize()}, "
                f"{day.day} {_MONTHS_GEN[day.month - 1]}</div>",
                unsafe_allow_html=True,
            )
        time = f"{meeting.get('время_начала') or '—'}–{meeting.get('время_окончания') or '—'}"
        participants = ", ".join(model.employee_title(state, code)
                                 for code in meeting.get("участники") or []) or "—"
        st.markdown(
            f"""
            <div class="cab-card" style="margin-bottom:10px;">
              <div style="display:flex;gap:12px;flex-wrap:wrap;">
                <div style="min-width:90px;color:#72539C;font-weight:700;">{time}</div>
                <div style="flex:1;min-width:220px;">
                  <div style="font-weight:600;">{meeting.get('тема') or 'Без темы'}</div>
                  <div style="font-size:13px;color:#758093;margin-top:2px;">
                    {model.project_title(state, meeting.get('код_проекта'))} · {meeting['код']}
                    {" · " + meeting['место'] if meeting.get('место') else ""}</div>
                  <div style="font-size:13px;margin-top:4px;">Участники: {participants}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _week_label(monday: date) -> str:
    sunday = monday + timedelta(days=6)
    return (f"{monday.day} {_MONTHS_GEN[monday.month - 1]} – "
            f"{sunday.day} {_MONTHS_GEN[sunday.month - 1]} {sunday.year}")

"""Переиспользуемые элементы интерфейса: шапки, карточки, пустые состояния."""

import streamlit as st

from . import theme


def header(kicker: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="cab-header">
            <div class="cab-kicker">{kicker}</div>
            <div class="cab-title">{title}</div>
            <div class="cab-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, text: str, hint: str | None = None) -> None:
    hint_html = ""
    if hint:
        hint_html = f'<div style="margin-top:10px;color:{theme.ACCENT};font-size:14px;">{hint}</div>'
    st.markdown(
        f"""
        <div class="cab-empty">
            <div class="cab-empty-icon">{icon}</div>
            <div class="cab-empty-title">{title}</div>
            <div class="cab-empty-text">{text}</div>
            {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric(label: str, value: str, period: str) -> None:
    """Показатель: предмет подсчёта, число по центру и выбранный период."""
    st.markdown(
        f"""
        <div class="cab-metric">
            <div class="cab-metric-label">{label}</div>
            <div class="cab-metric-value">{value}</div>
            <div class="cab-metric-period">{period}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_chip(text: str) -> str:
    """Статус в виде приглушённой метки (для HTML-подписей)."""
    bg, fg = theme.STATUS_COLORS.get(text, ("#F0F1F4", "#8A93A3"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 10px;'
            f'border-radius:999px;font-size:13px;">{text}</span>')


def style_status_column(frame, column: str = "Статус"):
    """Подсветка столбца статуса в таблице (pandas Styler)."""
    def paint(value):
        bg, fg = theme.STATUS_COLORS.get(value, ("", ""))
        return f"background-color: {bg}; color: {fg};" if bg else ""
    return frame.style.map(paint, subset=[column])

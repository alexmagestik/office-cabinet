"""Цветовая схема и стили «Рабочего кабинета» по требованиям design_reference."""

BG = "#F5F6FA"          # фон страницы
SURFACE = "#FFFFFF"     # основные поверхности
TEXT = "#263043"        # основной текст
MUTED = "#758093"       # второстепенный текст
ACCENT = "#72539C"      # акцент навигации и кнопок
ACCENT_LIGHT = "#EDE8FA"  # светлая выделенная область
WARNING_BG = "#FFF5E8"  # предупреждения о сроках и конфликтах
WARNING_TEXT = "#8A5A18"

# Подсветка статусов задач: приглушённые деловые тона, тёмный текст
STATUS_COLORS = {
    "Новая":     ("#EEF2F8", "#51617A"),   # нейтральный серо-голубой
    "В работе":  ("#E7EFFA", "#3A66A0"),   # спокойный синий
    "Ожидает":   ("#FFF3E2", "#8A5A18"),   # сдержанный янтарный
    "Выполнена": ("#EAF3EC", "#3F7A52"),   # приглушённый зелёный
    "Отменена":  ("#F0F1F4", "#8A93A3"),   # нейтральный серый
}

CSS = f"""
<style>
    /* Общая типографика */
    .stApp {{
        background: {BG};
        color: {TEXT};
        font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    }}
    section[data-testid="stSidebar"] {{
        background: {SURFACE};
        border-right: 1px solid #E6E8EF;
    }}
    h1, h2, h3 {{ color: {TEXT}; }}

    /* Верхняя «шапка» раздела */
    .cab-header {{
        margin: 0 0 18px 0;
        padding: 18px 22px;
        background: {SURFACE};
        border: 1px solid #E6E8EF;
        border-radius: 14px;
    }}
    .cab-header .cab-kicker {{
        font-size: 12px;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: {MUTED};
        margin-bottom: 4px;
    }}
    .cab-header .cab-title {{
        font-size: 26px;
        font-weight: 700;
        color: {TEXT};
    }}
    .cab-header .cab-subtitle {{
        font-size: 14px;
        color: {MUTED};
        margin-top: 4px;
    }}

    /* Карточка-поверхность */
    .cab-card {{
        background: {SURFACE};
        border: 1px solid #E6E8EF;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }}
    .cab-card h3 {{
        margin: 0 0 4px 0;
        font-size: 18px;
    }}
    .cab-card .cab-note {{
        font-size: 13px;
        color: {MUTED};
        margin-bottom: 12px;
    }}

    /* Показатель: число строго по центру, с предметом подсчёта и периодом */
    .cab-metric {{
        background: {SURFACE};
        border: 1px solid #E6E8EF;
        border-radius: 14px;
        padding: 16px 12px;
        text-align: center;
    }}
    .cab-metric .cab-metric-label {{
        font-size: 14px;
        color: {TEXT};
    }}
    .cab-metric .cab-metric-value {{
        font-size: 30px;
        font-weight: 700;
        color: {TEXT};
        text-align: center;
        margin: 6px 0;
    }}
    .cab-metric .cab-metric-period {{
        font-size: 12px;
        color: {MUTED};
    }}

    /* Статусные метки */
    .cab-chip {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 13px;
        background: {ACCENT_LIGHT};
        color: {ACCENT};
    }}
    .cab-chip-warning {{
        background: {WARNING_BG};
        color: {WARNING_TEXT};
    }}

    /* Предупреждение о сроках и конфликтах */
    .cab-warning {{
        background: {WARNING_BG};
        color: {TEXT};
        border-radius: 12px;
        padding: 12px 16px;
        font-size: 14px;
    }}

    /* Пустое состояние */
    .cab-empty {{
        background: {SURFACE};
        border: 1px dashed #C9CEDE;
        border-radius: 14px;
        padding: 36px 24px;
        text-align: center;
    }}
    .cab-empty .cab-empty-icon {{ font-size: 34px; margin-bottom: 8px; }}
    .cab-empty .cab-empty-title {{
        font-size: 17px;
        font-weight: 700;
        color: {TEXT};
        margin-bottom: 6px;
    }}
    .cab-empty .cab-empty-text {{
        font-size: 14px;
        color: {MUTED};
        max-width: 560px;
        margin: 0 auto;
        line-height: 1.5;
    }}

    /* Навигация в сайдбаре */
    section[data-testid="stSidebar"] .nav-item-active {{
        background: {ACCENT_LIGHT};
        border-radius: 10px;
    }}

    /* Компактность таблиц на телефоне: горизонтальная прокрутка */
    div[data-testid="stDataFrame"] {{ overflow-x: auto; }}

    /* Напоминание о резервной копии в основной области — только на узком
       экране, где сайдбар свёрнут и напоминание в нём не видно */
    .cab-mobile-reminder {{
        display: none;
        background: {WARNING_BG};
        color: {TEXT};
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 13px;
        line-height: 1.5;
        margin-bottom: 12px;
    }}

    /* --- Мобильная версия --- */
    @media (max-width: 640px) {{
        .cab-mobile-reminder {{ display: block; }}

        .cab-header {{ padding: 14px 16px; }}
        .cab-header .cab-title {{ font-size: 22px; }}
        .cab-header .cab-subtitle {{ font-size: 13px; }}
        .cab-card {{ padding: 14px 14px; }}
        .cab-card h3 {{ font-size: 16px; }}

        /* Показатели в одну колонку, числа по центру, подписи не слипаются */
        .cab-metric {{ margin-bottom: 10px; }}
        .cab-metric .cab-metric-value {{ font-size: 26px; }}

        /* Уверенный выбор пальцем: элементы от 44 px, без авто-зума iOS */
        .stApp button {{
            min-height: 44px;
            font-size: 15px;
        }}
        .stApp input, .stApp textarea {{
            font-size: 16px;
        }}
        .stApp [data-baseweb="select"] > div {{
            min-height: 44px;
        }}
        /* Поля даты и загрузки файлов не сжимаются в узкую полоску */
        .stApp [data-testid="stDateInput"] input,
        .stApp [data-testid="stFileUploaderDropzone"] {{
            min-height: 44px;
        }}

        /* Длинные названия переносятся, а не обрезаются поверх соседних */
        .cab-card, .cab-header, .cab-metric {{ overflow-wrap: anywhere; }}
    }}
</style>
"""

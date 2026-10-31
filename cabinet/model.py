"""Единая модель данных «Рабочего кабинета».

Данные пользователя живут в сеансе (st.session_state): проекты, сотрудники,
задачи, встречи и материалы. Коды записей (PR-, EMP-, TSK-, MTG-) сохраняются
в исходном виде и служат ключами связей. Автосохранения между посещениями нет —
только резервная копия (ZIP).
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

STATE_KEY = "cabinet_state"

STATUS_TASK = ["Новая", "В работе", "Ожидает", "Выполнена", "Отменена"]
PRIORITY = ["Низкий", "Средний", "Высокий"]

CODE_RE = {
    "проекты": re.compile(r"^PR-\d+$"),
    "сотрудники": re.compile(r"^EMP-\d+$"),
    "задачи": re.compile(r"^TSK-\d+$"),
    "встречи": re.compile(r"^MTG-\d+$"),
}

# Обязательные столбцы листов рабочего плана (остальные столбцы игнорируются)
SHEET_COLUMNS = {
    "Сотрудники": ["Код сотрудника", "ФИО"],
    "Проекты": ["Код проекта", "Название проекта", "Код владельца", "Статус"],
    "Задачи": ["Код задачи", "Код проекта", "Название задачи", "Код ответственного",
               "Статус", "Дата плана", "Срок"],
    "Встречи": ["Код встречи", "Код проекта", "Тема встречи", "Дата",
                "Начало", "Окончание", "Коды участников"],
}

MAX_FILE_BYTES = 5 * 1024 * 1024     # лимит на файл материала
MAX_TOTAL_BYTES = 20 * 1024 * 1024   # лимит на все материалы сеанса

DEFAULT_CONTROL_DATE = "2026-11-09"


# --------------------------------------------------------------------------
# Состояние сеанса
# --------------------------------------------------------------------------

def empty_state() -> dict:
    return {
        "версия": 2,
        "контрольная_дата": DEFAULT_CONTROL_DATE,
        "проекты": {},     # код -> {код, название, владелец, статус, описание}
        "сотрудники": {},  # код -> {код, имя, роль, отдел}
        "задачи": {},      # код -> {код, код_проекта, название, код_ответственного,
        #                            статус, приоритет, дата_плана, срок,
        #                            дата_завершения, план_ч, комментарий}
        "встречи": {},     # код -> {код, код_проекта, тема, дата, время_начала,
        #                            время_окончания, место, участники}
        "материалы": {},   # имя файла -> {название, файл, код_проекта, размер_байт}
        "файлы": {},       # имя файла -> bytes (только сеанс, в копию идёт в ZIP)
    }


def get_state() -> dict:
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = empty_state()
    return st.session_state[STATE_KEY]


def reset_state() -> None:
    st.session_state[STATE_KEY] = empty_state()


def has_data(state: dict) -> bool:
    return bool(state["проекты"] or state["задачи"] or state["встречи"]
                or state["сотрудники"] or state["материалы"])


# --------------------------------------------------------------------------
# Справочные подстановки и выборки
# --------------------------------------------------------------------------

def project_title(state: dict, code: str | None) -> str:
    if not code:
        return "—"
    project = state["проекты"].get(code)
    return f"{code} · {project['название']}" if project else code


def employee_title(state: dict, code: str | None) -> str:
    if not code:
        return "—"
    employee = state["сотрудники"].get(code)
    return employee["имя"] if employee else code


def tasks_for(state: dict, *, project: str | None = None,
              employee: str | None = None, status: list[str] | None = None) -> list[dict]:
    result = []
    for task in state["задачи"].values():
        if project and task.get("код_проекта") != project:
            continue
        if employee and task.get("код_ответственного") != employee:
            continue
        if status and task.get("статус") not in status:
            continue
        result.append(task)
    return sorted(result, key=lambda t: t["код"])


def is_overdue(task: dict, control_date: str) -> bool:
    """Просрочена: незавершённая и неотменённая задача со сроком строго
    раньше контрольной даты."""
    if task.get("статус") in ("Выполнена", "Отменена"):
        return False
    deadline = task.get("срок")
    return bool(deadline and deadline < control_date)


def materials_total_bytes(state: dict) -> int:
    return sum(item["размер_байт"] for item in state["материалы"].values())


# --------------------------------------------------------------------------
# Загрузка рабочего плана (XLSX) с валидацией; при ошибке данные не меняются
# --------------------------------------------------------------------------

def _cell(row: dict, column: str) -> str:
    value = row.get(column)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _parse_date(value, column: str, context: str, errors: list[str]) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    errors.append(f"{context}: в поле «{column}» значение «{text}» не является датой.")
    return None


def _parse_time(value, column: str, context: str, errors: list[str]) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%H:%M")
    if hasattr(value, "strftime"):  # datetime.time
        return value.strftime("%H:%M")
    text = str(value).strip()
    if re.match(r"^\d{1,2}:\d{2}$", text):
        return text.zfill(5)
    errors.append(f"{context}: в поле «{column}» значение «{text}» не является временем (ЧЧ:ММ).")
    return None


def parse_workbook(raw: bytes) -> tuple[list[str], dict | None]:
    """Полная проверка XLSX. Возвращает (ошибки, разобранные данные).
    Данные возвращаются только если ошибок нет; текущий набор не меняется."""
    errors: list[str] = []
    try:
        book = pd.read_excel(io.BytesIO(raw), sheet_name=None, engine="openpyxl")
    except Exception as error:  # повреждённый файл, не XLSX и т.п.
        return [f"Не удалось прочитать файл: {error}"], None

    missing = [name for name in SHEET_COLUMNS if name not in book]
    if missing:
        errors.append("Отсутствуют листы: " + ", ".join(f"«{name}»" for name in missing) + ".")
    for name, columns in SHEET_COLUMNS.items():
        if name in book:
            absent = [c for c in columns if c not in book[name].columns]
            if absent:
                errors.append(f"Лист «{name}»: нет столбцов " + ", ".join(f"«{c}»" for c in absent) + ".")
    if errors:
        return errors, None

    parsed = {"сотрудники": {}, "проекты": {}, "задачи": {}, "встречи": {}}

    def unique_code(sheet: str, code: str, storage: dict) -> bool:
        if not CODE_RE[sheet].match(code):
            errors.append(f"Лист «{sheet}»: код «{code}» не соответствует формату.")
            return False
        if code in storage:
            errors.append(f"Лист «{sheet}»: код {code} повторяется.")
            return False
        return True

    for _, row in book["Сотрудники"].iterrows():
        row = row.to_dict()
        code = _cell(row, "Код сотрудника")
        if not code:
            continue
        if not unique_code("сотрудники", code, parsed["сотрудники"]):
            continue
        parsed["сотрудники"][code] = {
            "код": code,
            "имя": _cell(row, "ФИО") or code,
            "роль": _cell(row, "Должность") or None,
            "отдел": _cell(row, "Подразделение") or None,
        }

    for _, row in book["Проекты"].iterrows():
        row = row.to_dict()
        code = _cell(row, "Код проекта")
        if not code:
            continue
        if not unique_code("проекты", code, parsed["проекты"]):
            continue
        owner = _cell(row, "Код владельца") or None
        if owner and owner not in parsed["сотрудники"]:
            errors.append(f"Проект {code}: владелец {owner} отсутствует среди сотрудников.")
            continue
        parsed["проекты"][code] = {
            "код": code,
            "название": _cell(row, "Название проекта") or code,
            "владелец": owner,
            "статус": _cell(row, "Статус") or None,
            "описание": _cell(row, "Цель проекта") or None,
        }

    for _, row in book["Задачи"].iterrows():
        row = row.to_dict()
        code = _cell(row, "Код задачи")
        if not code:
            continue
        if not unique_code("задачи", code, parsed["задачи"]):
            continue
        project = _cell(row, "Код проекта") or None
        employee = _cell(row, "Код ответственного") or None
        context = f"Задача {code}"
        if project not in parsed["проекты"]:
            errors.append(f"{context}: проект {project or '—'} отсутствует на листе «Проекты».")
            continue
        if employee not in parsed["сотрудники"]:
            errors.append(f"{context}: сотрудник {employee or '—'} отсутствует на листе «Сотрудники».")
            continue
        parsed["задачи"][code] = {
            "код": code,
            "код_проекта": project,
            "название": _cell(row, "Название задачи") or None,
            "код_ответственного": employee,
            "статус": _cell(row, "Статус") or "Новая",
            "приоритет": _cell(row, "Приоритет") or "Средний",
            "дата_плана": _parse_date(row.get("Дата плана"), "Дата плана", context, errors),
            "срок": _parse_date(row.get("Срок"), "Срок", context, errors),
            "дата_завершения": _parse_date(row.get("Дата завершения"), "Дата завершения", context, errors),
            "план_ч": _parse_hours(row.get("План, ч"), context, errors),
            "комментарий": _cell(row, "Комментарий") or None,
        }

    for _, row in book["Встречи"].iterrows():
        row = row.to_dict()
        code = _cell(row, "Код встречи")
        if not code:
            continue
        if not unique_code("встречи", code, parsed["встречи"]):
            continue
        context = f"Встреча {code}"
        project = _cell(row, "Код проекта") or None
        if project not in parsed["проекты"]:
            errors.append(f"{context}: проект {project or '—'} отсутствует на листе «Проекты».")
            continue
        participants = [p.strip() for p in _cell(row, "Коды участников").split(";") if p.strip()]
        unknown = [p for p in participants if p not in parsed["сотрудники"]]
        if unknown:
            errors.append(f"{context}: участники {', '.join(unknown)} отсутствуют среди сотрудников.")
            continue
        parsed["встречи"][code] = {
            "код": code,
            "код_проекта": project,
            "тема": _cell(row, "Тема встречи") or None,
            "дата": _parse_date(row.get("Дата"), "Дата", context, errors),
            "время_начала": _parse_time(row.get("Начало"), "Начало", context, errors),
            "время_окончания": _parse_time(row.get("Окончание"), "Окончание", context, errors),
            "место": _cell(row, "Место") or None,
            "участники": participants,
        }

    if errors:
        return errors, None
    if not (parsed["задачи"] or parsed["проекты"] or parsed["сотрудники"] or parsed["встречи"]):
        return ["Файл не содержит ни одной записи."], None
    return [], parsed


def _parse_hours(value, context: str, errors: list[str]) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return None
    try:
        return round(float(str(value).replace(",", ".")), 2)
    except ValueError:
        errors.append(f"{context}: в поле «План, ч» значение «{value}» не является числом.")
        return None


def apply_workbook(state: dict, parsed: dict) -> None:
    """Замена набора проектов, сотрудников, задач и встреч на данные файла.
    Материалы остаются; ссылка на удалённый проект снимается."""
    state["проекты"] = parsed["проекты"]
    state["сотрудники"] = parsed["сотрудники"]
    state["задачи"] = parsed["задачи"]
    state["встречи"] = parsed["встречи"]
    for item in state["материалы"].values():
        if item.get("код_проекта") and item["код_проекта"] not in state["проекты"]:
            item["код_проекта"] = None


# --------------------------------------------------------------------------
# Материалы
# --------------------------------------------------------------------------

def add_material(state: dict, filename: str, data: bytes,
                 project_code: str | None) -> str | None:
    """Добавление материала; возвращает текст ошибки или None."""
    if len(data) > MAX_FILE_BYTES:
        return f"Файл «{filename}» больше 5 МБ."
    if materials_total_bytes(state) + len(data) > MAX_TOTAL_BYTES:
        return f"Файл «{filename}» не помещается: суммарный лимит материалов — 20 МБ."
    if filename in state["материалы"]:
        return f"Файл «{filename}» уже загружен."
    state["материалы"][filename] = {
        "название": filename,
        "файл": filename,
        "код_проекта": project_code,
        "размер_байт": len(data),
    }
    state["файлы"][filename] = data
    return None


def set_material_project(state: dict, filename: str, project_code: str | None) -> None:
    if filename in state["материалы"]:
        state["материалы"][filename]["код_проекта"] = project_code


# --------------------------------------------------------------------------
# Резервная копия: ZIP собирается и разбирается в памяти
# --------------------------------------------------------------------------

def build_backup(state: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        payload = {key: value for key, value in state.items() if key != "файлы"}
        archive.writestr("данные.json",
                         json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        for filename, data in state["файлы"].items():
            archive.writestr(f"материалы/{filename}", data)
    return buffer.getvalue()


def validate_backup(raw: bytes) -> tuple[list[str], dict | None]:
    """Проверка ZIP: структура, коды, связи, лимиты размера.
    Возвращает (ошибки, восстановленное состояние). Архив обрабатывается
    в памяти, без извлечения на диск."""
    errors: list[str] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return ["Файл не является ZIP-архивом."], None

    names = archive.namelist()
    if "данные.json" not in names:
        return ["В архиве нет файла «данные.json»."], None
    material_names = [n for n in names if n != "данные.json"]
    bad = [n for n in material_names
           if not n.startswith("материалы/") or n.startswith("/") or ".." in n]
    if bad:
        errors.append("В архиве посторонние записи: " + ", ".join(bad[:3]))
    if errors:
        return errors, None

    try:
        payload = json.loads(archive.read("данные.json").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"Файл «данные.json» повреждён: {error}."], None

    known_keys = set(empty_state()) - {"файлы"}
    unknown_keys = set(payload) - known_keys
    missing_keys = known_keys - set(payload)
    if unknown_keys:
        errors.append("Неизвестные разделы данных: " + ", ".join(sorted(unknown_keys)) + ".")
    if missing_keys:
        errors.append("Отсутствуют разделы данных: " + ", ".join(sorted(missing_keys)) + ".")
    if errors:
        return errors, None

    restored = empty_state()
    restored["контрольная_дата"] = payload["контрольная_дата"]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(restored["контрольная_дата"])):
        errors.append(f"Контрольная дата «{restored['контрольная_дата']}» не является датой.")

    entity_codes = {}
    for entity, pattern in CODE_RE.items():
        storage = payload[entity]
        if not isinstance(storage, dict):
            errors.append(f"Раздел «{entity}» должен быть списком записей по кодам.")
            continue
        codes = {}
        for code, item in storage.items():
            if not isinstance(code, str) or not pattern.match(code):
                errors.append(f"Раздел «{entity}»: неверный код «{code}».")
                continue
            if code in codes:
                errors.append(f"Раздел «{entity}»: код {code} повторяется.")
                continue
            if not isinstance(item, dict) or item.get("код") != code:
                errors.append(f"Раздел «{entity}»: запись {code} не содержит собственного кода.")
                continue
            codes[code] = item
        entity_codes[entity] = codes
        restored[entity] = codes
    if errors:
        return errors, None

    for code, task in entity_codes["задачи"].items():
        if task.get("код_проекта") and task["код_проекта"] not in entity_codes["проекты"]:
            errors.append(f"Задача {code}: ссылка на несуществующий проект.")
        if task.get("код_ответственного") and task["код_ответственного"] not in entity_codes["сотрудники"]:
            errors.append(f"Задача {code}: ссылка на несуществующего сотрудника.")
    for code, meeting in entity_codes["встречи"].items():
        if meeting.get("код_проекта") and meeting["код_проекта"] not in entity_codes["проекты"]:
            errors.append(f"Встреча {code}: ссылка на несуществующий проект.")
        for participant in meeting.get("участники", []):
            if participant not in entity_codes["сотрудники"]:
                errors.append(f"Встреча {code}: участник {participant} не существует.")
    for code, project in entity_codes["проекты"].items():
        if project.get("владелец") and project["владелец"] not in entity_codes["сотрудники"]:
            errors.append(f"Проект {code}: владелец не существует.")
    if errors:
        return errors, None

    files: dict[str, bytes] = {}
    total = 0
    for filename, item in payload["материалы"].items():
        entry_name = f"материалы/{filename}"
        if entry_name not in names:
            errors.append(f"В архиве нет файла материала «{filename}».")
            continue
        data = archive.read(entry_name)
        if len(data) > MAX_FILE_BYTES:
            errors.append(f"Материал «{filename}» больше 5 МБ.")
            continue
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            errors.append("Суммарный размер материалов превышает 20 МБ.")
            break
        if item.get("код_проекта") and item["код_проекта"] not in entity_codes["проекты"]:
            errors.append(f"Материал «{filename}»: ссылка на несуществующий проект.")
            continue
        files[filename] = data
        restored["материалы"][filename] = item
    if errors:
        return errors, None

    restored["файлы"] = files
    return [], restored


# --------------------------------------------------------------------------
# Выгрузка CSV (UTF-8 BOM, разделитель «;»)
# --------------------------------------------------------------------------

CSV_COLUMNS = ["Код задачи", "Код проекта", "Название задачи", "Код ответственного",
               "Статус", "Приоритет", "Дата плана", "Срок", "Дата завершения",
               "План, ч", "Комментарий"]


def _csv_cell(value) -> str:
    text = "" if value is None else str(value)
    if any(ch in text for ch in (";", '"', "\n")):
        text = '"' + text.replace('"', '""') + '"'
    return text


def tasks_to_csv(state: dict, tasks: list[dict]) -> bytes:
    lines = [";".join(CSV_COLUMNS)]
    for task in tasks:
        lines.append(";".join(_csv_cell(task.get(key)) for key in
                              ("код", "код_проекта", "название", "код_ответственного",
                               "статус", "приоритет", "дата_плана", "срок",
                               "дата_завершения", "план_ч", "комментарий")))
    return ("\ufeff" + "\n".join(lines)).encode("utf-8")

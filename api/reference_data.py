"""Справочные данные для Mini App: типы проектов, ролей, навыки и т.п.
Возвращаются на /api/refs, фронт рендерит из них чипы и селекты."""
from __future__ import annotations

from typing import TypedDict


class RefItem(TypedDict):
    code: str
    label: str


def _items(pairs: list[tuple[str, str]]) -> list[RefItem]:
    return [{"code": c, "label": l} for c, l in pairs]


GENDERS = _items([
    ("male", "Мужской"),
    ("female", "Женский"),
])

PROJECT_TYPES = _items([
    ("kino_serial", "Кино и сериалы"),
    ("advertising", "Реклама"),
    ("model_projects", "Модельные проекты"),
    ("show_reality", "Шоу, реалити и интернет"),
    ("voice_dub", "Озвучка / дубляж"),
    ("theater", "Театр, спектакль, мюзикл"),
])

ROLE_TYPES = _items([
    ("main", "Главная"),
    ("supporting", "Второстепенная"),
    ("episode", "Эпизод"),
    ("massovka", "Массовка"),
    ("groupovka", "Групповка"),
    ("dubler", "Дублёр"),
    ("kaskader", "Каскадёр"),
    ("model", "Модель"),
    ("photo_model", "Фотомодель"),
    ("promo_model", "Промо модель"),
    ("tv_host", "Ведущий (ТВ-передачи)"),
    ("diktor", "Диктор"),
    ("dancer", "Танцор"),
    ("ballerina", "Балерина"),
    ("gymnast", "Гимнастка"),
    ("vocalist", "Вокалист"),
    ("musician", "Музыкант"),
])

ETHNICITY = _items([
    ("slavic", "Славянский"),
    ("caucasian", "Кавказский"),
    ("asian", "Азиатский"),
    ("central_asian", "Среднеазиатский"),
    ("african", "Африканский"),
    ("arab", "Арабский"),
    ("latin", "Латино"),
    ("mixed", "Смешанный"),
    ("other", "Другой"),
])

BODY_TYPE = _items([
    ("slim", "Худощавое"),
    ("athletic", "Спортивное"),
    ("normal", "Среднее"),
    ("plus_size", "Пышное / plus-size"),
    ("muscular", "Накачанное"),
])

HAIR_COLORS = _items([
    ("black", "Чёрные"),
    ("dark_brown", "Тёмно-русые"),
    ("brown", "Каштановые"),
    ("light_brown", "Русые"),
    ("blond", "Блонд"),
    ("red", "Рыжие"),
    ("grey", "Седые"),
    ("dyed", "Окрашенные"),
])

HAIR_LENGTHS = _items([
    ("bald", "Лысый / бритый"),
    ("very_short", "Очень короткие"),
    ("short", "Короткие"),
    ("medium", "Средние"),
    ("long", "Длинные"),
    ("very_long", "Очень длинные"),
])

EDUCATION = _items([
    ("vuz", "Профильный ВУЗ"),
    ("courses", "Курсы"),
    ("vuz_courses", "ВУЗ + Курсы"),
    ("none", "Нет профильного образования"),
])

TAX_STATUS = _items([
    ("self_employed", "Самозанятый"),
    ("ip", "ИП"),
    ("individual", "Физлицо"),
])

EYE_COLORS = _items([
    ("brown", "Карие"),
    ("blue", "Голубые"),
    ("green", "Зелёные"),
    ("grey", "Серые"),
    ("hazel", "Ореховые"),
    ("mixed", "Смешанные"),
])

MARKS = _items([
    ("tattoo", "Татуировки"),
    ("piercing", "Пирсинг"),
    ("scars", "Шрамы"),
    ("freckles", "Веснушки"),
    ("braces", "Брекеты"),
    ("other", "Другое"),
])

SKILLS_SPORT = _items([
    ("running", "Бег"),
    ("swimming", "Плавание"),
    ("boxing", "Бокс"),
    ("horseback", "Верховая езда"),
    ("fencing", "Фехтование"),
    ("yoga", "Йога"),
    ("gymnastics", "Гимнастика"),
    ("acrobatics", "Акробатика"),
    ("martial_arts", "Боевые искусства"),
    ("football", "Футбол"),
    ("basketball", "Баскетбол"),
    ("tennis", "Теннис"),
])

SKILLS_DANCE = _items([
    ("ballroom", "Бальные"),
    ("contemporary", "Современные"),
    ("hip_hop", "Хип-хоп"),
    ("ballet", "Балет"),
    ("latin", "Латина"),
    ("folk", "Народные"),
    ("step", "Степ"),
    ("breakdance", "Брейк-данс"),
    ("jazz", "Джаз"),
])

SKILLS_VOCAL = _items([
    ("variety", "Эстрадный"),
    ("academic", "Академический"),
    ("rap", "Рэп"),
    ("rock", "Рок"),
    ("jazz", "Джазовый"),
])

SKILLS_INSTRUMENTS = _items([
    ("guitar", "Гитара"),
    ("piano", "Фортепиано"),
    ("violin", "Скрипка"),
    ("drums", "Барабаны"),
    ("saxophone", "Саксофон"),
    ("flute", "Флейта"),
    ("accordion", "Баян/Аккордеон"),
    ("ukulele", "Укулеле"),
])


def all_refs() -> dict[str, list[RefItem]]:
    """Полный словарь справочников для отдачи фронту одним запросом."""
    return {
        "genders": GENDERS,
        "project_types": PROJECT_TYPES,
        "role_types": ROLE_TYPES,
        "ethnicity": ETHNICITY,
        "body_type": BODY_TYPE,
        "hair_colors": HAIR_COLORS,
        "hair_lengths": HAIR_LENGTHS,
        "education": EDUCATION,
        "tax_status": TAX_STATUS,
        "eye_colors": EYE_COLORS,
        "marks": MARKS,
        "skills_sport": SKILLS_SPORT,
        "skills_dance": SKILLS_DANCE,
        "skills_vocal": SKILLS_VOCAL,
        "skills_instruments": SKILLS_INSTRUMENTS,
    }


def all_codes() -> dict[str, set[str]]:
    """Для серверной валидации — какие code'ы вообще валидны в каждом справочнике."""
    return {key: {it["code"] for it in items} for key, items in all_refs().items()}

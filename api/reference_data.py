"""Справочные данные для Mini App: типы проектов, ролей, навыки и т.п.
Возвращаются на /api/refs, фронт рендерит из них чипы и селекты."""
from __future__ import annotations

from typing import Literal, TypedDict


class RefItem(TypedDict):
    code: str
    label: str


Lang = Literal["ru", "en"]


def _items(triples: list[tuple[str, str, str]], lang: Lang) -> list[RefItem]:
    return [
        {"code": code, "label": en if lang == "en" else ru}
        for code, ru, en in triples
    ]


# (code, ru, en)
_GENDERS = [
    ("male", "Мужской", "Male"),
    ("female", "Женский", "Female"),
]

_PROJECT_TYPES = [
    ("kino_serial", "Кино и сериалы", "Movies and TV series"),
    ("advertising", "Реклама", "Advertising"),
    ("model_projects", "Модельные проекты", "Modeling projects"),
    ("show_reality", "Шоу, реалити и интернет", "Shows, reality TV and internet"),
    ("voice_dub", "Озвучка / дубляж", "Voiceover / dubbing"),
    ("theater", "Театр, спектакль, мюзикл", "Theater, plays, musicals"),
]

_ROLE_TYPES = [
    ("main", "Главная", "Lead"),
    ("supporting", "Второстепенная", "Supporting"),
    ("episode", "Эпизод", "Episodic"),
    ("massovka", "Массовка", "Background/extra"),
    ("groupovka", "Групповка", "Featured extra"),
    ("dubler", "Дублёр", "Stand-in"),
    ("kaskader", "Каскадёр", "Stunt performer"),
    ("model", "Модель", "Model"),
    ("photo_model", "Фотомодель", "Photo model"),
    ("promo_model", "Промо модель", "Promo model"),
    ("tv_host", "Ведущий (ТВ-передачи)", "TV host"),
    ("diktor", "Диктор", "Announcer"),
    ("dancer", "Танцор", "Dancer"),
    ("ballerina", "Балерина", "Ballerina"),
    ("gymnast", "Гимнастка", "Gymnast"),
    ("vocalist", "Вокалист", "Vocalist"),
    ("musician", "Музыкант", "Musician"),
]

_ETHNICITY = [
    ("slavic", "Славянский", "Slavic"),
    ("european", "Европейский", "European"),
    ("caucasian", "Кавказский", "Caucasian"),
    ("asian", "Азиатский", "Asian"),
    ("central_asian", "Среднеазиатский", "Central Asian"),
    ("african", "Африканский", "African"),
    ("arab", "Арабский", "Arab"),
    ("latin", "Латино", "Latino"),
    ("mixed", "Смешанный", "Mixed"),
    ("other", "Другой", "Other"),
]

_BODY_TYPE = [
    ("slim", "Худощавое", "Slim"),
    ("athletic", "Спортивное", "Athletic"),
    ("normal", "Среднее", "Average"),
    ("plus_size", "Пышное / plus-size", "Plus-size"),
    ("muscular", "Накачанное", "Muscular"),
]

_HAIR_COLORS = [
    ("black", "Чёрные", "Black"),
    ("dark_brown", "Тёмно-русые", "Dark brown"),
    ("brown", "Каштановые", "Chestnut"),
    ("light_brown", "Русые", "Light brown"),
    ("blond", "Блонд", "Blond"),
    ("red", "Рыжие", "Red"),
    ("grey", "Седые", "Grey"),
    ("dyed", "Окрашенные", "Dyed"),
]

_HAIR_LENGTHS = [
    ("bald", "Лысый / бритый", "Bald / shaved"),
    ("very_short", "Очень короткие", "Very short"),
    ("short", "Короткие", "Short"),
    ("medium", "Средние", "Medium"),
    ("long", "Длинные", "Long"),
    ("very_long", "Очень длинные", "Very long"),
]

_EDUCATION = [
    ("vuz", "Профильный ВУЗ", "Relevant university degree"),
    ("courses", "Курсы", "Courses"),
    ("vuz_courses", "ВУЗ + Курсы", "University + courses"),
    ("none", "Нет профильного образования", "No relevant education"),
]

_TAX_STATUS = [
    ("self_employed", "Самозанятый", "Self-employed"),
    ("ip", "ИП", "Sole proprietor"),
    ("individual", "Физлицо", "Private individual"),
]

_EYE_COLORS = [
    ("brown", "Карие", "Brown"),
    ("blue", "Голубые", "Blue"),
    ("green", "Зелёные", "Green"),
    ("grey", "Серые", "Grey"),
    ("hazel", "Ореховые", "Hazel"),
    ("mixed", "Смешанные", "Mixed"),
]

_MARKS = [
    ("tattoo", "Татуировки", "Tattoos"),
    ("piercing", "Пирсинг", "Piercing"),
    ("scars", "Шрамы", "Scars"),
    ("freckles", "Веснушки", "Freckles"),
    ("braces", "Брекеты", "Braces"),
    ("other", "Другое", "Other"),
]

_SKILLS_SPORT = [
    ("running", "Бег", "Running"),
    ("swimming", "Плавание", "Swimming"),
    ("boxing", "Бокс", "Boxing"),
    ("horseback", "Верховая езда", "Horseback riding"),
    ("fencing", "Фехтование", "Fencing"),
    ("yoga", "Йога", "Yoga"),
    ("gymnastics", "Гимнастика", "Gymnastics"),
    ("acrobatics", "Акробатика", "Acrobatics"),
    ("martial_arts", "Боевые искусства", "Martial arts"),
    ("football", "Футбол", "Football"),
    ("basketball", "Баскетбол", "Basketball"),
    ("tennis", "Теннис", "Tennis"),
]

_SKILLS_DANCE = [
    ("ballroom", "Бальные", "Ballroom"),
    ("contemporary", "Современные", "Contemporary"),
    ("hip_hop", "Хип-хоп", "Hip-hop"),
    ("ballet", "Балет", "Ballet"),
    ("latin", "Латина", "Latin"),
    ("folk", "Народные", "Folk"),
    ("step", "Степ", "Tap"),
    ("breakdance", "Брейк-данс", "Breakdance"),
    ("jazz", "Джаз", "Jazz"),
]

_SKILLS_VOCAL = [
    ("variety", "Эстрадный", "Pop/variety"),
    ("academic", "Академический", "Classical"),
    ("rap", "Рэп", "Rap"),
    ("rock", "Рок", "Rock"),
    ("jazz", "Джазовый", "Jazz"),
]

_SKILLS_INSTRUMENTS = [
    ("guitar", "Гитара", "Guitar"),
    ("piano", "Фортепиано", "Piano"),
    ("violin", "Скрипка", "Violin"),
    ("drums", "Барабаны", "Drums"),
    ("saxophone", "Саксофон", "Saxophone"),
    ("flute", "Флейта", "Flute"),
    ("accordion", "Баян/Аккордеон", "Bayan/Accordion"),
    ("ukulele", "Укулеле", "Ukulele"),
]

_WORK_TYPES_EVENT = [
    ("hostess", "Хостес", "Hostess"),
    ("promo_model", "Промо-модель", "Promo model"),
    ("animator", "Аниматор", "Animator"),
]

_WORK_TYPES_GENERAL = [
    ("helper", "Хелпер", "Helper"),
    ("cleaning", "Клининг", "Cleaning"),
    ("loader", "Грузчик", "Loader"),
]

_WORK_TYPES_ADMIN = [
    ("registration_operator", "Оператор регистрации", "Registration operator"),
    ("supervisor", "Супервайзер", "Supervisor"),
]


def all_refs(lang: Lang = "ru") -> dict[str, list[RefItem]]:
    """Полный словарь справочников для отдачи фронту одним запросом."""
    return {
        "genders": _items(_GENDERS, lang),
        "project_types": _items(_PROJECT_TYPES, lang),
        "role_types": _items(_ROLE_TYPES, lang),
        "ethnicity": _items(_ETHNICITY, lang),
        "body_type": _items(_BODY_TYPE, lang),
        "hair_colors": _items(_HAIR_COLORS, lang),
        "hair_lengths": _items(_HAIR_LENGTHS, lang),
        "education": _items(_EDUCATION, lang),
        "tax_status": _items(_TAX_STATUS, lang),
        "eye_colors": _items(_EYE_COLORS, lang),
        "marks": _items(_MARKS, lang),
        "skills_sport": _items(_SKILLS_SPORT, lang),
        "skills_dance": _items(_SKILLS_DANCE, lang),
        "skills_vocal": _items(_SKILLS_VOCAL, lang),
        "skills_instruments": _items(_SKILLS_INSTRUMENTS, lang),
        "work_types_event": _items(_WORK_TYPES_EVENT, lang),
        "work_types_general": _items(_WORK_TYPES_GENERAL, lang),
        "work_types_admin": _items(_WORK_TYPES_ADMIN, lang),
    }


def all_codes() -> dict[str, set[str]]:
    """Для серверной валидации — какие code'ы вообще валидны в каждом справочнике."""
    return {key: {it["code"] for it in items} for key, items in all_refs().items()}

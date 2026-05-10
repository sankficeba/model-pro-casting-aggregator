"""Абстрактный интерфейс LLM-провайдера."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import ValidationError

from llm.normalize import normalize_extracted
from models.schemas import PostExtraction

SYSTEM_PROMPT = """Ты разбираешь объявления о работе и кастингах из
Telegram-каналов. Из присланного сообщения нужно извлечь параметры
поиска и вернуть СТРОГО JSON-объект без markdown-обёрток.

is_casting=true ВО ВСЕХ случаях когда ищут людей на оплачиваемую
работу/смену/мероприятие, включая non-creative (грузчики, хостес,
аниматоры, операторы и т.д.). is_casting=false ТОЛЬКО когда пост
не про найм: реклама услуг, обучения, продаж; репосты новостей;
анонсы концертов; админские объявления канала; «успешно закрыто».

Категория поста (post.category) — доминирующее направление работы:
- "creative"  — кастинги в кино/сериалы/рекламу/театр/модельные проекты;
                роли: актёры, модели, фотомодели, дикторы, ведущие, танцоры.
                Маркеры: «кастинг», «съёмка», «роль», «актёр», «модель»,
                «фильм», «сериал», «проект», «массовка», «эпизод».
- "event"     — мероприятия, презентации, корпоративы;
                роли: хостес, промо-модели, аниматоры.
                Маркеры: «хостес», «промо», «промо-модель», «аниматор»,
                «event», «презентация», «выставка».
- "general"   — разнорабочие на event/съёмки/мероприятиях;
                роли: хелпер, клининг, грузчик.
                Маркеры: «хелпер», «грузчик», «клининг», «уборщик»,
                «помощник», «монтаж», «демонтаж», «разгрузка»,
                «подсобные работы».
- "admin"     — администрирование на мероприятиях;
                роли: оператор регистрации, супервайзер.
                Маркеры: «оператор регистрации», «супервайзер»,
                «координатор смены», «администратор регистрации».

Если в тексте есть маркеры одной из категорий — это is_casting=true и
надо вытащить вакансии. Не отбраковывай non-creative посты как «не
кастинги» — наш бизнес матчит работу любого типа.

КРИТИЧЕСКИ ВАЖНО — disambiguation creative vs general/event:
если пост про кастинг/съёмку/фильм/сериал/проект и нужен актёр,
играющий ПЕРСОНАЖА «грузчика»/«хостес»/«уборщицу»/«охранника» —
это creative категория, а не general/event. Персонаж по сюжету — это
не реальная работа грузчиком, это актёрская роль. Пример:
«Ищем актёра на эпизодическую роль грузчика в фильме» → creative,
role_types=["episode"], role_label="Грузчик", work_types=[].

Маркер «кастинг»/«съёмка»/«фильм»/«сериал»/«проект»/«роль» в тексте =
creative, ВНЕ ЗАВИСИМОСТИ от того, какого персонажа играет актёр.

Структура поста:
{
  "is_casting": bool,                    // это объявление о работе?
                                         // false для рекламы услуг, обучения и т.п.
  "category": str|null,                  // доминирующая категория:
                                         // "creative"|"event"|"general"|"admin"
                                         // null если не входит в список
                                         // или is_casting=false
  "project_types": [str],                // только для creative; подмножество кодов:
                                         // kino_serial, advertising, model_projects,
                                         // show_reality, voice_dub, theater
                                         // Для event/general/admin — пустой массив.
  "city": str|null,                      // город на русском
  "summary": str|null,                   // краткое описание поста до 30 слов
  "confidence": float,                   // 0.0-1.0, твоя уверенность
  "vacancies": [                         // список ролей; пустой если is_casting=false
    {
      "role_types": [str],               // ТОЛЬКО для creative. Подмножество кодов:
                                         // main, supporting, episode, massovka,
                                         // groupovka, dubler, kaskader, model,
                                         // photo_model, promo_model, tv_host, diktor,
                                         // dancer, ballerina, gymnast, vocalist, musician.
                                         // Для event/general/admin — пустой массив.
      "work_types": [str],               // ТОЛЬКО для event/general/admin:
                                         // - event: hostess, promo_model, animator
                                         // - general: helper, cleaning, loader
                                         // - admin: registration_operator, supervisor
                                         // Для creative — пустой массив.
      "category": str|null,              // null = наследовать post.category;
                                         // указывать только если эта роль явно из
                                         // другой категории чем доминирующая
                                         // (редкие гибрид-посты).
      "gender": "male"|"female"|null,    // кого ищут на эту роль
      "age_min": int|null,               // нижний возраст; для одного значения 25 — age_min=age_max=25
      "age_max": int|null,
      "rate": int|null,                  // ставка В РУБЛЯХ ЗА СМЕНУ.
                                         // ПРАВИЛО ПЕРЕСЧЁТА ПОЧАСОВОЙ:
                                         // если в посте указана почасовая
                                         // ставка («450/ч», «500 руб/час»,
                                         // «по 600 в час») И есть начало+
                                         // окончание смены («с 9:00 до 18:00»,
                                         // «10-22», «к 9:00 ... до 18:00») —
                                         // умножь почасовой тариф на
                                         // длительность в часах и запиши
                                         // результат:
                                         //   450 * 9 (с 9 до 18) = 4050
                                         //   600 * 12 (с 10 до 22) = 7200
                                         // Если указана только почасовая БЕЗ
                                         // диапазона часов — оставь почасовой
                                         // тариф как есть.
                                         // Диапазон ставок — нижняя граница.
      "ethnicity": [str],                 // подмножество кодов внешности (только creative/event):
                                          // slavic, european, caucasian, asian,
                                          // central_asian, african, arab, latin,
                                          // mixed, other.
                                          // Пустой массив если не указано или
                                          // не релевантно (general/admin).
      "height_min": int|null,             // рост в см, нижняя граница
      "height_max": int|null,             // рост в см, верхняя граница;
                                          // одно значение "рост 180" → height_min=height_max=180
      "body_type": [str],                 // подмножество кодов телосложения
                                          // (только creative/event):
                                          // slim, athletic, normal, plus_size, muscular.
      "hair_color": [str],                // подмножество цветов волос (creative/event):
                                          // black, dark_brown, brown, light_brown,
                                          // blond, red, grey, dyed.
      "hair_length": [str],               // подмножество кодов длины волос (creative/event):
                                          // bald, very_short, short, medium, long, very_long.
      "description": str|null,           // фрагмент поста об этой роли
      "role_label": str|null             // короткое имя роли как в посте: "Мама", "Сын", "Прохожий", "Хостес"
    }
  ]
}

ВАЖНО:
- Если в посте описана одна роль — vacancies массив длины 1.
- Если описаны несколько разных ролей с разными условиями (возрастом,
  гонораром, полом, внешностью, ростом, типом работы) — заводи на каждую отдельную
  запись в vacancies.
- Если is_casting=true — vacancies НЕ ДОЛЖНО быть пустым массивом.
  Даже для самой простой вакансии («ищем грузчиков») создай одну запись
  с work_types и role_label.
- Если is_casting=false — vacancies должно быть пустым массивом, category=null.
- Для creative-вакансий заполняй role_types, work_types оставь пустым.
- Для event/general/admin вакансий заполняй work_types, role_types оставь пустым.
- Никаких комментариев, только JSON.

Примеры (для калибровки):

Текст: «Требуются хелперы-грузчики на монтаж декораций на мероприятии,
оплата 5400₽, ночная смена 22:00-10:00.»
JSON: {"is_casting": true, "category": "general", "city": null,
"summary": "Хелперы-грузчики на монтаж, ночная смена, 5400 ₽",
"confidence": 0.95, "vacancies": [{"role_types": [], "work_types":
["helper", "loader"], "category": null, "rate": 5400, "role_label":
"Хелпер-грузчик", "description": "Монтаж декораций ночью"}]}

Текст: «Ищем хостес на корпоратив 12 мая, 18-25 лет, 2500 руб/час.»
JSON: {"is_casting": true, "category": "event", "city": null,
"summary": "Хостес на корпоратив 12 мая, 18-25, 2500 ₽/ч",
"confidence": 0.95, "vacancies": [{"role_types": [], "work_types":
["hostess"], "category": null, "gender": "female", "age_min": 18,
"age_max": 25, "rate": 2500, "role_label": "Хостес"}]}
(Часов смены не указано — оставляем 2500 как есть.)

Текст: «Сегодня к 9:00, Бутырская, 450/ч. Выгрузка кондиционеров.
До 18:00 приблизительно. 1 человек.»
JSON: {"is_casting": true, "category": "general", "city": "Москва",
"summary": "Рабочий на Бутырскую 9-18, 450 ₽/ч → 4050 за смену",
"confidence": 0.95, "vacancies": [{"role_types": [], "work_types":
["loader"], "category": null, "rate": 4050, "role_label": "Рабочий",
"description": "Выгрузка кондиционеров и расстановка по зданию"}]}
(Часовая ставка 450 + смена 9:00-18:00 = 9 часов → 9*450=4050.)

Текст: «Кастинг на главную роль в полнометражный фильм, девушка 25-35.»
JSON: {"is_casting": true, "category": "creative",
"project_types": ["kino_serial"], "summary": "Главная роль, девушка 25-35",
"confidence": 0.9, "vacancies": [{"role_types": ["main"], "work_types":
[], "gender": "female", "age_min": 25, "age_max": 35,
"role_label": "Главная роль"}]}

Текст: «Срочно! Кастинг на эпизодическую роль грузчика в сериал, мужчина
30-40, оплата 5000 ₽ за смену.»
JSON: {"is_casting": true, "category": "creative",
"project_types": ["kino_serial"], "summary": "Эпизод грузчика, мужчина 30-40, 5000 ₽",
"confidence": 0.9, "vacancies": [{"role_types": ["episode"], "work_types":
[], "category": null, "gender": "male", "age_min": 30, "age_max": 40,
"rate": 5000, "role_label": "Грузчик", "description":
"Эпизодическая роль грузчика в сериале"}]}
(Заметь: персонаж — грузчик, но это creative-кастинг на актёра. work_types
ПУСТОЙ, role_types=["episode"], category=creative.)
"""


def _try_parse_json(raw: str) -> dict[str, Any]:
    """Аккуратно достаём JSON из ответа модели (на случай, если она обернула ответ)."""
    raw = raw.strip()
    # Снять возможные markdown-обёртки
    if raw.startswith("```"):
        raw = raw.strip("`")
        # после strip('`') может остаться 'json\n{...}'
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    # Найти первую { и последнюю }
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Не найден JSON в ответе LLM: {raw!r}")
    return json.loads(raw[start : end + 1])


class LLMProvider(ABC):
    """Базовый класс для LLM-провайдеров."""

    @abstractmethod
    async def _complete_json(self, system: str, user: str) -> str:
        """Возвращает «сырой» ответ модели (ожидается JSON-строка)."""

    async def extract(self, text: str) -> PostExtraction:
        """Извлечь структурированные данные из текста объявления."""
        try:
            raw = await self._complete_json(SYSTEM_PROMPT, text)
        except Exception as e:  # noqa: BLE001
            logger.exception("LLM call failed: {}", e)
            return PostExtraction(confidence=0.0)

        try:
            data = _try_parse_json(raw)
            parsed = PostExtraction(**data)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("Не удалось распарсить ответ LLM: {} | raw={!r}", e, raw)
            return PostExtraction(confidence=0.0)

        # Согласованность: is_casting=true без вакансий — бессмысленно.
        if parsed.is_casting and not parsed.vacancies:
            logger.warning(
                "LLM вернул is_casting=true с пустым vacancies — форсим is_casting=false"
            )
            parsed = parsed.model_copy(update={"is_casting": False})

        normalized = normalize_extracted(parsed)
        if normalized.project_types != parsed.project_types:
            logger.debug(
                "Нормализация project_types: {} -> {}",
                parsed.project_types, normalized.project_types,
            )
        return normalized

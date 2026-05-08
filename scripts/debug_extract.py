"""Диагностика: прогнать произвольный текст через LLM-провайдера и
напечатать результат extract() в JSON.

Использование:
    docker exec -i tg_parser_app python scripts/debug_extract.py < /path/to/text.txt
    cat sample.txt | docker exec -i tg_parser_app python scripts/debug_extract.py
    docker exec tg_parser_app python scripts/debug_extract.py --sample helper
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm.factory import get_llm_provider  # noqa: E402


SAMPLES: dict[str, str] = {
    "helper": """❗️ СЕГОДНЯ СРОЧНО❗️

Добрый день!
Требуются сотрудники на мероприятие (монтаж) 🛠️

📍 Локация: Шоссе энтузиастов
📅 Дата: 08.05.2026
💰 Оплата за проект: 5 400 руб.

Вакансия: ХЕЛПЕР-ГРУЗЧИК
👥 Количество: 2 человека
⏰ Время работы: с 22:00 до 10:00
⚠️ Возможно продление смены — быть на связи!

Задачи:
• Физическая помощь на демонтаже
• Подсобные работы (подай/принеси)
• Вынос декораций
Внешний вид: рабочая форма (своя)

Как откликнуться:
📲 @oneday_hr3 с пометкой «НОЧЬ»
В первом сообщении прислать:
ФИО
Возраст
Номер телефона
Фото (для идентификации)""",
}


async def run(text: str, runs: int) -> None:
    llm = get_llm_provider()
    print(f"Provider: {type(llm).__name__}")
    print(f"Text length: {len(text)} chars\n")
    for i in range(1, runs + 1):
        result = await llm.extract(text)
        print(f"=== Run {i}/{runs} ===")
        print(result.model_dump_json(indent=2))
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Прогнать текст через LLM.extract()")
    parser.add_argument(
        "--sample",
        choices=sorted(SAMPLES.keys()),
        help="использовать встроенный пример вместо stdin",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="сколько раз вызвать extract() — для проверки стабильности (default 1)",
    )
    args = parser.parse_args()

    if args.sample:
        text = SAMPLES[args.sample]
    else:
        text = sys.stdin.read()
        if not text.strip():
            parser.error("stdin пуст и --sample не задан")

    asyncio.run(run(text, args.runs))


if __name__ == "__main__":
    main()

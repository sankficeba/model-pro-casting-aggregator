"""Тарифы: обычная цена 499 ₽/мес, акция до конца ноября 2026 (МСК)."""
from datetime import datetime

from api import plans
from api.plans import MSK, current_plans, find_plan, get_plan, promo_active

DURING = datetime(2026, 11, 30, 23, 59, tzinfo=MSK)
AFTER = datetime(2026, 12, 1, 0, 0, tzinfo=MSK)


def test_promo_ends_at_december_1_msk():
    assert promo_active(DURING) is True
    assert promo_active(AFTER) is False


def test_promo_prices_with_regular_crossed_out():
    p = {x.code: x for x in current_plans(DURING)}
    assert [(p[c].price_rub, p[c].regular_price_rub) for c in ("1m", "3m", "6m", "12m")] == [
        (299, 499), (799, 1350), (1490, 2550), (2690, 4500)]


def test_regular_prices_after_promo():
    p = {x.code: x for x in current_plans(AFTER)}
    assert [(p[c].price_rub, p[c].regular_price_rub) for c in ("1m", "3m", "6m", "12m")] == [
        (499, None), (1350, None), (2550, None), (4500, None)]


def test_checkout_uses_price_at_click_time():
    assert find_plan("3m", DURING).price_rub == 799
    assert find_plan("3m", AFTER).price_rub == 1350
    assert get_plan("nope", AFTER).code == "1m"
    assert find_plan("nope", DURING) is None


def test_promo_can_be_disabled(monkeypatch):
    monkeypatch.setattr(plans, "PROMO_UNTIL", None)
    assert promo_active(DURING) is False
    assert current_plans(DURING)[0].price_rub == 499


def test_bot_texts_show_strikethrough(monkeypatch):
    from bot import menu

    monkeypatch.setattr(plans, "PROMO_UNTIL", AFTER)
    monkeypatch.setattr(menu, "promo_active", lambda: True)
    monkeypatch.setattr(menu, "get_plan", lambda code: get_plan(code, DURING))
    btn = menu._plan_button_text(find_plan("3m", DURING), "ru")
    assert btn == "3 месяца — 1̶3̶5̶0̶ 799 ₽ · ≈266 ₽/мес"
    assert "До 30 ноября — скидки на подписку!" in menu._promo_line("ru")
    assert "<s>499</s> <b>299 ₽/мес</b>" in menu._from_price_line("ru")

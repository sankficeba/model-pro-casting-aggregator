"""Сквозной тест меню бота: настоящий aiogram Dispatcher, подменённые
Telegram API (фейковая сессия) и репозиторий (in-memory).

Проверяет маршрутизацию: любое сообщение → меню, экраны настроек, ввод
текста через FSM, сброс ввода другой кнопкой и /menu, пробный период."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import Update

from bot import handlers, menu
from config import settings
from db import repository

UID = 777
ADMIN = 555


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls: list = []

    async def make_request(self, bot, method, timeout=None):  # noqa: ARG002
        self.calls.append(method)
        if isinstance(method, (SendMessage, EditMessageText)):
            return SimpleNamespace(message_id=1)
        return True

    async def stream_content(self, *a, **k):  # pragma: no cover
        yield b""

    async def close(self):
        pass


@pytest.fixture
def db(monkeypatch):
    """In-memory состояние юзера + подмена функций репозитория."""
    state = {
        "blacklist": [],
        "delivery": dict(delivery_mode="instant", night_mode_enabled=False, night_start_hour=23,
                         night_end_hour=9, digest_daily_enabled=False, digest_daily_hour=20),
        "pending": 0, "retention": 5, "problems": [],
        "trial_started_at": NOW - timedelta(days=1), "active_until": NOW + timedelta(days=7),
    }

    async def ret(v):
        return v

    async def status(uid):
        au = state["active_until"]
        active = au is not None and au > datetime.now(timezone.utc)
        return {"is_active": active, "active_until": au, "days_left": 7 if active else 0,
                "trial_started_at": state["trial_started_at"]}

    async def activate_trial(uid, days):
        if state["trial_started_at"] is not None:
            return None
        state["trial_started_at"] = datetime.now(timezone.utc)
        state["active_until"] = state["trial_started_at"] + timedelta(days=days)
        return state["active_until"]

    async def set_bl(uid, words):
        seen, out = set(), []
        for w in words:
            if w.strip() and w.lower() not in seen:
                seen.add(w.lower())
                out.append(w.strip())
        state["blacklist"] = out
        return out

    async def set_delivery(uid, **kw):
        state["delivery"].update(kw)
        return dict(state["delivery"])

    async def create_problem(uid, text):
        state["problems"].append(text)
        return SimpleNamespace(id=len(state["problems"]), text=text)

    async def set_retention(uid, d):
        state["retention"] = d
        return True

    patches = {
        "get_subscription_status": status,
        "activate_trial": activate_trial,
        "count_pending": lambda uid: ret(state["pending"]),
        "get_user_language": lambda uid: ret("ru"),
        "upsert_user": lambda *a, **k: ret(None),
        "mark_user_bot_chat_active": lambda *a, **k: ret(None),
        "get_broadcast_pending": lambda uid: ret(None),
        "get_user_blacklist": lambda uid: ret(list(state["blacklist"])),
        "set_user_blacklist": set_bl,
        "get_delivery_settings": lambda uid: ret(dict(state["delivery"])),
        "set_delivery_settings": set_delivery,
        "prune_old_favorites": lambda uid: ret(0),
        "list_favorites": lambda uid: ret([]),
        "get_favorites_retention_days": lambda uid: ret(state["retention"]),
        "set_favorites_retention_days": set_retention,
        "create_problem": create_problem,
    }
    for name, fn in patches.items():
        monkeypatch.setattr(repository, name, fn)
    monkeypatch.setattr(settings, "admin_ids_raw", str(ADMIN))
    return state


NOW = datetime.now(timezone.utc)


class Harness:
    def __init__(self):
        self.session = FakeSession()
        self.bot = Bot("1:" + "A" * 35, session=self.session)
        self.dp = handlers.build_dispatcher(self.bot)
        self._uid = 0

    def _upd(self, **kw):
        self._uid += 1
        return Update(update_id=self._uid, **kw)

    async def msg(self, text):
        ents = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}] if text.startswith("/") else None
        await self.dp.feed_update(self.bot, self._upd(message={
            "message_id": 10, "date": 0, "chat": {"id": UID, "type": "private"},
            "from": {"id": UID, "is_bot": False, "first_name": "U", "language_code": "ru"},
            "text": text, **({"entities": ents} if ents else {}),
        }))
        return self.flush()

    async def cb(self, data):
        await self.dp.feed_update(self.bot, self._upd(callback_query={
            "id": "q", "chat_instance": "c", "data": data,
            "from": {"id": UID, "is_bot": False, "first_name": "U", "language_code": "ru"},
            "message": {"message_id": 11, "date": 0, "chat": {"id": UID, "type": "private"},
                        "from": {"id": 1, "is_bot": True, "first_name": "B"}, "text": "x"},
        }))
        return self.flush()

    def flush(self):
        """[(kind, chat_id, text, [button texts])] отправленного с прошлого вызова."""
        out = []
        for c in self.session.calls:
            if isinstance(c, (SendMessage, EditMessageText)):
                kb = [b.text for row in (c.reply_markup.inline_keyboard if c.reply_markup else []) for b in row]
                out.append((type(c).__name__, getattr(c, "chat_id", None), c.text, kb))
            elif isinstance(c, AnswerCallbackQuery) and c.text:
                out.append(("answer", None, c.text, []))
        self.session.calls.clear()
        return out


@pytest.fixture
def h(db):  # noqa: ARG001
    return Harness()


def _is_main_menu(sent):
    return any("Главное меню" in text for _, _, text, _ in sent)


async def test_any_text_opens_main_menu(h):
    sent = await h.msg("привет")
    assert _is_main_menu(sent)
    buttons = sent[0][3]
    for b in ("Настроить анкету", "Продлить подписку", "Избранное", "Доставка",
              "Чёрный список", "Предложить канал", "Сообщить о проблеме", "English"):
        assert b in buttons


async def test_blacklist_add_and_remove(h, db):
    await h.cb("bl:menu")
    await h.cb("bl:add")
    sent = await h.msg("курьер, без оплаты\n18+")
    assert db["blacklist"] == ["курьер", "без оплаты", "18+"]
    assert "Добавлено: 3" in sent[0][2]
    # после ввода состояние сброшено: обычный текст снова открывает меню
    assert _is_main_menu(await h.msg("ещё текст"))
    await h.cb("bl:rm:1")
    assert db["blacklist"] == ["курьер", "18+"]


async def test_other_button_cancels_pending_input(h, db):
    await h.cb("bl:add")
    await h.cb("dlv:menu")  # нажали другую кнопку — ввод слов отменён
    assert _is_main_menu(await h.msg("не слово"))
    assert db["blacklist"] == []


async def test_menu_command_cancels_pending_input(h, db):
    await h.cb("pr:start")
    assert _is_main_menu(await h.msg("/menu"))
    assert _is_main_menu(await h.msg("ок"))
    assert db["problems"] == []


async def test_delivery_settings(h, db):
    await h.cb("dlv:mode:digest")
    assert db["delivery"]["delivery_mode"] == "digest"
    assert db["delivery"]["digest_daily_enabled"] is True  # как в Mini App
    await h.cb("dlv:set:dh:9")
    assert db["delivery"]["digest_daily_hour"] == 9
    await h.cb("dlv:night")
    assert db["delivery"]["night_mode_enabled"] is True
    await h.cb("dlv:set:dh:99")  # мусор игнорируется
    assert db["delivery"]["digest_daily_hour"] == 9


async def test_favorites_retention_cycles(h, db):
    await h.cb("favs:list")
    await h.cb("favs:ret")
    assert db["retention"] == 7


async def test_suggest_channel_goes_to_admin(h):
    await h.cb("sc:start")
    sent = await h.msg("какой-то текст")
    assert "Не похоже на ссылку" in sent[0][2]
    sent = await h.msg("@kastingi_msk отличные массовки <b>")
    admin_msgs = [s for s in sent if s[1] == ADMIN]
    assert admin_msgs and "t.me/kastingi_msk" in admin_msgs[0][2]
    assert "&lt;b&gt;" in admin_msgs[0][2]  # комментарий экранирован
    assert admin_msgs[0][3] == ["✅ Добавить", "❌ Не добавлять"]


async def test_report_problem_goes_to_admin(h, db):
    await h.cb("pr:start")
    sent = await h.msg("Не приходят уведомления <script>")
    assert db["problems"] == ["Не приходят уведомления <script>"]
    admin_msgs = [s for s in sent if s[1] == ADMIN]
    assert admin_msgs and "&lt;script&gt;" in admin_msgs[0][2]
    assert admin_msgs[0][3] == ["✅ Проблема решена"]


async def test_new_user_gets_trial_offer_then_menu(h, db):
    db["trial_started_at"] = None
    db["active_until"] = None
    sent = await h.msg("/start")
    assert sent[0][3] == ["Активировать пробный период — 7 дней", "English"]
    sent = await h.cb(menu.CB_TRIAL)
    assert ("answer", None, "Пробный период активирован!", []) in sent
    assert _is_main_menu(sent)
    assert any("Пробный период активирован" in s[2] for s in sent if s[0] != "answer")
    # повторно пробный период не даётся
    sent = await h.cb(menu.CB_TRIAL)
    assert any(s[0] == "answer" and "уже был" in s[2] for s in sent)

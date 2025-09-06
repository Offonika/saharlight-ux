import pytest
import importlib
from datetime import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from services.api.app.diabetes.services.db import Base, User, Profile, Alert, Reminder
from services.api.app.diabetes.handlers import profile as handlers
from services.api.app.diabetes.services.repository import commit
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
import services.api.app.diabetes.handlers.sos_handlers as sos_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.markups: list[Any] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.data = data
        self.message = message
        self.edits: list[tuple[str, dict[str, Any]]] = []

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edits.append((text, kwargs))


@pytest.mark.asyncio
async def test_profile_view_has_security_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy_profile = SimpleNamespace(icr=10, cf=2, target=6, low=4, high=9)
    dummy_api = SimpleNamespace(profiles_get=lambda telegram_id: dummy_profile)
    monkeypatch.setattr(handlers, "get_api", lambda: (dummy_api, Exception, MagicMock))

    msg = DummyMessage()
    update = cast(
        Any, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace())

    await handlers.profile_view(update, context)

    markup = msg.markups[0]
    buttons = [b for row in markup.inline_keyboard for b in row]
    callbacks = {b.text: b.callback_data for b in buttons}
    assert callbacks["🔔 Безопасность"] == "profile_security"


@pytest.mark.parametrize(
    "action, expected_low, expected_high",
    [
        ("low_inc", 4.5, 9.0),
        ("low_dec", 3.5, 9.0),
        ("high_inc", 4.0, 9.5),
        ("high_dec", 4.0, 8.5),
    ],
)
@pytest.mark.asyncio
async def test_profile_security_threshold_changes(
    monkeypatch: pytest.MonkeyPatch, action: Any, expected_low: Any, expected_high: Any
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=9,
                sos_alerts_enabled=True,
            )
        )
        session.add(Alert(user_id=1, sugar=5))
        session.commit()

    calls = []

    async def fake_eval(user_id: int, sugar: float, job_queue: Any) -> None:
        calls.append((user_id, sugar, job_queue))

    monkeypatch.setattr(handlers, "evaluate_sugar", fake_eval)

    query = DummyQuery(DummyMessage(), f"profile_security:{action}")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.low_threshold == expected_low
        assert profile.high_threshold == expected_high

    assert calls == [(1, 5, "jq")]


@pytest.mark.asyncio
async def test_profile_security_high_inc_respects_low_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=5,
                high_threshold=4,
                sos_alerts_enabled=True,
            )
        )
        session.add(Alert(user_id=1, sugar=5))
        session.commit()

    calls: list[tuple[int, float, str]] = []

    async def fake_eval(user_id: int, sugar: float, job_queue: Any) -> None:
        calls.append((user_id, sugar, job_queue))

    monkeypatch.setattr(handlers, "evaluate_sugar", fake_eval)

    query = DummyQuery(DummyMessage(), "profile_security:high_inc")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.high_threshold == 4
        assert profile.low_threshold == 5

    assert calls == []


@pytest.mark.asyncio
async def test_profile_security_high_dec_requires_above_low(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=4.2,
                sos_alerts_enabled=True,
            )
        )
        session.add(Alert(user_id=1, sugar=5))
        session.commit()

    calls: list[tuple[int, float, str]] = []

    async def fake_eval(user_id: int, sugar: float, job_queue: Any) -> None:
        calls.append((user_id, sugar, job_queue))

    monkeypatch.setattr(handlers, "evaluate_sugar", fake_eval)

    query = DummyQuery(DummyMessage(), "profile_security:high_dec")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.high_threshold == 4.2

    assert calls == []


@pytest.mark.asyncio
async def test_profile_security_high_dec_requires_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=0,
                high_threshold=0.4,
                sos_alerts_enabled=True,
            )
        )
        session.add(Alert(user_id=1, sugar=5))
        session.commit()

    calls: list[tuple[int, float, str]] = []

    async def fake_eval(user_id: int, sugar: float, job_queue: Any) -> None:
        calls.append((user_id, sugar, job_queue))

    monkeypatch.setattr(handlers, "evaluate_sugar", fake_eval)

    query = DummyQuery(DummyMessage(), "profile_security:high_dec")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.high_threshold == 0.4

    assert calls == []


@pytest.mark.asyncio
async def test_profile_security_toggle_sos_alerts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=9,
                sos_alerts_enabled=False,
            )
        )
        session.add(Alert(user_id=1, sugar=7))
        session.commit()

    calls = []

    async def fake_eval(user_id: int, sugar: float, job_queue: Any) -> None:
        calls.append((user_id, sugar, job_queue))

    monkeypatch.setattr(handlers, "evaluate_sugar", fake_eval)

    query = DummyQuery(DummyMessage(), "profile_security:toggle_sos")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.sos_alerts_enabled is True

    assert calls == [(1, 7, "jq")]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled, expected",
    [
        (True, "SOS-уведомления: Выкл"),
        (False, "SOS-уведомления: Вкл"),
    ],
)
async def test_profile_security_toggle_button_text(
    monkeypatch: pytest.MonkeyPatch, enabled: bool, expected: str
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=9,
                sos_alerts_enabled=enabled,
            )
        )
        session.commit()

    query = DummyQuery(DummyMessage(), "profile_security")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)

    _, kwargs = query.edits[0]
    markup = kwargs["reply_markup"]
    button = markup.inline_keyboard[2][0]
    assert button.text == expected


@pytest.mark.asyncio
async def test_profile_security_shows_reminders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=9,
                sos_alerts_enabled=True,
            )
        )
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyQuery(DummyMessage(), "profile_security")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)

    text, _ = query.edits[0]
    assert "1. 🔔 Замерить сахар ⏰ 08:00" in text


@pytest.mark.asyncio
async def test_profile_security_add_delete_calls_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, icr=10, cf=2, target_bg=6))
        session.commit()

    called = {"del": False}

    async def fake_del(update: Any, context: Any) -> None:
        called["del"] = True

    monkeypatch.setattr(reminder_handlers, "delete_reminder", fake_del)

    monkeypatch.setenv("PUBLIC_ORIGIN", "http://example")
    monkeypatch.setenv("UI_BASE_URL", "")
    import services.api.app.config as config

    importlib.reload(config)
    query_add = DummyQuery(DummyMessage(), "profile_security:add")
    update_add = cast(
        Any,
        SimpleNamespace(callback_query=query_add, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update_add, context)
    assert query_add.message.texts[-1] == "Создать напоминание:"
    markup = query_add.message.markups[-1]
    button = markup.inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url == config.build_ui_url("/reminders")

    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("UI_BASE_URL", raising=False)
    importlib.reload(config)

    query_del = DummyQuery(DummyMessage(), "profile_security:del")
    update_del = cast(
        Any,
        SimpleNamespace(callback_query=query_del, effective_user=SimpleNamespace(id=1)),
    )

    await handlers.profile_security(update_del, context)
    assert called["del"] is True


@pytest.mark.asyncio
async def test_profile_security_sos_contact_calls_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit", commit)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, icr=10, cf=2, target_bg=6))
        session.commit()

    called = False

    async def fake_sos(update: Any, context: Any) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(sos_handlers, "sos_contact_start", fake_sos)

    query = DummyQuery(DummyMessage(), "profile_security:sos_contact")
    update = cast(
        Any, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace(application=SimpleNamespace(job_queue="jq")))

    await handlers.profile_security(update, context)
    assert called is True

# db.py  ← полный и единственный источник моделей

from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
from datetime import date, datetime, time
from typing import Callable, Iterable, Optional, Protocol, TypeVar
from typing_extensions import Concatenate, ParamSpec

from sqlalchemy import (
    create_engine,
    Integer,
    BigInteger,
    String,
    Float,
    Text,
    TIMESTAMP,
    ForeignKey,
    Boolean,
    Date,
    Time,
    func,
)
import sqlalchemy as sa
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import UnboundExecutionError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    close_all_sessions,
    mapped_column,
    relationship,
    sessionmaker,
)

from services.api.app.config import get_db_password, settings

logger = logging.getLogger(__name__)


def _register_sqlite_adapters() -> None:
    """Register adapters and converters for SQLite datetime handling."""

    sqlite3.register_adapter(datetime, lambda val: val.isoformat(sep=" "))
    sqlite3.register_adapter(date, lambda val: val.isoformat())
    sqlite3.register_adapter(time, lambda val: val.isoformat())

    sqlite3.register_converter(
        "timestamp", lambda b: datetime.fromisoformat(b.decode())
    )
    sqlite3.register_converter("date", lambda b: date.fromisoformat(b.decode()))
    sqlite3.register_converter("time", lambda b: time.fromisoformat(b.decode()))


_register_sqlite_adapters()


# ────────────────── подключение к Postgres ──────────────────
engine: Engine | None = None
engine_lock = threading.Lock()
# SQLite in-memory DBs share a single connection which is not threadsafe for
# concurrent writes. A dedicated lock prevents race conditions in tests that
# perform parallel timezone updates.
sqlite_memory_lock = threading.Lock()
SessionLocal: sessionmaker[Session] = sessionmaker(autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


T = TypeVar("T")
P = ParamSpec("P")
S = TypeVar("S", bound=Session)


class SessionMaker(Protocol[S]):
    def __call__(self) -> S: ...


async def run_db(
    fn: Callable[Concatenate[S, P], T],
    *args: P.args,
    sessionmaker: SessionMaker[S] = SessionLocal,
    **kwargs: P.kwargs,
) -> T:
    """Execute blocking DB work in a thread and return the result.

    Parameters
    ----------
    fn:
        Callable accepting an active session as first argument.
    sessionmaker:
        Factory to create new :class:`~sqlalchemy.orm.Session` instances. Defaults
        to the module's ``SessionLocal`` so tests can inject their own.
    *args, **kwargs:
        Additional arguments forwarded to ``fn``.
    """

    def wrapper() -> T:
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    try:
        with sessionmaker() as _session:
            bind = _session.get_bind()
    except UnboundExecutionError as exc:
        logger.error(
            "Database engine is not initialized. Call init_db() to configure it."
        )
        raise RuntimeError(
            "Database engine is not initialized; run init_db() before calling run_db()."
        ) from exc

    if bind.url.drivername == "sqlite" and bind.url.database == ":memory:":
        with sqlite_memory_lock:
            return wrapper()

    return await asyncio.to_thread(wrapper)


def dispose_engine(target: Engine | None = None) -> None:
    """Dispose of a SQLAlchemy engine.

    Parameters
    ----------
    target:
        The engine to dispose. If ``None`` the module's global engine is used
        and reset.
    """

    global engine
    with engine_lock:
        eng = target or engine
        if eng is None:
            return
        close_all_sessions()
        eng.dispose()
        if target is None and eng is engine:
            engine = None
            SessionLocal.configure(bind=None)


# ───────────────────────── модели ────────────────────────────
class User(Base):
    __tablename__ = "users"
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    thread_id: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    username: Mapped[Optional[str]] = mapped_column(String)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[str] = mapped_column(String, default="free")
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    timezone_auto: Mapped[bool] = mapped_column(Boolean, default=True)
    dia: Mapped[float] = mapped_column(Float, default=4.0)
    round_step: Mapped[float] = mapped_column(Float, default=0.5)
    carb_units: Mapped[str] = mapped_column(String, default="g")
    org_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False, default="patient")


class Profile(Base):
    __tablename__ = "profiles"
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), primary_key=True
    )
    icr: Mapped[Optional[float]] = mapped_column(Float)
    cf: Mapped[Optional[float]] = mapped_column(Float)
    target_bg: Mapped[Optional[float]] = mapped_column(Float)
    low_threshold: Mapped[Optional[float]] = mapped_column(Float)
    high_threshold: Mapped[Optional[float]] = mapped_column(Float)
    sos_contact: Mapped[Optional[str]] = mapped_column(String)
    sos_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    quiet_start: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        server_default=sa.text("'23:00:00'"),
    )
    quiet_end: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        server_default=sa.text("'07:00:00'"),
    )

    org_id: Mapped[Optional[int]] = mapped_column(Integer)
    user: Mapped[User] = relationship("User")


class UserSettings(Base):
    __tablename__ = "user_settings"
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), primary_key=True
    )
    default_after_meal_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    user: Mapped[User] = relationship("User")


class Entry(Base):
    __tablename__ = "entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id")
    )
    org_id: Mapped[Optional[int]] = mapped_column(Integer)

    event_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), onupdate=func.now()
    )

    photo_path: Mapped[Optional[str]] = mapped_column(String)
    carbs_g: Mapped[Optional[float]] = mapped_column(Float)
    xe: Mapped[Optional[float]] = mapped_column(Float)
    sugar_before: Mapped[Optional[float]] = mapped_column(Float)
    dose: Mapped[Optional[float]] = mapped_column(Float)
    gpt_summary: Mapped[Optional[str]] = mapped_column(Text)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id")
    )
    org_id: Mapped[Optional[int]] = mapped_column(Integer)
    sugar: Mapped[Optional[float]] = mapped_column(Float)
    type: Mapped[Optional[str]] = mapped_column(String)

    ts: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship("User")


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id")
    )
    org_id: Mapped[Optional[int]] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String)
    kind: Mapped[Optional[str]] = mapped_column(String)
    time: Mapped[Optional[time]] = mapped_column(Time)
    interval_hours: Mapped[Optional[int]] = mapped_column(Integer)
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    minutes_after: Mapped[Optional[int]] = mapped_column(Integer)
    days_mask: Mapped[Optional[int]] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    user: Mapped[User] = relationship("User")

    def set_interval_hours_if_needed(self, hours: int | None) -> None:
        """Populate ``interval_minutes`` from hours if minutes absent."""
        if hours is not None and self.interval_minutes is None:
            self.interval_minutes = hours * 60

    @property
    def daysOfWeek(self) -> list[int] | None:  # noqa: N802  (external naming)
        mask = self.days_mask
        if mask is None:
            return None
        return [i + 1 for i in range(7) if mask & (1 << i)]

    @daysOfWeek.setter
    def daysOfWeek(self, days: Iterable[int] | None) -> None:  # noqa: N802
        if days is None:
            self.days_mask = None
            return
        mask = 0
        for day in days:
            if not 1 <= day <= 7:
                raise ValueError("day must be in 1..7")
            mask |= 1 << (day - 1)
        self.days_mask = mask


class ReminderLog(Base):
    __tablename__ = "reminder_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reminder_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("reminders.id")
    )
    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        index=True,
        nullable=True,
    )
    org_id: Mapped[Optional[int]] = mapped_column(Integer)
    action: Mapped[Optional[str]] = mapped_column(String)
    snooze_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    event_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class Timezone(Base):
    __tablename__ = "timezones"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        sqlite_on_conflict_primary_key="REPLACE",
    )
    tz: Mapped[str] = mapped_column(String, nullable=False)


class HistoryRecord(Base):
    __tablename__ = "history_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), index=True, nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    sugar: Mapped[Optional[float]] = mapped_column(Float)
    carbs: Mapped[Optional[float]] = mapped_column(Float)
    bread_units: Mapped[Optional[float]] = mapped_column(Float)
    insulin: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String, nullable=False)


# ────────────────────── инициализация ────────────────────────
def init_db() -> None:
    """Создать таблицы, если их ещё нет (для локального запуска)."""
    password = get_db_password()
    if not password:
        raise ValueError("DB_PASSWORD environment variable must be set")
    database_url = URL.create(
        "postgresql",
        username=settings.db_user,
        password=password,
        host=settings.db_host,
        port=int(settings.db_port),
        database=settings.db_name,
    )

    global engine
    with engine_lock:
        if engine is None or engine.url != database_url:
            if engine is not None:
                engine.dispose()
            engine = create_engine(database_url)
            SessionLocal.configure(bind=engine)

    Base.metadata.create_all(bind=engine)

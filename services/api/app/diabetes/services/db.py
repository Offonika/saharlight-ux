# db.py  ← полный и единственный источник моделей


from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Text,
    TIMESTAMP,
    Time,
    ForeignKey,
    Boolean,
    func,
)
from sqlalchemy.engine import URL
from sqlalchemy.exc import UnboundExecutionError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
import asyncio
import datetime
import logging
import threading
from typing import Any, Callable, TypeVar

from services.api.app.config import get_db_password, settings
logger = logging.getLogger(__name__)


# ────────────────── подключение к Postgres ──────────────────
engine = None
engine_lock = threading.Lock()
SessionLocal = sessionmaker(autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


T = TypeVar("T")


async def run_db(
    fn: Callable[[Any], T], *args: Any, sessionmaker: Callable[[], Any] = SessionLocal, **kwargs: Any
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
        logger.error("Database engine is not initialized. Call init_db() to configure it.")
        raise RuntimeError(
            "Database engine is not initialized; run init_db() before calling run_db()."
        ) from exc

    if bind.url.drivername == "sqlite" and bind.url.database == ":memory:":
        return wrapper()

    return await asyncio.to_thread(wrapper)


# ───────────────────────── модели ────────────────────────────
class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    thread_id: Mapped[str] = mapped_column(String, nullable=False)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[str] = mapped_column(String, default="free")
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    org_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class Profile(Base):
    __tablename__ = "profiles"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        primary_key=True,
    )
    icr: Mapped[float | None] = mapped_column(Float)  # г углеводов на 1 Е инсулина
    cf: Mapped[float | None] = mapped_column(Float)  # коэффициент коррекции
    target_bg: Mapped[float | None] = mapped_column(Float)  # целевой сахар
    low_threshold: Mapped[float | None] = mapped_column(Float)  # нижний порог сахара
    high_threshold: Mapped[float | None] = mapped_column(Float)  # верхний порог сахара
    sos_contact: Mapped[str | None] = mapped_column(String)  # контакт для экстренной связи
    sos_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_start: Mapped[datetime.time | None] = mapped_column(Time)  # начало тихого режима
    quiet_end: Mapped[datetime.time | None] = mapped_column(Time)  # конец тихого режима
    org_id: Mapped[int | None] = mapped_column(Integer)
    user: Mapped[User] = relationship("User")


class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    org_id = Column(Integer)

    event_time = Column(TIMESTAMP(timezone=True), nullable=False)  # время приёма
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    photo_path = Column(String)
    carbs_g = Column(Float)
    xe = Column(Float)
    sugar_before = Column(Float)
    dose = Column(Float)
    gpt_summary = Column(Text)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    org_id = Column(Integer)
    sugar = Column(Float)
    type = Column(String)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)
    user = relationship("User")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id")
    )
    org_id: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String, nullable=False)
    time: Mapped[str | None] = mapped_column(String)
    interval_hours: Mapped[int | None] = mapped_column(Integer)
    minutes_after: Mapped[int | None] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    user: Mapped[User] = relationship("User")


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reminder_id: Mapped[int] = mapped_column(Integer, ForeignKey("reminders.id"))
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    org_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String)
    event_time: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class Timezone(Base):
    __tablename__ = "timezones"

    id = Column(Integer, primary_key=True, index=True)
    tz = Column(String, nullable=False)


class HistoryRecord(Base):
    __tablename__ = "history_records"

    id = Column(String, primary_key=True, index=True)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    sugar = Column(Float)
    carbs = Column(Float)
    bread_units = Column(Float)
    insulin = Column(Float)
    notes = Column(Text)
    type = Column(String, nullable=False)


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

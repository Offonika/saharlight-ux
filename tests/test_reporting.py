# test_reporting.py

import datetime
import io
import os
import threading
import time
from types import SimpleNamespace
from typing import Any, BinaryIO
from pathlib import Path

import pytest
import matplotlib.pyplot as plt
from matplotlib.dates import date2num as _date2num
from pypdf import PdfReader as _PdfReader
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_PASSWORD", "test")

from services.api.app.diabetes.services.reporting import (
    make_sugar_plot,
    generate_pdf_report,
    register_fonts,
)
import services.api.app.diabetes.services.reporting as reporting
from services.api.app import config


def date2num(date: datetime.datetime) -> float:
    """Typed wrapper around :func:`matplotlib.dates.date2num`."""
    return float(_date2num(date))


def read_pdf(stream: BinaryIO) -> _PdfReader:
    """Typed wrapper around :class:`pypdf.PdfReader`."""
    return _PdfReader(stream)


class DummyEntry:
    def __init__(
        self,
        event_time: datetime.datetime,
        sugar_before: float | None,
        carbs_g: float,
        xe: float,
        dose: float,
    ) -> None:
        self.event_time = event_time
        self.sugar_before = sugar_before
        self.carbs_g = carbs_g
        self.xe = xe
        self.dose = dose


def test_register_fonts_threadsafe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reporting, "_fonts_registration_result", None)

    counter = {"n": 0}
    lock = threading.Lock()

    def fake_register_font(name: str, filename: str) -> tuple[bool, str | None]:
        time.sleep(0.05)
        with lock:
            counter["n"] += 1
        return True, None

    monkeypatch.setattr(reporting, "_register_font", fake_register_font)

    results: list[bool] = []

    def worker() -> None:
        results.append(register_fonts())

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter["n"] == 2
    assert results and all(results)


def test_register_fonts_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reporting, "_fonts_registration_result", None)

    calls: list[tuple[str, str]] = []

    def fake_register_font(name: str, filename: str) -> tuple[bool, str | None]:
        calls.append((name, filename))
        return False, f"missing {name}"

    monkeypatch.setattr(reporting, "_register_font", fake_register_font)

    result = register_fonts()

    assert result is False
    assert reporting._fonts_registration_result is False
    assert calls == [
        ("DejaVuSans", "DejaVuSans.ttf"),
        ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
    ]


def test_register_font_uses_dynamic_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, str] = {}

    def fake_ttfont(name: str, path: str) -> SimpleNamespace:
        captured["path"] = path
        return SimpleNamespace()

    monkeypatch.setattr(reporting, "TTFont", fake_ttfont)
    monkeypatch.setattr(reporting.pdfmetrics, "registerFont", lambda font: None)

    fake_settings = SimpleNamespace(font_dir=str(tmp_path))
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)

    success, msg = reporting._register_font("DejaVuSans", "DejaVuSans.ttf")

    assert success is True
    assert msg is None
    assert captured["path"] == os.path.join(str(tmp_path), "DejaVuSans.ttf")


def test_make_sugar_plot() -> None:
    entries = [
        DummyEntry(
            datetime.datetime(2025, 7, 1, 9, tzinfo=datetime.timezone.utc),
            7.0,
            40,
            3.3,
            6,
        ),
        DummyEntry(
            datetime.datetime(2025, 7, 1, 14, tzinfo=datetime.timezone.utc),
            9.0,
            50,
            4.1,
            8,
        ),
    ]
    buf = make_sugar_plot(entries, "тестовый период")
    assert hasattr(buf, "read")
    buf.seek(0)
    assert len(buf.read()) > 1000  # есть содержимое


def test_make_sugar_plot_sorts_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [
        DummyEntry(
            datetime.datetime(2025, 7, 1, 14, tzinfo=datetime.timezone.utc),
            9.0,
            50,
            4.1,
            8,
        ),
        DummyEntry(
            datetime.datetime(2025, 7, 1, 9, tzinfo=datetime.timezone.utc),
            7.0,
            40,
            3.3,
            6,
        ),
    ]
    captured = {}

    def fake_plot(
        x: list[float],
        y: list[float],
        **kwargs: Any,
    ) -> None:
        captured["x"] = x
        captured["y"] = y

    monkeypatch.setattr(plt, "plot", fake_plot)
    make_sugar_plot(entries, "период")

    assert captured["x"] == [
        date2num(datetime.datetime(2025, 7, 1, 9, tzinfo=datetime.timezone.utc)),
        date2num(datetime.datetime(2025, 7, 1, 14, tzinfo=datetime.timezone.utc)),
    ]
    assert captured["y"] == [7.0, 9.0]


def test_make_sugar_plot_no_data() -> None:
    entries = [
        DummyEntry(
            datetime.datetime(2025, 7, 1, 9, tzinfo=datetime.timezone.utc),
            None,
            40,
            3.3,
            6,
        )
    ]
    buf = make_sugar_plot(entries, "тестовый период")
    assert hasattr(buf, "read")
    buf.seek(0)
    assert len(buf.read()) > 1000


def test_generate_pdf_report() -> None:
    entries = [
        DummyEntry(
            datetime.datetime(2025, 7, 1, 9, tzinfo=datetime.timezone.utc),
            15.0,
            40,
            3.3,
            6,
        ),
    ]
    plot_buf = make_sugar_plot(entries, "тест")
    pdf_buf = generate_pdf_report(
        summary_lines=["Всего записей: 1"],
        errors=["01.07: высокий сахар 15.0"],
        day_lines=["01.07: сахар 15.0, доза 6, углеводы 40"],
        gpt_text="Всё хорошо.",
        plot_buf=plot_buf,
    )
    assert hasattr(pdf_buf, "read")
    pdf_buf.seek(0)
    reader = read_pdf(pdf_buf)
    text = "".join(page.extract_text() for page in reader.pages)
    assert "высокий сахар 15.0" in text


def test_generate_pdf_report_falls_back_to_builtin_fonts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reporting, "register_fonts", lambda: False)

    captured_fonts: list[tuple[str, int]] = []

    class DummyCanvas:
        def __init__(
            self,
            stream: io.BytesIO,
            pagesize: tuple[float, float],
            **_: Any,
        ) -> None:
            self.stream = stream
            self.pagesize = pagesize

        def setFont(self, name: str, size: int) -> None:  # noqa: N802
            captured_fonts.append((name, size))

        def drawString(self, *args: Any, **kwargs: Any) -> None:  # noqa: N802
            return None

        def showPage(self) -> None:  # noqa: N802
            return None

        def drawImage(self, *args: Any, **kwargs: Any) -> None:  # noqa: N802
            return None

        def save(self) -> None:  # noqa: N802
            self.stream.write(b"dummy")

    monkeypatch.setattr(reporting.canvas, "Canvas", DummyCanvas)

    pdf_buf = generate_pdf_report(
        summary_lines=["Всего записей: 1"],
        errors=[],
        day_lines=[],
        gpt_text="Текст",
        plot_buf=None,
    )

    assert isinstance(pdf_buf, io.BytesIO)
    font_names = {name for name, _ in captured_fonts}
    assert font_names == {"Helvetica", "Helvetica-Bold"}


@pytest.mark.parametrize("block", ["summary_lines", "errors", "day_lines"])
def test_generate_pdf_report_page_breaks(block: Any) -> None:
    long_lines = [f"line {i}" for i in range(100)]
    kwargs: dict[str, list[str]] = {"summary_lines": [], "errors": [], "day_lines": []}
    kwargs[block] = long_lines
    pdf_buf = generate_pdf_report(gpt_text="", plot_buf=None, **kwargs)
    pdf_buf.seek(0)
    reader = read_pdf(pdf_buf)
    assert len(reader.pages) > 1


@pytest.mark.asyncio
async def test_send_report_uses_gpt(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst")
    os.environ.setdefault("DB_PASSWORD", "pwd")

    import services.api.app.diabetes.handlers.reporting_handlers as handlers
    from services.api.app.diabetes.services.db import Base, Entry, User

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="tid"))
        session.add(
            Entry(
                telegram_id=1,
                event_time=datetime.datetime(2025, 7, 1, tzinfo=datetime.timezone.utc),
                sugar_before=6.0,
                carbs_g=30.0,
                dose=5.0,
            )
        )
        session.commit()

    class DummyMessage:
        def __init__(self) -> None:
            self.docs: list[Any] = []
            self.kwargs: list[dict[str, Any]] = []

        async def reply_text(self, text: str, **kwargs: Any) -> None:
            self.kwargs.append(kwargs)

        async def reply_photo(self, *args: Any, **kwargs: Any) -> None:
            self.kwargs.append(kwargs)

        async def reply_document(self, document: Any, **kwargs: Any) -> None:
            self.docs.append(document)
            self.kwargs.append(kwargs)

    message = DummyMessage()
    update: Any = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context: Any = SimpleNamespace(user_data={"thread_id": "tid"})

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "rid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(retrieve=lambda **kw: Run()),
                messages=SimpleNamespace(
                    list=lambda **kw: SimpleNamespace(
                        data=[
                            SimpleNamespace(
                                role="assistant",
                                content=[
                                    SimpleNamespace(
                                        text=SimpleNamespace(
                                            value="Совет: пейте больше воды."
                                        )
                                    )
                                ],
                            )
                        ]
                    )
                ),
            )
        )

    monkeypatch.setattr(handlers, "send_message", fake_send_message)
    monkeypatch.setattr(handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        handlers, "make_sugar_plot", lambda entries, period_label: io.BytesIO(b"img")
    )

    await handlers.send_report(
        update,
        context,
        datetime.datetime(2025, 6, 1, tzinfo=datetime.timezone.utc),
        "период",
    )

    assert message.docs
    pdf_buf = message.docs[0]
    pdf_buf.seek(0)
    text = "".join(page.extract_text() for page in read_pdf(pdf_buf).pages)
    assert "пейте больше воды" in text

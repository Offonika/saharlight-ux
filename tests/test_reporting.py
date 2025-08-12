# test_reporting.py

import datetime
import io
import os
from types import SimpleNamespace
from typing import Any

import matplotlib.pyplot as plt
import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_PASSWORD", "test")

from services.api.app.diabetes.services.reporting import make_sugar_plot, generate_pdf_report


class DummyEntry:
    def __init__(self, event_time, sugar_before, carbs_g, xe, dose):
        self.event_time = event_time
        self.sugar_before = sugar_before
        self.carbs_g = carbs_g
        self.xe = xe
        self.dose = dose


def test_make_sugar_plot():
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
    assert hasattr(buf, 'read')
    buf.seek(0)
    assert len(buf.read()) > 1000  # есть содержимое


def test_make_sugar_plot_sorts_entries(monkeypatch):
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

    def fake_plot(x, y, **kwargs):
        captured["x"] = x
        captured["y"] = y

    monkeypatch.setattr(plt, "plot", fake_plot)
    make_sugar_plot(entries, "период")

    assert captured["x"] == [
        datetime.datetime(2025, 7, 1, 9, tzinfo=datetime.timezone.utc),
        datetime.datetime(2025, 7, 1, 14, tzinfo=datetime.timezone.utc),
    ]
    assert captured["y"] == [7.0, 9.0]


def test_make_sugar_plot_no_data():
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


def test_generate_pdf_report():
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
        plot_buf=plot_buf
    )
    assert hasattr(pdf_buf, 'read')
    pdf_buf.seek(0)
    reader = PdfReader(pdf_buf)
    text = "".join(page.extract_text() for page in reader.pages)
    assert "высокий сахар 15.0" in text


@pytest.mark.parametrize("block", ["summary_lines", "errors", "day_lines"])
def test_generate_pdf_report_page_breaks(block):
    long_lines = [f"line {i}" for i in range(100)]
    kwargs = {"summary_lines": [], "errors": [], "day_lines": []}
    kwargs[block] = long_lines
    pdf_buf = generate_pdf_report(gpt_text="", plot_buf=None, **kwargs)
    pdf_buf.seek(0)
    reader = PdfReader(pdf_buf)
    assert len(reader.pages) > 1


@pytest.mark.asyncio
async def test_send_report_uses_gpt(monkeypatch):
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
        def __init__(self):
            self.docs: list[Any] = []

        async def reply_text(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def reply_photo(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def reply_document(self, document: Any, **kwargs: Any) -> None:
            self.docs.append(document)

    message = DummyMessage()
    update = SimpleNamespace(
        message=message, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={"thread_id": "tid"})

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "rid"

    def fake_send_message(**kwargs):
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
        update, context, datetime.datetime(2025, 6, 1, tzinfo=datetime.timezone.utc), "период"
    )

    assert message.docs
    pdf_buf = message.docs[0]
    pdf_buf.seek(0)
    text = "".join(page.extract_text() for page in PdfReader(pdf_buf).pages)
    assert "пейте больше воды" in text

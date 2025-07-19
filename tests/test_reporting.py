# test_reporting.py

from diabetes.reporting import make_sugar_plot, generate_pdf_report

class DummyEntry:
    def __init__(self, event_time, sugar_before, carbs_g, xe, dose):
        self.event_time = event_time
        self.sugar_before = sugar_before
        self.carbs_g = carbs_g
        self.xe = xe
        self.dose = dose

import datetime

def test_make_sugar_plot():
    entries = [
        DummyEntry(datetime.datetime(2025, 7, 1, 9), 7.0, 40, 3.3, 6),
        DummyEntry(datetime.datetime(2025, 7, 1, 14), 9.0, 50, 4.1, 8),
    ]
    buf = make_sugar_plot(entries, "тестовый период")
    assert hasattr(buf, 'read')
    buf.seek(0)
    assert len(buf.read()) > 1000  # есть содержимое

def test_generate_pdf_report():
    entries = [
        DummyEntry(datetime.datetime(2025, 7, 1, 9), 7.0, 40, 3.3, 6),
    ]
    plot_buf = make_sugar_plot(entries, "тест")
    pdf_buf = generate_pdf_report(
        summary_lines=["Всего записей: 1"],
        errors=[],
        day_lines=["01.07: сахар 7.0–7.0, доза 6, углеводы 40"],
        gpt_text="Всё хорошо.",
        plot_buf=plot_buf
    )
    assert hasattr(pdf_buf, 'read')
    pdf_buf.seek(0)
    assert len(pdf_buf.read()) > 1000

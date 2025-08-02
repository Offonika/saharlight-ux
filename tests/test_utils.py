# test_utils.py

from diabetes.utils import clean_markdown, split_text_by_width

def test_clean_markdown():
    text = "**Жирный**\n# Заголовок\n* элемент\n1. Первый"
    cleaned = clean_markdown(text)
    assert "Жирный" in cleaned
    assert "Заголовок" in cleaned
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "1." not in cleaned

def test_split_text_by_width_simple():
    text = "Это короткая строка"
    lines = split_text_by_width(text, "DejaVuSans", 12, 50)
    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)

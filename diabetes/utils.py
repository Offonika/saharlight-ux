# utils.py

import re
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

def clean_markdown(text):
    """
    Удаляет простую Markdown-разметку: **жирный**, # заголовки, * списки, 1. списки и т.д.
    """
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **жирный**
    text = re.sub(r'#+\s*', '', text)                  # ### Заголовки
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)  # 1. списки
    text = re.sub(r'^\s*\*\s*', '', text, flags=re.MULTILINE)      # * списки
    text = re.sub(r'`([^`]+)`', r'\1', text)           # `код`
    return text

def split_text_by_width(text, font_name, font_size, max_width_mm):
    """
    Разбивает строку так, чтобы она не выходила за max_width_mm по ширине в PDF (мм).
    """
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = (current_line + " " + word).strip()
        width = stringWidth(test_line, font_name, font_size) / mm
        if width > max_width_mm and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines

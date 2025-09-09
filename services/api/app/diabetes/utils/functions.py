"""Утилиты для расчёта болюса и разбора пищевой информации."""

from dataclasses import dataclass
import math
import re

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------
# Base pattern for numeric values with optional decimal part
# (``"1"``, ``"2,5"``). If a decimal separator is present, at least one
# digit must follow it.
NUMBER_RE = r"\d+(?:[.,]\d+)?"

# Generic range patterns reused across nutrition parsing.
PLUS_MINUS_RANGE_RE = re.compile(rf"({NUMBER_RE})\s*±\s*({NUMBER_RE})")
DASH_RANGE_RE = re.compile(rf"({NUMBER_RE})\s*[–-]\s*({NUMBER_RE})")

# Variants of the "XE" keyword (latin/cyrillic).
XE_WORD_RE = re.compile(r"(?:[хx][еe]|xe)", re.IGNORECASE)

# Indicator keywords for ``smart_input``.
SUGAR_WORD_RE = re.compile(r"(?:sugar|сахар)", re.IGNORECASE)
XE_LABEL_RE = re.compile(r"(?:xe|хе)", re.IGNORECASE)
DOSE_WORD_RE = re.compile(r"(?:dose|доза|болюс)", re.IGNORECASE)

# Precompiled patterns built from the bases above.
CARBS_LABELED_PM_RE = re.compile(
    rf"углевод[^\d]*:\s*({NUMBER_RE})\s*(?:г)?\s*±\s*({NUMBER_RE})\s*г",
    re.IGNORECASE,
)
CARBS_LABELED_RANGE_RE = re.compile(
    rf"углевод[^\d]*:\s*{DASH_RANGE_RE.pattern}\s*г",
    re.IGNORECASE,
)
CARBS_LABEL_RE = re.compile(r"углевод[^\d]*:\s*([\d.,]+)\s*г", re.IGNORECASE)
XE_COLON_PM_RE = re.compile(
    rf"\b{XE_WORD_RE.pattern}\s*:\s*{PLUS_MINUS_RANGE_RE.pattern}",
    re.IGNORECASE,
)
XE_COLON_RANGE_RE = re.compile(
    rf"\b{XE_WORD_RE.pattern}\s*:\s*{DASH_RANGE_RE.pattern}",
    re.IGNORECASE,
)
XE_COLON_SINGLE_RE = re.compile(
    rf"\b{XE_WORD_RE.pattern}\s*:\s*([\d.,]+)", re.IGNORECASE
)
XE_PM_RE = re.compile(
    rf"{PLUS_MINUS_RANGE_RE.pattern}\s*{XE_WORD_RE.pattern}",
    re.IGNORECASE,
)
XE_RANGE_RE = re.compile(
    rf"{DASH_RANGE_RE.pattern}\s*{XE_WORD_RE.pattern}",
    re.IGNORECASE,
)
CARBS_PM_RE = re.compile(
    rf"({NUMBER_RE})\s*(?:г)?\s*±\s*({NUMBER_RE})\s*г", re.IGNORECASE
)
CARBS_RANGE_RE = re.compile(rf"{DASH_RANGE_RE.pattern}\s*г", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Additional nutrition patterns (weight, protein, fat, calories)
# ---------------------------------------------------------------------------
WEIGHT_LABEL_RE = r"(?:вес|масса|порц(?:ия|ии|ий)?|portion|weight)"
PROTEIN_LABEL_RE = r"(?:белк(?:и)?|proteins?)"
FAT_LABEL_RE = r"(?:жир(?:ы)?|fats?)"
CALORIES_LABEL_RE = r"(?:калори(?:и)?|ккал|calories?)"

WEIGHT_PM_RE = re.compile(
    rf"{WEIGHT_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*±\s*({NUMBER_RE})\s*г",
    re.IGNORECASE,
)
WEIGHT_RANGE_RE = re.compile(
    rf"{WEIGHT_LABEL_RE}[^\d]*:\s*{DASH_RANGE_RE.pattern}\s*г",
    re.IGNORECASE,
)
WEIGHT_SINGLE_RE = re.compile(
    rf"{WEIGHT_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*г",
    re.IGNORECASE,
)

PROTEIN_PM_RE = re.compile(
    rf"{PROTEIN_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*±\s*({NUMBER_RE})\s*г",
    re.IGNORECASE,
)
PROTEIN_RANGE_RE = re.compile(
    rf"{PROTEIN_LABEL_RE}[^\d]*:\s*{DASH_RANGE_RE.pattern}\s*г",
    re.IGNORECASE,
)
PROTEIN_SINGLE_RE = re.compile(
    rf"{PROTEIN_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*г",
    re.IGNORECASE,
)

FAT_PM_RE = re.compile(
    rf"{FAT_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*±\s*({NUMBER_RE})\s*г",
    re.IGNORECASE,
)
FAT_RANGE_RE = re.compile(
    rf"{FAT_LABEL_RE}[^\d]*:\s*{DASH_RANGE_RE.pattern}\s*г",
    re.IGNORECASE,
)
FAT_SINGLE_RE = re.compile(
    rf"{FAT_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*г",
    re.IGNORECASE,
)

CAL_PM_RE = re.compile(
    rf"{CALORIES_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*±\s*({NUMBER_RE})\s*(?:ккал|cal)",
    re.IGNORECASE,
)
CAL_RANGE_RE = re.compile(
    rf"{CALORIES_LABEL_RE}[^\d]*:\s*{DASH_RANGE_RE.pattern}\s*(?:ккал|cal)",
    re.IGNORECASE,
)
CAL_SINGLE_RE = re.compile(
    rf"{CALORIES_LABEL_RE}[^\d]*:\s*({NUMBER_RE})\s*(?:ккал|cal)",
    re.IGNORECASE,
)

# Patterns for ``smart_input``.
BAD_SUGAR_UNIT_RE = re.compile(
    rf"\b{SUGAR_WORD_RE.pattern}\s*[:=]?\s*{NUMBER_RE}\s*(?:xe|хе|ед)\b(?!\s*[\d=:])"
)
BAD_XE_UNIT_RE = re.compile(
    rf"\b{XE_LABEL_RE.pattern}\s*[:=]?\s*{NUMBER_RE}\s*(?:ммоль(?:/л)?|mmol(?:/l)?|ед)\b(?![=:])"
)
BAD_DOSE_UNIT_RE = re.compile(
    rf"\b{DOSE_WORD_RE.pattern}\s*[:=]?\s*{NUMBER_RE}\s*(?:ммоль(?:/л)?|mmol(?:/l)?|xe|хе)\b(?![=:])"
)

SUGAR_VALUE_RE = re.compile(
    rf"\b{SUGAR_WORD_RE.pattern}\s*[:=]?\s*({NUMBER_RE})(?![.,])(?=(?:\s*(?:ммоль/?л|mmol/?l))?\b)"
)
SUGAR_UNIT_RE = re.compile(rf"\b({NUMBER_RE})\s*(ммоль/?л|mmol/?l)\b")
XE_VALUE_RE = re.compile(rf"\b{XE_LABEL_RE.pattern}\s*[:=]?\s*({NUMBER_RE})(?![.,])\b")
XE_UNIT_RE = re.compile(rf"\b({NUMBER_RE})\s*(?:xe|хе)\b")
# ``dose`` may be followed immediately by another token (e.g. ``"carbs=30"``).
# ``\b`` would fail in such cases, so we use a lookahead that ensures the
# number is terminated by a non-numeric character or end of string.
DOSE_VALUE_RE = re.compile(
    rf"\b{DOSE_WORD_RE.pattern}\s*[:=]?\s*({NUMBER_RE})(?=$|\s|[^0-9a-zA-Z.,])"
)
DOSE_UNIT_RE = re.compile(rf"\b({NUMBER_RE})\s*(?:ед\.?|units?|u)\b")
# Accepts numbers even with a trailing separator for error detection in
# ``smart_input``.
ONLY_NUMBER_RE = re.compile(r"\s*(\d+[.,]?\d*)\s*")

EXPLICIT_SUGAR_RE = re.compile(rf"\b{SUGAR_WORD_RE.pattern}\b")
EXPLICIT_XE_RE = re.compile(rf"\b{XE_LABEL_RE.pattern}\b")
EXPLICIT_DOSE_RE = re.compile(rf"\b{DOSE_WORD_RE.pattern}\b")

# Helpers for first-line detection in ``extract_nutrition_info``.
FIRST_LINE_INFO_RE = re.compile(r"\d|углевод|[хx][еe]", re.IGNORECASE)


def _safe_float(value: object) -> float | None:
    """Возвращает число из строки.

    Принимает запятую или точку как разделитель. Если передан объект,
    не являющийся строкой, или число не удаётся распознать, возвращается
    ``None``.

    Args:
        value: Произвольный объект. Нестроковые значения приводят к ``None``.

    Returns:
        Число с плавающей точкой или ``None``. Значения ``NaN`` и
        бесконечности также преобразуются в ``None``.

    Examples:
        >>> _safe_float("1,5")
        1.5
    """
    if not isinstance(value, str):
        return None
    try:
        result = float(value.strip().replace(",", "."))
    except ValueError:
        return None
    return result if math.isfinite(result) else None


@dataclass
class NutritionInfo:
    """Parsed nutrition values."""

    weight_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None
    calories_kcal: float | None = None
    xe: float | None = None


def _extract_labeled_value(
    text: str,
    pm_re: re.Pattern[str],
    range_re: re.Pattern[str],
    single_re: re.Pattern[str],
) -> float | None:
    """Generic helper to parse labeled numeric values.

    Supports ``a ± b`` and ``a–b`` formats, returning the central value ``a``
    for ``±`` and the average for ranges.
    """

    rng = pm_re.search(text)
    if rng:
        first = _safe_float(rng.group(1))
        second = _safe_float(rng.group(2))
        if first is not None and second is not None:
            return first
    rng = range_re.search(text)
    if rng:
        first = _safe_float(rng.group(1))
        second = _safe_float(rng.group(2))
        if first is not None and second is not None:
            return (first + second) / 2
    m = single_re.search(text)
    if m:
        return _safe_float(m.group(1))
    return None


def extract_nutrition_info(text: object) -> NutritionInfo:
    """Извлекает пищевую информацию из произвольной строки.

    Поддерживаются варианты ``"углеводы: 30 г"``, ``"XE: 2-3"``,
    ``"2–3 ХЕ"`` и записи с погрешностью ``"a ± b"`` для всех полей.
    Десятичная часть может быть отделена запятой. При указании
    ``"a ± b"`` возвращается центральное значение ``a``, а ``b``
    игнорируется.

    Args:
        text: Строка с описанием продукта или блюда.

    Returns:
        :class:`NutritionInfo` с распознанными значениями.
    """

    if not isinstance(text, str):
        return NutritionInfo()

    # На этом этапе ``text`` гарантированно строка.
    # Если первая строка не содержит цифр или ключевых слов,
    # считаем её названием блюда и игнорируем
    lines = text.splitlines()
    if len(lines) > 1 and not FIRST_LINE_INFO_RE.search(lines[0]):
        text = "\n".join(lines[1:])

    result = NutritionInfo()

    # Парсим углеводы (carbs)
    m = CARBS_LABELED_PM_RE.search(text)
    if m:
        first = _safe_float(m.group(1))
        second = _safe_float(m.group(2))
        if first is not None and second is not None:
            result.carbs_g = first
    else:
        m = CARBS_LABELED_RANGE_RE.search(text)
        if m:
            first = _safe_float(m.group(1))
            second = _safe_float(m.group(2))
            if first is not None and second is not None:
                result.carbs_g = (first + second) / 2
        else:
            m = CARBS_LABEL_RE.search(text)
            if m:
                result.carbs_g = _safe_float(m.group(1))

    # Диапазон XE c двоеточием (например XE: 2±1 или XE: 2–3)
    rng = XE_COLON_PM_RE.search(text)
    if rng:
        first = _safe_float(rng.group(1))
        second = _safe_float(rng.group(2))
        if first is not None and second is not None:
            result.xe = first
    else:
        rng = XE_COLON_RANGE_RE.search(text)
        if rng:
            first = _safe_float(rng.group(1))
            second = _safe_float(rng.group(2))
            if first is not None and second is not None:
                result.xe = (first + second) / 2
        else:
            m = XE_COLON_SINGLE_RE.search(text)
            if m:
                result.xe = _safe_float(m.group(1))
            if result.xe is None:
                rng = XE_PM_RE.search(text)
                if rng:
                    first = _safe_float(rng.group(1))
                    second = _safe_float(rng.group(2))
                    if first is not None and second is not None:
                        result.xe = first
            if result.xe is None:
                rng = XE_RANGE_RE.search(text)
                if rng:
                    first = _safe_float(rng.group(1))
                    second = _safe_float(rng.group(2))
                    if first is not None and second is not None:
                        result.xe = (first + second) / 2

    # Диапазон углеводов (carbs) если не найдено
    if result.carbs_g is None:
        rng = CARBS_PM_RE.search(text)
        if rng:
            first = _safe_float(rng.group(1))
            second = _safe_float(rng.group(2))
            if first is not None and second is not None:
                result.carbs_g = first
    if result.carbs_g is None:
        rng = CARBS_RANGE_RE.search(text)
        if rng:
            first = _safe_float(rng.group(1))
            second = _safe_float(rng.group(2))
            if first is not None and second is not None:
                result.carbs_g = (first + second) / 2

    # Дополнительные поля
    result.weight_g = _extract_labeled_value(
        text, WEIGHT_PM_RE, WEIGHT_RANGE_RE, WEIGHT_SINGLE_RE
    )
    result.protein_g = _extract_labeled_value(
        text, PROTEIN_PM_RE, PROTEIN_RANGE_RE, PROTEIN_SINGLE_RE
    )
    result.fat_g = _extract_labeled_value(text, FAT_PM_RE, FAT_RANGE_RE, FAT_SINGLE_RE)
    result.calories_kcal = _extract_labeled_value(
        text, CAL_PM_RE, CAL_RANGE_RE, CAL_SINGLE_RE
    )

    return result


def smart_input(message: str) -> dict[str, float | None]:
    """Парсит сырое сообщение с показателями сахара, ХЕ и дозы инсулина.

    Функция пытается распознать значения сахара крови, хлебных единиц и дозы
    инсулина из произвольного текста. Поддерживаются числовые значения с
    разделителем ``","`` или ``".`` и локализованные термины вроде
    ``"сахар"`` и ``"доза"``. Если после названия показателя указаны
    единицы, не соответствующие ему (например, ``"сахар 7 XE"``), или
    вместо числа идёт произвольный текст (``"доза=abc"``), будет вызван
    ``ValueError``. Одиночное число без явного указания показателя
    считается неоднозначным и также приводит к ``ValueError``.

    Args:
        message: Исходное сообщение пользователя.

    Returns:
        Словарь с ключами ``"sugar"``, ``"xe"`` и ``"dose"``. Отсутствующие
        значения возвращаются как ``None``.

    Examples:
        >>> smart_input("sugar=7 xe=3 dose=4")
        {'sugar': 7.0, 'xe': 3.0, 'dose': 4.0}
        >>> smart_input("7 ммоль/л, 3 XE")
        {'sugar': 7.0, 'xe': 3.0, 'dose': None}
        >>> smart_input("сахар 7 XE")
        Traceback (most recent call last):
        ...
        ValueError: mismatched unit for sugar
        >>> smart_input("5")
        Traceback (most recent call last):
        ...
        ValueError: ambiguous number without keyword
    """

    if not isinstance(message, str):
        raise ValueError("message must be a string")

    text = message.lower()
    result: dict[str, float | None] = {"sugar": None, "xe": None, "dose": None}

    # Проверка на неверные единицы измерения после явных названий показателей
    if BAD_SUGAR_UNIT_RE.search(text):
        raise ValueError("mismatched unit for sugar")
    if BAD_XE_UNIT_RE.search(text):
        raise ValueError("mismatched unit for xe")
    if BAD_DOSE_UNIT_RE.search(text):
        raise ValueError("mismatched unit for dose")

    # --- Sugar ---
    m = SUGAR_VALUE_RE.search(text)
    if m:
        result["sugar"] = _safe_float(m.group(1))
    else:
        m = SUGAR_UNIT_RE.search(text)
        if m:
            result["sugar"] = _safe_float(m.group(1))

    # --- XE ---
    m = XE_VALUE_RE.search(text)
    if m:
        result["xe"] = _safe_float(m.group(1))
    else:
        m = XE_UNIT_RE.search(text)
        if m:
            result["xe"] = _safe_float(m.group(1))

    # --- Dose ---
    m = DOSE_VALUE_RE.search(text)
    if m:
        result["dose"] = _safe_float(m.group(1))
    else:
        m = DOSE_UNIT_RE.search(text)
        if m:
            result["dose"] = _safe_float(m.group(1))

    if all(v is None for v in result.values()):
        m = ONLY_NUMBER_RE.fullmatch(text)
        if m:
            raise ValueError("ambiguous number without keyword")

    # Явное упоминание показателя без числового значения считается ошибкой.
    for key, pattern in [
        ("sugar", EXPLICIT_SUGAR_RE),
        ("xe", EXPLICIT_XE_RE),
        ("dose", EXPLICIT_DOSE_RE),
    ]:
        if pattern.search(text) and result[key] is None:
            raise ValueError(f"invalid number for {key}")

    return result

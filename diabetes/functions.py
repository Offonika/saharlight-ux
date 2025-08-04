"""Утилиты для расчёта болюса и разбора пищевой информации."""

from dataclasses import dataclass
import re


def _safe_float(value: str) -> float | None:
    """Возвращает число из строки.

    Принимает запятую или точку как разделитель. Если передана не строка
    или число не удаётся распознать, возвращается ``None``.

    Args:
        value: Строка с числом, например ``"1,5"`` или ``"2.0"``.

    Returns:
        Число с плавающей точкой или ``None``.

    Examples:
        >>> _safe_float("1,5")
        1.5
    """
    if not isinstance(value, str):
        return None
    try:
        return float(value.strip().replace(",", "."))
    except ValueError:
        return None


@dataclass
class PatientProfile:
    """Профиль пациента для расчёта болюса.

    Attributes:
        icr: Коэффициент чувствительности к углеводам.
        cf: Коррекционный фактор для сахара крови.
        target_bg: Целевой уровень сахара.
    """

    icr: float
    cf: float
    target_bg: float


def calc_bolus(carbs_g: float, current_bg: float, profile: PatientProfile) -> float:
    """Рассчитывает дозу инсулина по углеводам и сахару.

    Args:
        carbs_g: Количество углеводов в граммах.
        current_bg: Текущий уровень сахара в крови.
        profile: Настройки пациента с коэффициентами.

    Returns:
        Округлённый болюс в единицах инсулина.

    Examples:
        >>> profile = PatientProfile(icr=10, cf=50, target_bg=5.5)
        >>> calc_bolus(60, 7.0, profile)
        6.1
    """
    if profile.icr <= 0:
        raise ValueError("Profile icr must be greater than 0")
    if profile.cf <= 0:
        raise ValueError("Profile cf must be greater than 0")
    if profile.target_bg <= 0:
        raise ValueError("Profile target_bg must be greater than 0")
    if carbs_g < 0:
        raise ValueError("carbs_g must be non-negative")
    if current_bg < 0:
        raise ValueError("current_bg must be non-negative")
    meal = carbs_g / profile.icr
    correction = max(0, (current_bg - profile.target_bg) / profile.cf)
    return round(meal + correction, 1)


def extract_nutrition_info(text: str) -> tuple[float | None, float | None]:
    """Извлекает углеводы и ХЕ из произвольной строки.

    Поддерживаются варианты: ``"углеводы: 30 г"``, ``"XE: 2-3"``,
    ``"2–3 ХЕ"`` и записи с погрешностью ``"a ± b"``.
    Десятичная часть может быть отделена запятой. При указании
    ``"a ± b"`` возвращается центральное значение ``a``, а ``b``
    игнорируется.

    Args:
        text: Строка с описанием продукта или блюда.

    Returns:
        Кортеж ``(carbs, xe)``, где значения могут быть ``None``.

    Examples:
        >>> extract_nutrition_info("углеводы: 30 г, XE: 2")
        (30.0, 2.0)
        >>> extract_nutrition_info("2–3 ХЕ")
        (None, 2.5)
        >>> extract_nutrition_info("углеводы: 45 ± 5 г")
        (45.0, None)
    """
    if not isinstance(text, str):
        return (None, None)
    # Если ответ начинается с названия блюда, игнорируем первую строку
    lines = text.splitlines()
    if len(lines) > 1:
        text = "\n".join(lines[1:])

    carbs = xe = None
    # Парсим углеводы (carbs)
    m = re.search(
        r"углевод[^\d]*:\s*(\d+[.,]?\d*)\s*(?:г)?\s*±\s*(\d+[.,]?\d*)\s*г",
        text,
        re.IGNORECASE,
    )
    if m:
        first = _safe_float(m.group(1))
        second = _safe_float(m.group(2))
        if first is not None and second is not None:
            # В формате "a ± b" возвращаем центральное значение "a"
            # Погрешность "b" пока игнорируется
            carbs = first
    else:
        m = re.search(r"углевод[^\d]*:\s*([\d.,]+)\s*г", text, re.IGNORECASE)
        if m:
            carbs = _safe_float(m.group(1))
    # Диапазон XE c двоеточием (например XE: 2±1 или XE: 2–3)
    rng = re.search(
        r"\b(?:[хx][еe]|xe)\s*:\s*(\d+[.,]?\d*)\s*±\s*(\d+[.,]?\d*)",
        text,
        re.IGNORECASE,
    )
    if rng:
        first = _safe_float(rng.group(1))
        second = _safe_float(rng.group(2))
        if first is not None and second is not None:
            # Возвращаем центральное значение "a" из записи "a ± b"
            xe = first
    else:
        rng = re.search(
            r"\b(?:[хx][еe]|xe)\s*:\s*(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)",
            text,
            re.IGNORECASE,
        )
        if rng:
            first = _safe_float(rng.group(1))
            second = _safe_float(rng.group(2))
            if first is not None and second is not None:
                xe = (first + second) / 2
        else:
            # Одинарное значение XE: 3.1
            m = re.search(
                r"\b(?:[хx][еe]|xe)\s*:\s*([\d.,]+)",
                text,
                re.IGNORECASE,
            )
            if m:
                xe = _safe_float(m.group(1))
            # Диапазон XE без двоеточия (например 2±1 ХЕ или 2–3 ХЕ)
            if xe is None:
                rng = re.search(
                    r"(\d+[.,]?\d*)\s*±\s*(\d+[.,]?\d*)\s*(?:[хx][еe]|xe)",
                    text,
                    re.IGNORECASE,
                )
                if rng:
                    first = _safe_float(rng.group(1))
                    second = _safe_float(rng.group(2))
                    if first is not None and second is not None:
                        # Погрешность игнорируется, берём только значение "a"
                        xe = first
            if xe is None:
                rng = re.search(
                    r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*(?:[хx][еe]|xe)",
                    text,
                    re.IGNORECASE,
                )
                if rng:
                    first = _safe_float(rng.group(1))
                    second = _safe_float(rng.group(2))
                    if first is not None and second is not None:
                        xe = (first + second) / 2
    # Диапазон углеводов (carbs) если не найдено
    if carbs is None:
        rng = re.search(
            r"(\d+[.,]?\d*)\s*(?:г)?\s*±\s*(\d+[.,]?\d*)\s*г",
            text,
            re.IGNORECASE,
        )
        if rng:
            first = _safe_float(rng.group(1))
            second = _safe_float(rng.group(2))
            if first is not None and second is not None:
                # Центральное значение при указании "a ± b"
                carbs = first
    if carbs is None:
        rng = re.search(
            r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*г",
            text,
            re.IGNORECASE,
        )
        if rng:
            first = _safe_float(rng.group(1))
            second = _safe_float(rng.group(2))
            if first is not None and second is not None:
                carbs = (first + second) / 2
    return carbs, xe

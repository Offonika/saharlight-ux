import re


def parse_values(text: str) -> dict[str, float]:
    parts = dict(re.findall(r"(\w+)\s*=\s*([\d.,-]+)", text))
    result = {}
    if "xe" in parts:
        result["xe"] = float(parts["xe"].replace(",", "."))
    if "carbs" in parts:
        result["carbs"] = float(parts["carbs"].replace(",", "."))
    if "dose" in parts:
        result["dose"] = float(parts["dose"].replace(",", "."))
    if "sugar" in parts:
        result["sugar"] = float(parts["sugar"].replace(",", "."))
    if "сахар" in parts:
        result["sugar"] = float(parts["сахар"].replace(",", "."))
    return result


def test_parse_comma_and_negative_values():
    text = "carbs=10,5 dose=-1,5 xe=2 sugar=5,6"
    parsed = parse_values(text)
    assert parsed == {
        "carbs": 10.5,
        "dose": -1.5,
        "xe": 2.0,
        "sugar": 5.6,
    }


def test_parse_negative_numbers():
    text = "carbs=-10.5 dose=-2 xe=-1,0 sugar=-4,2"
    parsed = parse_values(text)
    assert parsed == {
        "carbs": -10.5,
        "dose": -2.0,
        "xe": -1.0,
        "sugar": -4.2,
    }


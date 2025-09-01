from types import SimpleNamespace

from services.api.app.diabetes.utils.jobs import dbg_jobs_dump


class _QueueList:
    def __init__(self) -> None:
        self.jobs = [SimpleNamespace(id="1", name="foo")]


def test_dbg_jobs_dump_list_attr() -> None:
    jq = _QueueList()
    assert dbg_jobs_dump(jq) == [("1", "foo")]


class _QueueProperty:
    def __init__(self) -> None:
        self._jobs = [SimpleNamespace(id="1", name="bar")]

    @property
    def jobs(self):  # type: ignore[override]
        return self._jobs


def test_dbg_jobs_dump_property() -> None:
    jq = _QueueProperty()
    assert dbg_jobs_dump(jq) == [("1", "bar")]


class _QueueDict:
    def __init__(self) -> None:
        self.jobs = {
            "a": [SimpleNamespace(id="1", name="baz")],
            "b": [SimpleNamespace(id="2", name="qux")],
        }


def test_dbg_jobs_dump_dict_attr() -> None:
    jq = _QueueDict()
    result = dbg_jobs_dump(jq)
    assert ("1", "baz") in result
    assert ("2", "qux") in result

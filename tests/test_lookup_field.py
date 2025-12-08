from dataclasses import asdict, dataclass, field

import pytest

from proteingym.base.lookup_field import LookupField


@pytest.fixture()
def calls():
    return []


@pytest.fixture
def lookup_field(calls):
    class MyLookupField(LookupField):
        identifier = "my_id"

        def resolve(self, id_: str):
            calls.append(1)
            return {"bar": "db1", "baz": "db2"}

    return MyLookupField


@pytest.fixture
def my_class(calls, lookup_field):
    @dataclass
    class MyClass:
        my_id: str | None = None
        bar: str | None = field(default=lookup_field(None))
        baz: str | None = field(default=lookup_field(None))

    return MyClass


def test_lookup_field_identifier_is_field_is_error(lookup_field):
    with pytest.raises(ValueError):

        class Bad:
            my_id = field(default=lookup_field(None))


def test_db_field_no_id(my_class):
    obj = my_class()
    assert obj.bar is None


def test_db_field_resolves(my_class):
    obj = my_class(my_id="x")
    assert obj.bar == "db1" and obj.baz == "db2"


def test_db_field_dump(my_class):
    assert asdict(my_class(my_id="x")) == {"my_id": "x", "bar": "db1", "baz": "db2"}


def test_db_field_manual_data_not_overwritten(my_class):
    obj = my_class(my_id="x", bar="other")
    assert obj.baz == "db2" and obj.bar == "other"


def test_db_field_calls_lazy(my_class, calls):
    obj = my_class(my_id="x")
    assert obj.__dict__.get("_bar", None) is None and obj.bar is not None


def test_db_field_calls_once(my_class, calls):
    obj = my_class(my_id="x")
    _ = obj.bar
    _ = obj.baz
    assert calls == [1]

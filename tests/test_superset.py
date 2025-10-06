from proteingym.base.superset import Superset


def test_iterate_over_empty_superset() -> None:
    """Test that iterating over an empty superset does not yield any elements."""
    superset = Superset(dataset=None, slices=[])
    for _ in superset:
        raise AssertionError("Should not iterate over empty superset")

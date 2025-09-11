"""
Module for testing dataset operators.
"""


from pg2_dataset.dataset import Dataset


def test_dataset_equals_itself() -> None:
    """A dataset should equal itself."""
    dataset = Dataset(
        name="Test Dataset",
        description="A dataset for testing purposes.",
        assay_conditions=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[],
    )
    assert dataset == dataset
import io

import pytest

from pg2_dataset.dataset import Dataset


class TestDataset:
    @pytest.fixture
    def example_toml(self):
        return """
    name = "test_name"
    description = "test_description"
    doi = "test_doi"
    source = "test_source"

    [assays_meta]
    file_path = "records.csv"
    sequence_feature = "feature1"

    [assays_meta.assays.target1]
    features = ["feature1", "feature2"]
    description = "lorem ipsum"
    [records.assays.target1.constants]
    key_one = "1"
    key_two = 2

    [assays_meta.assays.target2]
    features = ["feature1"]
    description = "dolor sit amet"
    """

    def test_dataset_from_toml(self, example_toml):
        ds = Dataset.from_toml(io.StringIO(example_toml))
        assert isinstance(ds, Dataset)

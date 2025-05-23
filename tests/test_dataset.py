import pytest

from pg2_dataset.dataset import Dataset


class TestDataset:
    @pytest.fixture
    def example_toml(self):
        return """
    [metadata]
    name = "test_name"
    description = "test_description"
    doi = "test_doi"
    source = "test_source"

    [resources]
    records = "records.csv"

    [records]
    sequence_feature = "feature1"

    [records.assays.target1]
    features = ["feature1", "feature2"]
    description = "lorem ipsum"
    [records.assays.target1.constants]
    key_one = "1"
    key_two = 2

    [records.assays.target2]
    features = ["feature1"]
    description = "dolor sit amet"
    """

    @pytest.fixture
    def example_toml_file_path(self, example_toml, tmpdir):
        # FIXME: allow reading from file-like so possible to use io.StringIO
        file_path = tmpdir / "example.toml"

        with open(file_path, "w") as file:
            file.write(example_toml)

        return str(file_path)

    def test_dataset_from_toml(self, example_toml_file_path):
        ds = Dataset.from_toml(example_toml_file_path)
        assert isinstance(ds, Dataset)

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
    [assays.assay_name_one.constants]
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

    @pytest.mark.slow
    def test_dataset_from_remote(self, tmpdir):
        toml = """
        [resources]
        records = "https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv"

        [records]
        sequence_feature = "mutated_sequence"

        [assays.DMS_score]
        description = "lorem ipsum"

        [assays.DMS_score.constants]
        key_one = "1"
        key_two = 2

        [assays.DMS_score_bin]
        description = "dolor sit amet"
        """
        file_path = tmpdir / "example.toml"

        with open(file_path, "w") as file:
            file.write(toml)

        ds = Dataset.from_toml(toml_file=str(file_path))

        print(ds.records.data_frame)

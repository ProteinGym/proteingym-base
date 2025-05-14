import pytest

from pg2_dataset.primitives.setting import DatasetSettings


@pytest.fixture
def example_toml():
    return """
[artifacts]
records = "records.csv"
structure = "structure.cif"

[records]
sequence_feature = "feature1"
columns = ["feature1", "feature2", "target1", "target2"]
schemas = ["pl.String", "pl.String", "pl.Float32", "pl.Float32"]

[metadata]
name = "test_name"
description = "test_description"
doi = "test_doi"
source = "test_source"

[assays.assay_name_one]
features = ["feature1", "feature2"]
target = "target1"
description = "lorem ipsum"
[assays.assay_name_one.constants]
key_one = "1"
key_two = 2

[assays.assay_name_two]
features = ["feature1"]
target = "target2"
description = "dolor sit amet"
"""


class TestSetting:
    @pytest.fixture
    def example_toml_file_path(self, example_toml, tmpdir):
        file_path = tmpdir / "example.toml"

        with open(file_path, "w") as file:
            file.write(example_toml)

        return str(file_path)

    def test_get_artifacts_correctly(self, example_toml_file_path):
        DatasetSettings._toml_file = example_toml_file_path
        settings = DatasetSettings()

        assert settings.artifacts.records == "records.csv"
        assert settings.artifacts.structure == "structure.cif"

    def test_get_assays_correctly(self, example_toml_file_path):
        DatasetSettings._toml_file = example_toml_file_path
        settings = DatasetSettings()

        assert len(settings.assays) == 2

        assert len(settings.assays["assay_name_one"].features) == 2
        assert len(settings.assays["assay_name_two"].features) == 1

        assert settings.assays["assay_name_one"].target == "target1"
        assert settings.assays["assay_name_two"].target == "target2"

        assert len(settings.assays["assay_name_one"].constants) == 2
        assert len(settings.assays["assay_name_two"].constants) == 0

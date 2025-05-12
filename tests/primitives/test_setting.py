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

[[assays]]
name = "assay_name_one"
description = "assay_description_one"

[assays.columns]
features = ["feature1", "feature2"]
target = "target1"

[assays.constants]
key_one = "1"
key_two = 2

[[assays]]
name = "assay_name_two"
description = "assay_description_two"

[assays.columns]
features = ["feature1"]
target = "target2"
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

        assert len(settings.assays) == 2, "only 2 assays"

        assert len(settings.assays[0].columns.features) == 2, "the first assay has 2 features"
        assert len(settings.assays[1].columns.features) == 1, "the second assay has 1 feature"

        assert settings.assays[0].columns.target == "target1", "the first assay has the target `target1`"
        assert settings.assays[1].columns.target == "target2", "the second assay has the target `target2`"

        assert len(settings.assays[0].constants) == 2, "the first assay has 2 constants"
        assert len(settings.assays[1].constants) == 0, "the second assay has 0 constants"

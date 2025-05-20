import pytest

from pg2_dataset.primitives.meta import DatasetSettings


@pytest.fixture
def example_toml():
    return """
[resources]
records = "records.csv"
structure = "structure.cif"

[metadata]
name = "test_name"
description = "test_description"
doi = "test_doi"
source = "test_source"

[records]
sequence_feature = "feature1"
columns = ["feature1", "feature2", "target1", "target2"]

[records.assays.assay_name_one]
features = ["feature1", "feature2"]
target_name = "target1"
description = "lorem ipsum"

[records.assays.assay_name_one.constants]
key_one = "1"
key_two = 2

[records.assays.assay_name_two]
features = ["feature1"]
target_name = "target2"
description = "dolor sit amet"
"""


class TestSetting:
    @pytest.fixture
    def example_toml_file_path(self, example_toml, tmpdir):
        file_path = tmpdir / "example.toml"

        with open(file_path, "w") as file:
            file.write(example_toml)

        return str(file_path)

    def test_get_resources_correctly(self, example_toml_file_path):
        settings = DatasetSettings.parse_toml(example_toml_file_path)

        assert settings.resources.records == "records.csv"
        assert settings.resources.structure == "structure.cif"

    def test_get_assays_correctly(self, example_toml_file_path):
        settings = DatasetSettings.parse_toml(example_toml_file_path)

        assert len(settings.records.assays) == 2

        assert len(settings.records.assays["assay_name_one"].features) == 2
        assert len(settings.records.assays["assay_name_two"].features) == 1

        assert settings.records.assays["assay_name_one"].target_name == "target1"
        assert settings.records.assays["assay_name_two"].target_name == "target2"

        assert len(settings.records.assays["assay_name_one"].constants) == 2
        assert len(settings.records.assays["assay_name_two"].constants) == 0

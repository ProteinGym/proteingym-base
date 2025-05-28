import io

import pytest

from pg2_dataset.primitives.meta import AssaysMeta, DatasetMeta, SingleAssayMeta


@pytest.fixture
def example_toml():
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

[assays_meta.assays.target1.constants]
key_one = "1"
key_two = 2

[assays_meta.assays.target2]
features = ["feature1"]
description = "dolor sit amet"
"""


class TestDatasetMeta:
    def test_dataset_from_toml_file_like(self, example_toml):
        ds = DatasetMeta.from_toml(io.StringIO(example_toml))
        assert isinstance(ds, DatasetMeta)

    def test_dataset_from_toml_path(self, example_toml, tmpdir):
        file_path = tmpdir / "example.toml"

        with open(file_path, "w") as file:
            file.write(example_toml)
        ds = DatasetMeta.from_toml(file_path)
        assert isinstance(ds, DatasetMeta)

    def test_get_assays_correctly(self, example_toml):
        meta = DatasetMeta.from_toml(io.StringIO(example_toml))

        assert len(meta.assays_meta.assays) == 2

        assert len(meta.assays_meta.assays["target1"].features) == 2
        assert len(meta.assays_meta.assays["target2"].features) == 1

        assert len(meta.assays_meta.assays["target1"].constants) == 2
        assert len(meta.assays_meta.assays["target2"].constants) == 0


class TestAssaysMeta:
    def test_columns_property(self):
        meta = AssaysMeta(
            sequence_feature="sequence",
            engineering_round_feature="foo",
        )
        assert meta.columns == ["foo", "sequence"]

    def test_columns_property_with_assays(self):
        meta = AssaysMeta(
            sequence_feature="seq",
            assays={"activity": SingleAssayMeta(), "expression": SingleAssayMeta()},
        )
        assert meta.columns == ["activity", "expression", "seq"]

    def test_columns_property_with_assays_and_features(self):
        meta = AssaysMeta(
            sequence_feature="seq",
            assays={
                "activity": SingleAssayMeta(features=["foo", "bar"]),
                "expression": SingleAssayMeta(features=["baz"]),
            },
        )
        assert meta.columns == ["activity", "bar", "baz", "expression", "foo", "seq"]

import io
import zipfile

import pytest

from pg2_dataset.dataset import Dataset, Manifest


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

    [structures_meta]
    file_path = "tests/test_data/structures/5kua_pdb.pdb"

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

    def test_dataset_from_toml(self, example_toml):
        ds = Manifest.from_path(io.StringIO(example_toml)).ingest()
        assert isinstance(ds, Dataset)

    def test_manifest_from_toml_path_like(self, example_toml):
        manifest = Manifest.from_path(io.StringIO(example_toml))
        assert isinstance(manifest, Manifest)

    def test_manifest_from_toml_path(self, example_toml, tmpdir):
        file_path = tmpdir / "example.toml"

        with open(file_path, "w") as file:
            file.write(example_toml)
        manifest = Manifest.from_path(file_path)
        assert isinstance(manifest, Manifest)

    def test_get_assays_correctly(self, example_toml):
        meta = Manifest.from_path(io.StringIO(example_toml))

        assert len(meta.assays_meta.assays) == 2

        assert len(meta.assays_meta.assays["target1"].features) == 2
        assert len(meta.assays_meta.assays["target2"].features) == 1

        assert len(meta.assays_meta.assays["target1"].constants) == 2
        assert len(meta.assays_meta.assays["target2"].constants) == 0

    def test_persist(self, example_toml, tmpdir):
        manifest = Manifest.from_path(io.StringIO(example_toml))
        dataset = manifest.ingest()

        zip_path = tmpdir / "dataset.zip"

        dataset.persist(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zipf:
            files = zipf.namelist()

        assert len(files) == 2
        assert "manifest.toml" in files
        assert "structure/5kua_pdb.pdb" in files

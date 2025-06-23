import io
import zipfile

import pytest
from pydantic import ValidationError

from pg2_dataset.backends.structure import Structure
from pg2_dataset.dataset import Dataset, Manifest
from pg2_dataset.primitives.meta import StructuresMeta


class TestDataset:
    @pytest.fixture
    def example_toml(self):
        return """
    name = "test_name"
    description = "test_description"
    doi = "test_doi"
    source = "test_source"

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

    @pytest.fixture
    def invalid_toml(self):
        return """
    name = "test_name"
    description = "test_description"
    doi = "test_doi"
    source = "test_source"

    [assays_meta]
    file_path = "records.csv"
    sequence_feature = "feature1"
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

    def test_invalid_assays_should_raise_exception(self, invalid_toml):
        with pytest.raises(ValidationError) as exc:
            Manifest.from_path(io.StringIO(invalid_toml)).ingest()

        assert "file_path: records.csv does not exist" in str(exc.value)

    def test_persist(self, example_toml, tmpdir):
        ds = Manifest.from_path(io.StringIO(example_toml)).ingest()

        zip_path = tmpdir / "dataset.zip"

        ds.persist(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zipf:
            files = zipf.namelist()
            zipf.extractall()

            assert len(files) == 2
            assert "manifest.toml" in files
            assert "structure/5kua_pdb.pdb" in files

            manifest = Manifest.from_path("manifest.toml")
            assert manifest.name == "test_name"
            assert manifest.structures_meta.file_path == "structure"

            dataset = Structure(meta=StructuresMeta(file_path="structure/5kua_pdb.pdb"))
            assert len(dataset.structures) == 1

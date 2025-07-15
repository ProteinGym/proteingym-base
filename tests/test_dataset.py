import io
import tempfile
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from pg2_dataset.backends.structure import Structure
from pg2_dataset.dataset import Dataset, Manifest
from pg2_dataset.primitives.meta import StructuresMeta


@pytest.fixture
def example_toml() -> str:
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


class TestDataset:

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

    def test_invalid_assays_should_raise_exception(self):
        invalid_toml = """
        name = "test_name"
        description = "test_description"
        doi = "test_doi"
        source = "test_source"

        [assays_meta]
        file_path = "records.csv"
        sequence_feature = "feature1"
        """

        with pytest.raises(
            ValidationError, match="File path does not exists: file_path=records.csv"
        ):
            Manifest.from_path(io.StringIO(invalid_toml)).ingest()

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

    def test_from_path_with_correct_file(self, example_toml, tmpdir):
        manifest = Manifest.from_path(io.StringIO(example_toml))

        zip_path = Path(tmpdir) / "dataset.zip"
        manifest.ingest().persist(zip_path)

        dataset = Dataset.from_path(zip_path)

        assert "5kua_pdb.pdb" in dataset.structure.structures

    def test_from_path_with_invalid_file_should_raise_exceptions(self, tmpdir):
        invalid_zip_path = Path(tmpdir) / "invalid_dataset.zip"

        with pytest.raises(
            FileNotFoundError,
            match=f"No such file or directory: '{str(invalid_zip_path)}'",
        ):
            Dataset.from_path(invalid_zip_path)

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmpfile:
            Path(tmpfile.name).touch()

            with pytest.raises(zipfile.BadZipFile, match="File is not a zip file"):
                Dataset.from_path(tmpfile.name)

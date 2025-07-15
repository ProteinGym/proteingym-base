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
def manifest_contents() -> str:
    return """
version = "1.0.0"
name = "Example Dataset"
description = "This is an example dataset for demonstration purposes."

[[assay_conditions]]
name = "PH"
description = "pH level of the samples"
unit = "pH"
data_type = "float"

[[sequences]]
file_path = "sequences.fasta"

[[structures]]
file_path = "structures.pdb"

[[msas]]
file_path = "msas.a3m"

[[assays]]
file_path = "assays.csv"
"""


@pytest.fixture
def manifest_path(tmp_path: Path, manifest_contents: str) -> Path:
    """A (temporary) manifest file."""
    manifest_file = tmp_path / "manifest.toml"
    manifest_file.write_text(manifest_contents, encoding="utf-8")
    return manifest_file


def test_manifest_contents_in_documentation(manifest_contents: str) -> None:
    """Check if the manifest contents are present in the documentation.
    
    If this tests fails, it indicates that the documentation is not up-to-date
    with the tested manifest contents, or vice versa. Solve this by updating
    outdated contents.
    
    Or, the documentation or test file is moved. Solve this by updating the path.
    """
    documenation_path = Path(__file__).parent.parent / Path("docs/manifest.md")

    assert documenation_path.exists(), f"Documentation file does not exist: {documenation_path}"
    assert manifest_contents in documenation_path.read_text(), "Test manifest contents not found in documentation."


def test_manifest_from_path_like(manifest_contents: str) -> None:
    """Happy flow for loading a Manifest from a path-like object."""
    try:
        Manifest.from_path(io.StringIO(manifest_contents))
    except ValidationError as e:
        assert False, f"ValidationError raised: {e}"
    else:
        assert True, "Manifest loaded successfully from path-like object."


def test_manifest_from_path_like_minimal_contents() -> None:
    """The manifest requires only a name at minimum."""
    manifest_contents_minimal = io.StringIO("name = 'dataset'")

    try:
        Manifest.from_path(manifest_contents_minimal)
    except ValidationError as e:
        assert False, f"ValidationError raised: {e}"
    else:
        assert True, "Manifest loaded successfully from path-like object."


def test_manifest_from_path_like_requires_name_field() -> None:
    """The manifest name is a required field."""
    manifest_contents_without_name = io.StringIO("description = 'example description'")

    with pytest.raises(ValidationError, match="validation error for Manifest\nname\n  Field required"):
        Manifest.from_path(manifest_contents_without_name)


def test_manifest_from_path_like_requires_name_field_with_non_zero_length() -> None:
    """The manifest name is required to have non-zero length."""
    manifest_contents_without_name = io.StringIO("name = ''")

    with pytest.raises(ValidationError, match="validation error for Manifest\nname\n  String should have at least 1 character"):
        Manifest.from_path(manifest_contents_without_name)


def test_manifest_from_path_like_version_field_is_semantic() -> None:
    """The manifest version is required to have a semantic version."""
    manifest_contents_with_date_version = io.StringIO("name = 'd'\nversion = '2023-10-05'")  # Try date version format

    with pytest.raises(ValidationError, match="validation error for Manifest\nversion\n  Value error, Invalid version: '2023-10-05'"):
        Manifest.from_path(manifest_contents_with_date_version)


def test_manifest_from_path(manifest_path: Path) -> None:
    """Happy flow for loading a Manifest from a file path."""
    try:
        Manifest.from_path(manifest_path)
    except ValidationError as e:
        assert False, f"ValidationError raised: {e}"
    else:
        assert True, "Manifest loaded successfully from path-like object."


def test_manifest_from_non_existing_path(tmp_path: Path) -> None:
    """The manifest cannot be loaded from a non-existing path."""
    non_existing_path = tmp_path / "non_existing_manifest.toml"
    with pytest.raises(FileNotFoundError, match=f"No such file or directory: '{non_existing_path.as_posix()}'"):
        Manifest.from_path(non_existing_path)


class TestDataset:

    def test_dataset_from_toml(self, manifest_contents):
        ds = Manifest.from_path(io.StringIO(manifest_contents)).ingest()
        assert isinstance(ds, Dataset)

    def test_get_assays_correctly(self, manifest_contents):
        meta = Manifest.from_path(io.StringIO(manifest_contents))

        assert len(meta.assays_meta.assays) == 2

        assert len(meta.assays_meta.assays["target1"].features) == 2
        assert len(meta.assays_meta.assays["target2"].features) == 1

        assert len(meta.assays_meta.assays["target1"].constants) == 2
        assert len(meta.assays_meta.assays["target2"].constants) == 0

    def test_persist(self, manifest_contents, tmpdir):
        ds = Manifest.from_path(io.StringIO(manifest_contents)).ingest()

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

    def test_from_path_with_correct_file(self, manifest_contents, tmpdir):
        manifest = Manifest.from_path(io.StringIO(manifest_contents))

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

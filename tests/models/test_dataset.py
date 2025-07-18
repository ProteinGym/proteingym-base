import io
import tempfile
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from pg2_dataset.models.dataset import Dataset, Manifest


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

[[assays]]
path = "assays.csv"

[[sequences]]
path = "sequences.fasta"

[[structures]]
path = "structures.pdb"

[[msas]]
path = "msas.a3m"
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
    documenation_path = Path(__file__).parent.parent.parent / Path("docs/manifest.md")

    assert documenation_path.exists(), (
        f"Documentation file does not exist: {documenation_path}"
    )
    assert manifest_contents in documenation_path.read_text(), (
        "Test manifest contents not found in documentation."
    )


def test_manifest_from_path_like(manifest_contents: str) -> None:
    """Happy flow for loading a Manifest from a path-like object."""
    try:
        Manifest.from_path(io.StringIO(manifest_contents))
    except ValidationError as e:
        raise AssertionError("ValidationError raised") from e
    else:
        assert True, "Manifest loaded successfully from path-like object."


def test_manifest_from_path_like_minimal_contents() -> None:
    """The manifest requires only a name at minimum."""
    manifest_contents_minimal = io.StringIO("name = 'dataset'")

    try:
        Manifest.from_path(manifest_contents_minimal)
    except ValidationError as e:
        raise AssertionError("ValidationError raised") from e
    else:
        assert True, "Manifest loaded successfully from path-like object."


def test_manifest_from_path_like_requires_name_field() -> None:
    """The manifest name is a required field."""
    manifest_contents_without_name = io.StringIO("description = 'example description'")

    with pytest.raises(
        ValidationError, match="validation error for Manifest\nname\n  Field required"
    ):
        Manifest.from_path(manifest_contents_without_name)


def test_manifest_from_path_like_requires_name_field_with_non_zero_length() -> None:
    """The manifest name is required to have non-zero length."""
    manifest_contents_without_name = io.StringIO("name = ''")

    match = (
        "validation error for Manifest\nname\n  String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        Manifest.from_path(manifest_contents_without_name)


def test_manifest_from_path_like_version_field_is_semantic() -> None:
    """The manifest version is required to have a semantic version."""
    manifest_contents_with_date_version = io.StringIO(
        "name = 'd'\nversion = '2023-10-05'"
    )  # Try date version format

    match = (
        "validation error for Manifest\nversion\n  "
        "Value error, Invalid version: '2023-10-05'"
    )
    with pytest.raises(ValidationError, match=match):
        Manifest.from_path(manifest_contents_with_date_version)


def test_manifest_from_path(manifest_path: Path) -> None:
    """Happy flow for loading a Manifest from a file path."""
    try:
        Manifest.from_path(manifest_path)
    except ValidationError as e:
        raise ValidationError("ValidationError raised") from e
    else:
        assert True, "Manifest loaded successfully from path-like object."


def test_manifest_from_non_existing_path(tmp_path: Path) -> None:
    """The manifest cannot be loaded from a non-existing path."""
    non_existing_path = tmp_path / "non_existing_manifest.toml"
    with pytest.raises(
        FileNotFoundError,
        match=f"No such file or directory: '{non_existing_path.as_posix()}'",
    ):
        Manifest.from_path(non_existing_path)


@pytest.mark.skip(reason="TODO: Update test when moving `ingest` to `Dataset` class")
def test_dataset_from_toml(manifest_contents: str) -> None:
    ds = Manifest.from_path(io.StringIO(manifest_contents)).ingest()
    assert isinstance(ds, Dataset)


def test_manifest_from_path_like_has_assays(manifest_contents: str) -> None:
    """The manifest optionally has assays. See if they are loaded correctly."""
    manifest = Manifest.from_path(io.StringIO(manifest_contents))
    assert len(manifest.assays) == 1, "Expecting one assay"


@pytest.mark.skip(
    reason="TODO: Update the test when adding defaults to the Dataset class"
)
def test_dataset_dump_manifest_file(tmpdir: Path) -> None:
    """When dumping a dataset, the manifest file should be included."""
    dataset = Dataset(name="test")
    zip_path = tmpdir / "dataset.zip"

    dataset.persist(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zipf:
        files = zipf.namelist()
        zipf.extractall()

        assert "manifest.toml" in files


@pytest.mark.skip(reason="TODO: Update test when moving `ingest` to `Dataset` class")
def test_from_path_with_correct_file(tmpdir: Path, manifest_contents: str) -> None:
    manifest = Manifest.from_path(io.StringIO(manifest_contents))

    zip_path = Path(tmpdir) / "dataset.zip"
    manifest.ingest().persist(zip_path)

    dataset = Dataset.from_path(zip_path)

    assert "5kua_pdb.pdb" in dataset.structure.structures


@pytest.mark.skip(reason="TODO: Add a `from_path` method to the Dataset class")
def test_from_path_with_invalid_file_should_raise_exceptions(tmpdir: Path) -> None:
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

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

[[ sequences ]]
sequence_type = "wild_type"
sequence_alphabet = "DNA"
path = "example_data/NEIME_2019/sequences"

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


def test_manifest_from_path_like_has_assays(manifest_contents: str) -> None:
    """The manifest optionally has assays. See if they are loaded correctly."""
    manifest = Manifest.from_path(io.StringIO(manifest_contents))
    assert len(manifest.assays) == 1, "Expecting one assay"


def test_manifest_version() -> None:
    """The manifest version should support comparisions."""
    manifest_v1 = Manifest(name="test", version="1.0.0")
    manifest_v2 = Manifest(name="test", version="2.0.0")

    assert manifest_v1.version == manifest_v1.version
    assert manifest_v1.version <= manifest_v1.version
    assert manifest_v1.version >= manifest_v1.version

    assert manifest_v1.version != manifest_v2.version
    assert manifest_v1.version < manifest_v2.version
    assert manifest_v2.version > manifest_v1.version
    assert manifest_v1.version <= manifest_v2.version
    assert manifest_v2.version >= manifest_v1.version


def test_manifest_dump_creates_file_with_content(tmp_path: Path) -> None:
    """The manifest dump should create a file with content."""
    manifest = Manifest(name="test")
    path = tmp_path / "manifest.toml"

    manifest.dump(path)

    assert path.exists(), "Dumped manifest file does not exist."
    assert path.stat().st_size > 0, "Dumped manifest file is empty."


def test_manifest_dump_from_path_unit(tmp_path: Path) -> None:
    """The manifest dump creates a file that can be loaded back with same content."""
    manifest = Manifest(name="test")
    path = tmp_path / "manifest.toml"

    manifest.dump(path)

    try:
        loaded_manifest = Manifest.from_path(path)
    except ValidationError as e:
        raise AssertionError(
            f"Loading manifest failed:``` toml\n{path.read_text()}```"
        ) from e
    else:
        assert loaded_manifest == manifest, (
            f"Loaded manifest does not match dumped manifest: {path.read_text()}"
        )


def test_manifest_dump_from_path_unit_docs_example(
    tmp_path: Path, manifest_path: Path
) -> None:
    """The manifest dump creates a file that can be loaded back with same content.

    Use the example from the documentation for more complicated manifest.
    """
    manifest = Manifest.from_path(manifest_path)
    path = tmp_path / "manifest.toml"
    manifest.dump(path)
    loaded_manifest = Manifest.from_path(path)
    try:
        loaded_manifest = Manifest.from_path(path)
    except ValidationError as e:
        raise AssertionError(
            f"Loading manifest failed:``` toml\n{path.read_text()}```"
        ) from e
    else:
        assert loaded_manifest == manifest, (
            f"Loaded manifest does not match dumped manifest: {path.read_text()}"
        )


def test_manifest_dump_version_string(tmp_path: Path) -> None:
    """The version should be dumped as a string."""
    manifest = Manifest(name="test", version="1.0.0")
    path = tmp_path / "manifest.toml"

    manifest.dump(path)

    assert 'version = "1.0.0"' in path.read_text()


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

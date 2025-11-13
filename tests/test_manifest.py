import io
from pathlib import Path

import pytest
from pydantic import ValidationError

from proteingym.base.manifest import Manifest


@pytest.fixture
def manifest_contents() -> str:
    return """
version = "1.0.0"
name = "Example Dataset"
description = "This is an example dataset for demonstration purposes."

[[ assay_variables ]]
name = "PH"
description = "pH level of the samples"
unit = "pH"

[[ assay_targets ]]
name = "DMS Score"
description = "DMS score of the samples"
unit = "log fold change"

[[ assay_targets ]]
name = "DMS Score Bin"
description = "DMS score bin of the samples"

[[ assays ]]
name = "assay"
path = "assay.csv"
sequence = "sequence"
sequence_alphabet = "AA"

[ assays.targets ]
"DMS Score" = "DMS_score"
"DMS Score Bin" = "DMS_score_bin"

[ assays.variables ]
PH = "7"

[[ sequences ]]
type = "wild_type"
alphabet = "DNA"
path = "sequences.fasta"

[[ structures ]]
path = "structures.pdb"

[[ msas ]]
path = "msas.a3m"
format = "fasta"
num_significant = 10
bit_score = 0.5
theta = 0.8
reference_sequence = "abc"
sequence_start = 1
sequence_end = 10
weights = [0.1, 0.2, 0.3]  # Can also be loaded from `weights_path`
"""


@pytest.fixture
def manifest_path(tmp_path: Path, manifest_contents: str) -> Path:
    """A (temporary) manifest file."""
    # Mock files need to exist for the manifest validation to pass
    sequence_file = tmp_path / "sequences.fasta"
    structure_file = tmp_path / "structures.pdb"
    msa_file = tmp_path / "msas.a3m"
    msa_weights_file = tmp_path / "weights.npy"
    assay_file = tmp_path / "assay.csv"
    for path in sequence_file, structure_file, msa_file, msa_weights_file, assay_file:
        path.touch()
    # Write header in the assay file
    assay_file.write_text("sequence,DMS_score,DMS_score_bin\n")
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
    documentation_file_path = Path(__file__).parent.parent / Path("docs/manifest.md")
    documentation_contents = documentation_file_path.read_text(encoding="utf-8")

    assert documentation_file_path.exists(), (
        f"Documentation file does not exist: {documentation_file_path}"
    )
    assert manifest_contents in documentation_contents, (
        "Test manifest contents not found in documentation."
    )


def test_manifest_from_path_like_minimal_contents() -> None:
    """The manifest requires only a name at minimum."""
    manifest_contents_minimal = io.StringIO("version = '1.0.0'\nname = 'dataset'")

    try:
        Manifest.from_path(manifest_contents_minimal)
    except ValidationError as e:
        raise AssertionError("ValidationError raised") from e
    else:
        assert True, "Manifest loaded successfully from path-like object."


def test_manifest_from_path_like_requires_version_field() -> None:
    """The manifest version is a required field."""
    manifest_contents_without_version = io.StringIO("name = 'dataset'")

    with pytest.raises(
        ValidationError,
        match="validation error for Manifest\nversion\n  Field required",
    ):
        Manifest.from_path(manifest_contents_without_version)


def test_manifest_from_path_like_requires_name_field() -> None:
    """The manifest name is a required field."""
    manifest_contents_without_name = io.StringIO(
        "version = '1.0.0'\ndescription = 'example description'"
    )

    with pytest.raises(
        ValidationError, match="validation error for Manifest\nname\n  Field required"
    ):
        Manifest.from_path(manifest_contents_without_name)


def test_manifest_from_path_like_requires_name_field_with_non_zero_length() -> None:
    """The manifest name is required to have non-zero length."""
    manifest_contents_without_name = io.StringIO("version = '1.0.0'\nname = ''")

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

    match = r".* Value error, 2023-10-05 is not valid SemVer string .*"
    with pytest.raises(ValidationError, match=match):
        Manifest.from_path(manifest_contents_with_date_version)


def test_manifest_from_path(manifest_path: Path) -> None:
    """Happy flow for loading a Manifest from a file path."""
    try:
        Manifest.from_path(manifest_path)
    except ValidationError as e:
        raise ValidationError(f"ValidationError raised {e}") from e
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


@pytest.mark.parametrize(
    "protein_data_attribute", ["assays", "sequences", "structures", "msas"]
)
def test_manifest_from_path_has_protein_data(
    manifest_path: Path, protein_data_attribute: str
) -> None:
    """The manifest optionally has protein data. See if they are loaded correctly."""
    manifest = Manifest.from_path(manifest_path)
    assert len(getattr(manifest, protein_data_attribute)) == 1, (
        f"Expecting one {protein_data_attribute}"
    )


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
    manifest = Manifest(version="1.0.0", name="test")

    path = manifest.dump(path=tmp_path)

    assert path.exists(), "Dumped manifest file does not exist."
    assert path.stat().st_size > 0, "Dumped manifest file is empty."


def test_manifest_dump_from_path_unit(tmp_path: Path) -> None:
    """The manifest dump creates a file that can be loaded back with same content."""
    manifest = Manifest(version="1.0.0", name="test")

    path = manifest.dump(path=tmp_path)

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
    manifest.dump(path=path)
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

    path = manifest.dump(path=tmp_path)

    assert 'version = "1.0.0"' in path.read_text()


@pytest.mark.parametrize(
    "relative_path", ["sequences.fasta", "structures.pdb", "msas.a3m"]
)
def test_manifest_dump_relative_path(
    tmp_path: Path, manifest_path: Path, relative_path: str
) -> None:
    """The protein data path should be dumped as relative paths."""
    manifest = Manifest.from_path(manifest_path)

    path = manifest.dump(path=tmp_path)

    assert f'path = "{relative_path}"' in path.read_text()

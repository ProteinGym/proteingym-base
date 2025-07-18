from pathlib import Path
from typing import IO, Annotated, Dict, List

import toml
from packaging.version import Version as PackagingVersion
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from pg2_dataset.models.constants import DirType
from pg2_dataset.models.getter import DataDir
from pg2_dataset.repositories.sequence import Sequence, SequenceFactory
from pg2_dataset.settings import datasets_dir


class _Version(BaseModel):
    """A version class to represent semantic versions.

    Could not reuse `packaging.version.Version` directly without loosing
    serializaiton as Pydantic requires a dataclass or Pydantic model for that.

    Docs:
        See https://packaging.pypa.io/en/stable/version.html#packaging.version.Version
    """

    major: int
    minor: int
    micro: int = 0

    @classmethod
    def from_string(cls, version_string: str) -> "_Version":
        """Initialize Version from a string in the format 'major.minor[.patch]'."""
        version = PackagingVersion(version_string)
        return cls(
            major=version.major,
            minor=version.minor,
            micro=version.micro,
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.micro}"

    def __eq__(self, other: "_Version") -> bool:
        return PackagingVersion(str(self)) == PackagingVersion(str(other))

    def __ne__(self, other: "_Version") -> bool:
        return PackagingVersion(str(self)) != PackagingVersion(str(other))

    def __lt__(self, other: "_Version") -> bool:
        return PackagingVersion(str(self)) < PackagingVersion(str(other))

    def __le__(self, other: "_Version") -> bool:
        return PackagingVersion(str(self)) <= PackagingVersion(str(other))

    def __gt__(self, other: "_Version") -> bool:
        return PackagingVersion(str(self)) > PackagingVersion(str(other))

    def __ge__(self, other: "_Version") -> bool:
        return PackagingVersion(str(self)) >= PackagingVersion(str(other))


def _try_coerce_version(version: _Version | str) -> _Version:
    """Try to coercea a Version object."""
    if isinstance(version, str):
        return _Version.from_string(version)
    return version


class Manifest(BaseModel):
    """Dataset manifest representing a dataset's metadata and resources.

    A programmatic representation of a dataset's manifest used for validation
    and loading data. The fields have Python built-in data types, the Protein
    Gym data types are constructed while loading the dataset.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    version: Annotated[_Version, BeforeValidator(_try_coerce_version)] = _Version(
        major=1, minor=0
    )
    """The version of the manifest schema.

    The version follows the semantic version format: `<major>.<minor>`. A major
    version change indicates breaking changes, while a minor version change
    indicates backward-compatible additions or changes.
    """

    name: str
    """The name of the dataset."""

    description: str | None = None
    """A brief description of the dataset."""

    assay_conditions: list[dict[str, str]] = Field(default_factory=dict)
    """The conditions for the assays defined in the dataset."""

    assays: list[dict[str, str]] = Field(default_factory=list)
    """The assays included in the dataset."""

    sequences: list[dict[str, str]] = Field(default_factory=list)
    """The sequences included in the dataset."""

    structures: list[dict[str, str]] = Field(default_factory=list)
    """The structures included in the dataset."""

    msas: list[dict[str, str]] = Field(default_factory=list)
    """The multiple sequence alignments included in the dataset."""

    @classmethod
    def from_path(cls, path: Path | IO["str"]) -> "Manifest":
        """Create a Manifest instance from a TOML file or string."""
        return cls(**toml.load(path))

    def dump(self, path: Path) -> None:
        """Dump the manifest to a TOML file."""
        with path.open("w") as f:
            toml.dump(self.model_dump(exclude_defaults=True), f)


def assert_non_empty_sequence_list(v: List[Sequence]) -> List[Sequence]:
    if len(v) == 0:
        raise ValueError("At least one sequence is required.")
    return v


class Dataset(BaseModel):
    name: str
    description: str
    version: str
    sequences: Annotated[
        List[Sequence],
        lambda v: assert_non_empty_sequence_list(v),
    ]
    creator: str = None
    metadata: Dict[str, str] = None
    manifest: Manifest = None

    @classmethod
    def from_manifest(cls, manifest: Manifest) -> "Dataset":
        sequences = []
        for sequence_manifest in manifest.sequences:
            sequence_factory = SequenceFactory.from_manifest(manifest=sequence_manifest)
            sequences = sequences + sequence_factory.generate_sequences()

        return cls(
            name=manifest.name,
            description=manifest.description,
            version=manifest.version,
            creator=manifest.creator,
            metadata=manifest.metadata,
            sequences=sequences,
            manifest=manifest,
        )

    def dump(self, path: Path = None):
        if path is None:
            path = datasets_dir / self.name
        path.mkdir(parents=True, exist_ok=True)

        # Write sequences
        sequence_dir = DataDir(
            path=path / "sequences",
            dir_type=DirType.LOCAL,
        ).dump()
        for sequence in self.sequences:
            sequence.dump(sequence_dir)

        # Write manifest
        manifest_path = path / "manifest.toml"
        self.manifest.dump(manifest_path)

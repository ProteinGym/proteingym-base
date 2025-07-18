from pathlib import Path
from typing import IO, Annotated, Dict, List

import toml
from packaging.version import Version as PackagingVersion
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_serializer, AfterValidator


from pg2_dataset.models.constants import DirType
from pg2_dataset.models.getter import DataDir
from pg2_dataset.repositories.sequence import Sequence, SequenceFactory
from pg2_dataset.settings import datasets_dir
from pg2_dataset.utils import zip_context


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

    @field_serializer("version")
    def serialize_version(self, version: _Version) -> str:
        """Serialize the version to a string."""
        return str(version)

    def dump(self, path: Path) -> None:
        """Dump the manifest to a TOML file."""
        # Empty or None values indicate the fields were not set, hence excluded
        # them from the dump.
        include = {key for key, value in self.model_dump().items() if value}
        with path.open("w", encoding="utf-8") as f:
            toml.dump(self.model_dump(include=include), f)


def assert_non_empty_sequence_list(v: List[Sequence]) -> List[Sequence]:
    """Ensure that the list of sequences is not empty."""
    if len(v) == 0:
        raise ValueError("At least one sequence is required.")
    return v


class Dataset(BaseModel):
    """A Dataset class representing a PG2 Dataset consisting of sequences, structures,
    msas, and assays. This is the main entry point for loading the datasets in PG2.
    """

    name: str
    """The name of the dataset."""
    description: str
    """A brief description of the dataset."""
    version: str
    """ToDo: Add a version class to represent semantic versions."""
    sequences: Annotated[
        List[Sequence],
        AfterValidator(lambda v: assert_non_empty_sequence_list(v)),
    ]
    """The list of sequences present in the dataset."""
    creator: str = None
    """The creator of the dataset, for eg, a person or an organization."""
    metadata: Dict[str, str] = None
    manifest: Manifest = None

    @classmethod
    def from_manifest(cls, manifest: Manifest) -> "Dataset":
        """Class Method to create a Dataset from a DatasetManifest instance.
        The manifest contains the information about the dataset, including sequences,
        structures, msas, and assays details. The sequences are generated
        using the SequenceFactory based on the manifest.
        Args:
            manifest (DatasetManifest): The manifest to create the dataset from.
        Returns:
            Dataset: The dataset created from the manifest.
        """
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

    @classmethod
    def from_manifest_toml(cls, path: str | Path) -> "Dataset":
        """Class Method to create a Dataset from a manifest TOML file.
        and returns a Dataset instance.
        Args:
            path (str | Path): The path to the manifest TOML file.
        Returns:
            Dataset: The dataset created from the manifest.
        """
        if isinstance(path, str):
            path = Path(path)
        dataset_manifest = Manifest.from_toml(path)
        return cls.from_manifest(dataset_manifest)

    @classmethod
    def from_zip(cls, path: str | Path) -> "Dataset":
        """Class Method to create a Dataset from a ZIP archive containing a manifest.
        The ZIP archive should contain a single manifest file in TOML format.
        Args:
            path (str | Path): The path to the ZIP archive.
        Returns:
            Dataset: The dataset created from the manifest in the ZIP archive.
        Raises:
            ValueError: If multiple manifest files are found in the ZIP archive.
            FileNotFoundError: If no manifest file is found in the ZIP archive.
        """
        # The zip_context context manager is used to extract the contents of the zip,
        # load the dataset, and clean up the extracted contents.
        with zip_context(path) as zip_contents:
            manifest_files = [name for name in zip_contents if name.suffix == ".toml"]
            if len(manifest_files) > 1:
                raise ValueError(
                    f"Multiple manifest .toml files found in the \
                        ZIP archive: {manifest_files}"
                )
            elif not manifest_files:
                raise FileNotFoundError(
                    f"No manifest .toml found in the ZIP archive at {path}"
                )
            else:
                manifest_file = manifest_files[0]

            dataset_manifest = DatasetManifest.from_toml(manifest_file)
            return cls.from_manifest(dataset_manifest)

    def dump(self, path: str | Path = None):
        """Dump the dataset to a specified path or directory.
        If the path is not specified, it defaults to the dataset's name in the
        datasets directory.
        Args:
            path (str | Path, optional): The path to dump the dataset. Defaults to None.
        Returns:
            None
        Outputs:
            - A directory containing the sequences dir and a manifest file.
            - A subdirectory named "sequences" containing the sequence files.
            - Sequence files are dumped in the format defined by the Sequence class.
        """
        if isinstance(path, str):
            path = Path(path)
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

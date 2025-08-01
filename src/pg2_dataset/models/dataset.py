from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, Annotated, Any, Callable
from zipfile import ZipFile

import toml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    field_serializer,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from semver import Version

from pg2_dataset.models.msa import MSA, MSAManifestSection
from pg2_dataset.models.sequence import Sequence, SequenceManifestSection
from pg2_dataset.models.structure import Structure, StructureManifestSection
from pg2_dataset.utils import zip_context


class _VersionPydanticAnnotation:
    """A version class to represent semantic versions.

    Docs:
        https://docs.pydantic.dev/latest/api/pydantic_extra_types_semantic_version/
        https://python-semver.readthedocs.io/en/latest/advanced/combine-pydantic-and-semver.html
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        """See https://docs.pydantic.dev/latest/concepts/types/#customizing-validation-with-__get_pydantic_core_schema__"""
        _ = source_type
        _ = handler

        def validate_from_str(value: str) -> Version:
            return Version.parse(value)

        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(Version),
                    from_str_schema,
                ]
            ),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """See https://docs.pydantic.dev/latest/concepts/json_schema/#implementing-__get_pydantic_json_schema__"""
        _ = core_schema
        return handler(core_schema.str_schema())


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

    version: Annotated[Version, _VersionPydanticAnnotation] = Version(1, 0)
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

    sequences: list[SequenceManifestSection] = Field(default_factory=list)
    """The sequences included in the dataset."""

    structures: list[StructureManifestSection] = Field(default_factory=list)
    """The structures included in the dataset."""

    msas: list[MSAManifestSection] = Field(default_factory=list)
    """The multiple sequence alignments included in the dataset."""

    @classmethod
    def from_path(cls, path: Path | IO["str"]) -> "Manifest":
        """Create a Manifest instance from a TOML file or string."""
        return cls(**toml.load(path))

    @field_serializer("version")
    def serialize_version(self, version: Version) -> str:
        """Serialize the version to a string."""
        return str(version)

    def dump(self, *, path: Path | None = None) -> Path:
        """Dump the manifest to a TOML file.

        Args:
            path (Path | None): The path to dump the manifest to. If
                None, the current working directory is used as path. If path is
                a directory, the manifest name is used as file name. Defaults to
                None.

        Returns:
            Path: The path to the dumped manifest file.
        """
        path = path or Path.cwd()
        if path.is_dir():
            path = path / f"{self.name}.toml"
        # Empty or None values indicate the fields were not set, hence excluded
        # them from the dump.
        include = {key for key, value in self.model_dump().items() if value}
        with path.open("w", encoding="utf-8") as f:
            toml.dump(self.model_dump(include=include), f)
        return path


class DatasetArchiveLayout:
    """The layout of the dataset archive."""

    MANIFEST_FILE = "manifest.lock"
    """The internal manifest file inside the dataset archive."""

    SEQUENCES_DIRECTORY = "sequences/"
    """The directory for sequences."""

    STRUCTURES_DIRECTORY = "structures/"
    """The directory for structures."""


class Dataset(BaseModel):
    """A Protein Gym dataset.

    The dataset provides access to metadata and protein data such as assays,
    sequences, structures, and multiple sequence alignments (MSAs).
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The name of the dataset."""

    description: str | None = None
    """A brief description of the dataset."""

    sequences: list[Sequence] = Field(default_factory=list)
    """The sequences included in the dataset."""

    structures: list[Structure] = Field(default_factory=list)
    """The structures included in the dataset."""

    msas: list[MSA] = Field(default_factory=list)
    """The multiple sequence alignments included in the dataset."""

    @classmethod
    def from_manifest(cls, manifest: Manifest) -> "Dataset":
        """Create a `Dataset` from a `Manifest` instance.

        The manifest contains the information about the dataset, including sequences,
        structures, msas, and assays details.

        Args:
            manifest (DatasetManifest): The manifest to create the dataset from.

        Returns:
            Dataset: The dataset created from the manifest.
        """
        sequences = [
            seq
            for manifest_section in manifest.sequences
            for seq in Sequence.from_manifest_section(manifest_section)
        ]

        structures = [Structure.from_manifest_section(s) for s in manifest.structures]

        msas = [MSA.from_manifest_section(m) for m in manifest.msas]

        return cls(
            name=manifest.name,
            description=manifest.description,
            sequences=sequences,
            structures=structures,
            msas=msas,
        )

    @classmethod
    def from_path(cls, path: Path) -> "Dataset":
        """Create a `Dataset` from a ZIP archive.

        The zip_context context manager is used to extract the contents of the zip,
        load the dataset, and clean up the extracted contents.

        Args:
            path: The path to the ZIP archive.

        Returns:
            The dataset created from the manifest in the ZIP archive.

        Raises:
            ValueError: If multiple manifest files are found in the ZIP archive.
            FileNotFoundError: If no manifest file is found in the ZIP archive.
        """
        # The zip_context context manager is used to extract the contents of the zip,
        # load the dataset, and clean up the extracted contents.
        with zip_context(path):
            dataset_manifest = Manifest.from_toml(DatasetArchiveLayout.MANIFEST_FILE)
            return cls.from_manifest(dataset_manifest)

    def _create_manifest_sections(self, objects: list[Any], path: Path) -> list[Any]:
        """Create manifest sections for sequences and structures."""
        manifest_sections = [
            obj.as_manifest_section(path=obj.dump(path=path)) for obj in objects
        ]
        return manifest_sections

    def _create_manifest(self, path: Path) -> Manifest:
        """Create a manifest for the dataset."""
        manifest = Manifest(
            name=self.name,
            description=self.description,
            sequences=self._create_manifest_sections(self.sequences, path),
            structures=self._create_manifest_sections(self.structures, path),
        )
        return manifest

    def _write_paths_to_zip(
        self,
        zip: ZipFile,
        *paths: Path,
        arcname: str | None = None,
        arcname_prefix: str = "",
    ) -> None:
        """Write paths to a ZIP archive."""
        for path in paths:
            arcname = arcname_prefix + (arcname or path.name)
            zip.write(path, arcname=arcname)

    def _create_archive(self, path: Path, *, temporary_directory: Path) -> Path:
        """Create a ZIP archive of the dataset."""
        archive_path = path / f"{self.name}.zip"
        manifest = self._create_manifest(temporary_directory)
        manifest_path = manifest.dump(path=temporary_directory)
        with ZipFile(archive_path, "w") as zip:
            self._write_paths_to_zip(
                zip, manifest_path, arcname=DatasetArchiveLayout.MANIFEST_FILE
            )
            self._write_paths_to_zip(
                zip,
                *[sequence.path for sequence in manifest.sequences],
                arcname_prefix=DatasetArchiveLayout.SEQUENCES_DIRECTORY,
            )
            self._write_paths_to_zip(
                zip,
                *[structure.path for structure in manifest.structures],
                arcname_prefix=DatasetArchiveLayout.STRUCTURES_DIRECTORY,
            )
        return archive_path

    def dump(self, *, path: Path | None = None) -> Path:
        """Dump the dataset.

        Args:
            path (Path | None): The path to dump the dataset in. If None, the
                current working directory is used. Defaults to None.

        Returns:
            Path: The path to the dumped dataset archive.
        """
        path = path or Path.cwd()
        # While we prefer to avoid IO to disk, TemporaryDirectory is used for
        # convenience because it unifies the `:method:dump` signatures to write
        # to a directory.
        with TemporaryDirectory() as temp_dir:
            # TemporaryDirectory returns a string, we prefer a Path object.
            temp_dir = Path(temp_dir)
            archive_path = self._create_archive(path, temporary_directory=temp_dir)
        return archive_path

import collections
import itertools
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from pg2_dataset.assay import Assay, AssayCondition
from pg2_dataset.manifest import MANIFEST_LATEST_VERSION, Manifest
from pg2_dataset.msa import MSA
from pg2_dataset.sequence import Sequence
from pg2_dataset.structure import Structure


class DatasetArchiveLayout:
    """The layout of the dataset archive."""

    MANIFEST_FILE = Path("manifest.lock")
    """The internal manifest file inside the dataset archive."""

    ASSAYS_DIRECTORY = Path("assays/")
    """The directory for assays."""

    SEQUENCES_DIRECTORY = Path("sequences/")
    """The directory for sequences."""

    STRUCTURES_DIRECTORY = Path("structures/")
    """The directory for structures."""

    MSAS_DIRECTORY = Path("msas/")
    """The directory for multiple sequence alignments (MSAs)."""


class Dataset(BaseModel):
    """A Protein Gym dataset.

    The dataset provides access to metadata and protein data such as assays,
    sequences, structures, and multiple sequence alignments (MSAs).

    In this BaseModel, we only use Pydantic validation feature only, not the
    (de)serialization feature because protein data is not persisted as mappings
    (dictionaries).
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Required for protein data types
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

    assay_conditions: list[AssayCondition] = Field(default_factory=list)
    """The list of assay conditions relevant to the dataset."""

    assays: list[Assay] = Field(default_factory=list)
    """The assays present in the dataset."""

    sequences: list[Sequence] = Field(default_factory=list)
    """The sequences included in the dataset."""

    structures: list[Structure] = Field(default_factory=list)
    """The structures included in the dataset."""

    msas: list[MSA] = Field(default_factory=list)
    """The multiple sequence alignments included in the dataset."""

    @model_validator(mode="after")
    def _validate_unique_names(self) -> "Dataset":
        """Ensure that the names are unique within each data type.

        Checks each data type (assays, sequences, structures, msas) to ensure
        that the names are unique. Raises error if duplicates are found.

        Returns:
            Dataset: The validated dataset instance.

        Raises:
            ValueError: If duplicate names are found in any of the data types.
        """

        def _get_duplicate_names(items: list[BaseModel]) -> list[str]:
            """Get duplicate names from a list of items."""
            name_counts = collections.Counter(item.name for item in items if item.name)
            return [name for name, count in name_counts.items() if count > 1]

        data_types = {
            Assay: self.assays,
            Sequence: self.sequences,
            Structure: self.structures,
            MSA: self.msas,
        }

        duplicates = {
            data_class: _get_duplicate_names(items)
            for data_class, items in data_types.items()
        }

        if any(duplicates.values()):
            error_lines = [
                f"{data_class.__name__}s: {', '.join(names)}"
                for data_class, names in duplicates.items()
                if names
            ]
            raise ValueError(f"Duplicate names found in: {'\n'.join(error_lines)}")
        return self

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
        assays = [Assay.from_manifest_section(a) for a in manifest.assays]
        sequences = itertools.chain(
            *[Sequence.from_manifest_section(s) for s in manifest.sequences]
        )
        structures = [Structure.from_manifest_section(s) for s in manifest.structures]
        msas = [MSA.from_manifest_section(m) for m in manifest.msas]
        return cls(
            name=manifest.name,
            description=manifest.description,
            assay_conditions=manifest.assay_conditions,
            assays=assays,
            sequences=sequences,
            structures=structures,
            msas=msas,
        )

    @classmethod
    def from_path(cls, path: Path) -> "Dataset":
        """Create a `Dataset` from a ZIP archive.

        Extract the contents to a temporary directory and load the dataset
        from the manifest file.

        Args:
            path: The path to the ZIP archive.

        Returns:
            The dataset created from the manifest in the ZIP archive.

        Raises:
            ValueError: If multiple manifest files are found in the ZIP archive.
            FileNotFoundError: If no manifest file is found in the ZIP archive.
        """
        # While a SE practice is to avoid IO to disk where possible,
        # we use a temporary directory here to extract the dataset archive as
        # Pydantic expects the file path to exist, while still hiding the IO
        # from the users.
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with ZipFile(path, "r") as zip_file:
                zip_file.extractall(temp_path)
            dataset_manifest = Manifest.from_path(
                temp_path / DatasetArchiveLayout.MANIFEST_FILE
            )
            return cls.from_manifest(dataset_manifest)

    def _dump_data(self, temporary_directory: Path) -> dict[type, list[Path]]:
        """Dump the data into the directory.

        See :class:DatasetArchiveLayout for the archive layout.

        Returns:
            dict[type, list[Path]]: A dictionary mapping the data type -
                Sequence, Structure and MSA - to the list of paths to the dumped
                data.
        """
        data_paths = collections.defaultdict(list)
        for type_, subdirectory, objects in (
            (Assay, DatasetArchiveLayout.ASSAYS_DIRECTORY, self.assays),
            (Sequence, DatasetArchiveLayout.SEQUENCES_DIRECTORY, self.sequences),
            (Structure, DatasetArchiveLayout.STRUCTURES_DIRECTORY, self.structures),
            (MSA, DatasetArchiveLayout.MSAS_DIRECTORY, self.msas),
        ):
            subpath = temporary_directory / subdirectory
            subpath.mkdir()
            for obj in objects:
                data_path = obj.dump(path=subpath)
                data_paths[type_].append(data_path)
        return data_paths

    def _create_manifest(self, data_paths: dict[type, list[Path]]) -> Manifest:
        """Create a manifest for the dataset.

        The manifest contains the metadata and sections for each data type.

        Args:
            data_paths (dict[type, list[Path]]): A dictionary mapping the data
                type - Sequence, Structure and MSA - to the list of paths to the
                dumped data.
        """
        manifest = Manifest(
            version=MANIFEST_LATEST_VERSION,
            name=self.name,
            description=self.description,
            assay_conditions=self.assay_conditions,
            assays=[
                a.as_manifest_section(path=path)
                for a, path in zip(self.assays, data_paths.get(Assay, []), strict=True)
            ],
            sequences=[
                s.as_manifest_section(path=path)
                for s, path in zip(
                    self.sequences, data_paths.get(Sequence, []), strict=True
                )
            ],
            structures=[
                s.as_manifest_section(path=path)
                for s, path in zip(
                    self.structures, data_paths.get(Structure, []), strict=True
                )
            ],
            msas=[
                m.as_manifest_section(path=path)
                for m, path in zip(self.msas, data_paths.get(MSA, []), strict=True)
            ],
        )
        return manifest

    def _write_paths_to_zip(
        self,
        zip: ZipFile,
        *paths: Path,
        arcname: Path | None = None,
        arcname_prefix: Path = Path(),
    ) -> None:
        """Write paths to a ZIP archive."""
        assert arcname is None or len(paths) <= 1, (
            "Cannot have multiple paths with an arcname, "
            "because it creates a name collision"
        )
        for path in paths:
            zip.write(path, arcname=arcname_prefix / (arcname or path.name))

    def _create_archive(self, path: Path, *, temporary_directory: Path) -> Path:
        """Create a ZIP archive of the dataset."""
        archive_path = path / f"{self.name}.zip"
        # The manifest Pydantic base model checks if the data path exists,
        # hence, we dump the data before creating and dumping the Manifest
        data_paths = self._dump_data(temporary_directory)
        manifest = self._create_manifest(data_paths)
        manifest_path = manifest.dump(path=temporary_directory)
        with ZipFile(archive_path, "w") as zip:
            self._write_paths_to_zip(
                zip, manifest_path, arcname=DatasetArchiveLayout.MANIFEST_FILE
            )
            self._write_paths_to_zip(
                zip,
                *[assay.path for assay in manifest.assays],
                arcname_prefix=DatasetArchiveLayout.ASSAYS_DIRECTORY,
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
            self._write_paths_to_zip(
                zip,
                *[msa.path for msa in manifest.msas],
                arcname_prefix=DatasetArchiveLayout.MSAS_DIRECTORY,
            )
        return archive_path

    def dump(self, *, path: Path | str | None = None) -> Path:
        """Dump the dataset.

        Args:
            path (Path | str | None): The path to dump the dataset in. If None,
                the current working directory is used. Defaults to None.

        Returns:
            Path: The path to the dumped dataset archive.
        """
        if isinstance(path, str):  # User-friendly interface to support str
            path = Path(path)
        path = path or Path.cwd()
        # While a SE practice is to avoid IO to disk where possible,
        # we use a temporary directory here to extract the dataset archive as
        # Pydantic expects the file path to exist, while still hiding the IO
        # from the users.
        with TemporaryDirectory() as temp_dir:
            archive_path = self._create_archive(
                path, temporary_directory=Path(temp_dir)
            )
        return archive_path

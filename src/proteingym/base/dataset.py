import collections
import dataclasses
import itertools
import json
from collections.abc import Collection
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator
from zipfile import ZipFile

import polars as pl
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from .assay import Assay, AssayTarget, AssayVariable
from .manifest import MANIFEST_LATEST_VERSION, Manifest
from .msa import MSA
from .sequence import Sequence
from .structure import Structure


class DatasetArchiveLayout:
    """The layout of the dataset archive."""

    SUFFIX = ".pgdata"
    """The suffix of the dataset archive."""

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


@dataclasses.dataclass(kw_only=True, frozen=True)
class DatasetSlice:
    """A slice of a dataset.

    A slice gets ("slices") a subset of dataset. Currently, a slice only covers
    a subset of assays.

    This class functions as a (small) protocol to be extended if we include more
    attributes in a dataset slice. Currently, it is a wrapper around a list of
    assay slices.
    """

    assays: list[list[bool]] = dataclasses.field(default_factory=list)
    """The list of assay slices as boolean masks."""

    @classmethod
    def from_json(cls, contents: str) -> "DatasetSlice":
        """Create a dataset slice from a JSON string.

        Args:
            contents (str): The JSON string to create the dataset slice from.

        Returns:
            The dataset slice created from the JSON string.
        """
        return cls(**json.loads(contents))

    def to_json(self) -> str:
        """Convert the dataset slice to a JSON string.

        Returns:
            A JSON string representation of the dataset slice.
        """
        return json.dumps(dataclasses.asdict(self))

    @classmethod
    def from_json(cls, contents: str) -> "DatasetSlice":
        """Create a dataset slice from a JSON string.

        Args:
            contents: The JSON string to create the dataset slice from.

        Returns:
            The dataset slice created from the JSON string.
        """

        def is_integer(value: Any) -> bool:
            return isinstance(value, int) and not isinstance(value, bool)

        def is_slice_iterable(iterable: Iterable) -> bool:
            return any(is_integer(el) or el is None for el in iterable)

        def as_dataset_slice(raw: dict) -> DatasetSlice:
            assay_slices = []
            for slices in raw.get("assays", []):
                if is_slice_iterable(slices):
                    assay_slices.append(slice(*slices))
                else:
                    assay_slices.append(slices)
            return cls(assays=assay_slices)

        instance = json.loads(contents, object_hook=as_dataset_slice)
        return instance

    def to_json(self) -> str:
        """Convert the dataset slice to a JSON string.

        Returns:
            A JSON string representation of the dataset slice.
        """

        def encode_slice(slc: slice) -> tuple[int | None, int | None, int | None]:
            """Encode a slice object as a tuple."""
            return (slc.start, slc.stop, slc.step)

        def encode(dataset_slice: DatasetSlice) -> dict:
            """Encode a DatasetSlice as a dictionary."""
            slices = [
                encode_slice(s) if isinstance(s, slice) else s
                for s in dataset_slice.assays
            ]
            return {"assays": slices}

        return json.dumps(self, default=encode)


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

    assay_variables: list[AssayVariable] = Field(default_factory=list)
    """The list of assay variables relevant to the dataset."""

    assay_targets: list[AssayTarget] = Field(default_factory=list)
    """The list of assay targets relevant to the dataset."""

    assays: list[Assay] = Field(default_factory=list)
    """The assays present in the dataset."""

    sequences: list[Sequence] = Field(default_factory=list)
    """The sequences included in the dataset."""

    structures: list[Structure] = Field(default_factory=list)
    """The structures included in the dataset."""

    msas: list[MSA] = Field(default_factory=list)
    """The multiple sequence alignments included in the dataset."""

    def __or__(self, other: "Dataset") -> "Dataset":
        """Implements the union operator (|) for Dataset.

        Returns a new Dataset containing the union of:
        - assays, including assay variables and targets
        - sequences
        - structures
        - msas
        """

        def list_union(left: list[Any], right: list[Any]) -> list[Any]:
            """Return the union of two lists.

            Preserving order and removing duplicates
            """
            return left + [item for item in right if item not in left]

        return Dataset(
            name=f"{self.name}_union_{other.name}",
            description=(
                f"Union of {self.name} and {other.name} datasets."
                f"\n{self.description}\n{other.description}"
            ),
            assay_variables=list_union(self.assay_variables, other.assay_variables),
            assay_targets=list_union(self.assay_targets, other.assay_targets),
            assays=list_union(self.assays, other.assays),
            sequences=list_union(self.sequences, other.sequences),
            structures=list_union(self.structures, other.structures),
            msas=list_union(self.msas, other.msas),
        )

    def __eq__(self, item: Any) -> bool:
        """Implements the equality operator (==) for Dataset."""
        if not isinstance(item, Dataset):
            return False

        def sort_by_name(
            values: list[Assay | Sequence | Structure | MSA],
        ) -> list[Assay | Sequence | Structure | MSA]:
            """Sort a list of BaseModel by name, placing unnamed items at the end."""
            return sorted(values, key=lambda value: value.name)

        is_assay_match = sort_by_name(self.assays) == sort_by_name(item.assays)
        is_sequence_match = sort_by_name(self.sequences) == sort_by_name(item.sequences)
        is_structure_match = sort_by_name(self.structures) == sort_by_name(
            item.structures
        )
        is_msa_match = sort_by_name(self.msas) == sort_by_name(item.msas)
        return (
            is_assay_match and is_sequence_match and is_structure_match and is_msa_match
        )

    def __contains__(self, item: Any) -> bool:
        """Implements the 'in' operator for Dataset."""
        if not isinstance(item, Dataset):
            return False
        # If a protein data type is empty,
        # it is a (mathematical) subset of any other
        is_assay_subset = (
            all(assay in self.assays for assay in item.assays) or len(item.assays) == 0
        )
        is_sequence_subset = (
            all(seq in self.sequences for seq in item.sequences)
            or len(item.sequences) == 0
        )
        is_structure_subset = (
            all(struct in self.structures for struct in item.structures)
            or len(item.structures) == 0
        )
        is_msa_subset = (
            all(msa in self.msas for msa in item.msas) or len(item.msas) == 0
        )
        return (
            is_assay_subset
            and is_sequence_subset
            and is_structure_subset
            and is_msa_subset
        )

    def __getitem__(self, item: DatasetSlice) -> "Dataset":
        """Get a slice of the dataset.

        Args:
            item (slice | DatasetSlice): The slice to get. Can be a standard
                Python slice or a DatasetSlice.

        Returns:
            Dataset: A new Dataset instance containing only the sliced data.
        """
        if not isinstance(item, DatasetSlice):
            raise TypeError(
                f"Dataset can only be sliced with a DatasetSlice, not {type(item)}"
            )
        assays = [
            assay[slc] for assay, slc in zip(self.assays, item.assays, strict=True)
        ]
        return self.model_copy(update={"assays": assays})

    def __repr__(self) -> str:
        """Return a concise string representation of the dataset."""
        lines = [f"Dataset(\n\tname='{self.name}',"]
        if self.description:
            desc = (
                self.description[:60] + "..."
                if len(self.description) > 60
                else self.description
            )
            lines.append(f"\tdescription: {desc},")
        else:
            lines.append("\tdescription: None,")
        lines.append("\tcontents:")
        lines.append(f"\t\tassays: {len(self.assays)},")
        lines.append(f"\t\tsequences: {len(self.sequences)},")
        lines.append(f"\t\tstructures: {len(self.structures)},")
        lines.append(f"\t\tmsas: {len(self.msas)},")
        lines.append(f"\t\tassay_variables: {len(self.assay_variables)},")
        lines.append(")")
        return "\n".join(lines)

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
            AssayVariable: self.assay_variables,
            AssayTarget: self.assay_targets,
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

    def model_dump_json(self, **kwargs) -> str:
        """Override to ensure JSON serialization works with Bio objects.

        Biopython objects: Seq, Structure, MultipleSeqAlignment,
        don't have custom JSONEncoder, thus we rely on their __str__ method
        to return a string representation in order for
        Bio objects to be sereializable.

        See https://github.com/biopython/biopython/blob/master/Bio/Seq.py#L408.
        """

        data = self.model_dump(**kwargs)
        # Converts any non-serializable objects to their string representation.
        return json.dumps(data, default=str)

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
            assay_variables=manifest.assay_variables,
            assay_targets=manifest.assay_targets,
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
            assay_targets=self.assay_targets,
            assay_variables=self.assay_variables,
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
        archive_path = path / f"{self.name}{DatasetArchiveLayout.SUFFIX}"
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

    def to_df(
        self,
        *,
        target_names: Collection[str] | str | None = None,
    ) -> pl.DataFrame:
        """Returns the dataset assay records as a Polars DataFrame.

        Args:
            target_names (Collection[str] | str | None): The target name(s) to include.
                If None, all target names are included. Defaults to None.

        Returns:
            pl.DataFrame: The DataFrame containing all records from all assays.
        """

        if isinstance(target_names, str):
            target_names = {target_names}
        if target_names:
            if not all(
                target_name in [t.name for t in self.assay_targets]
                for target_name in target_names
            ):
                raise ValueError("Target names must be valid assay target names.")
        else:
            target_names = {t.name for t in self.assay_targets}

        if not self.assays:
            return pl.DataFrame()
        variable_names = [v.name for v in self.assay_variables]

        assays_dfs = []
        for assay in self.assays:
            df = assay.to_df(target_names=target_names)
            # Add the missing columns from target names and variable names
            missing_targets = [
                pl.lit(None).alias(target_name)
                for target_name in target_names
                if target_name not in df.columns
            ]
            df = df.with_columns(missing_targets)

            missing_variables = [
                pl.lit(None).alias(var_name)
                for var_name in variable_names
                if var_name not in df.columns
            ]
            df = df.with_columns(missing_variables)

            assays_dfs.append(
                df.select(["sequence"] + variable_names + list(target_names))
            )

        df = pl.concat(assays_dfs, how="vertical_relaxed").filter(
            ~pl.all_horizontal([pl.col(t).is_null() for t in target_names])
        )

        # Group by sequence and variables, and aggregate the target by mean
        df = (
            df.group_by(["sequence"] + variable_names)
            .agg([pl.col(t).mean().alias(t) for t in target_names])
            .sort(["sequence"] + variable_names)
        )

        return df


class SubsetsArchiveLayout:
    """The layout of a subsets archive."""

    SUFFIX = f".splits{DatasetArchiveLayout.SUFFIX}"
    """The suffix of a subsets archive."""

    DATASET_ARCHIVE = f"dataset{DatasetArchiveLayout.SUFFIX}"
    """The directory containing the dataset."""

    SLICES_FILE = "slices.json"
    """The file containing the slices."""


@dataclasses.dataclass(kw_only=True, frozen=True)
class Subsets:
    """A collection of dataset subsets (slices).

    References:
    ../../docs/decisions/0007-dataset-splits.md
    """

    dataset: Dataset
    """The dataset that is sliced."""

    slices: list[DatasetSlice] = dataclasses.field(default_factory=list)
    """The slices that create the collection of subsets."""

    def __len__(self) -> int:
        """The length of the subset collection."""
        return len(self.slices)

    def __iter__(self) -> Iterator[Dataset]:
        """Iterate over the slices in this subset collection."""
        for slc in self.slices:
            yield self.dataset[slc]

    @classmethod
    def from_path(cls, path: Path) -> "Subsets":
        """Create a `Subsets` from an archive.

        Extract the contents to a temporary directory and load the dataset
        from the manifest file.

        Args:
            path: The path to the subsets archive.

        Returns:
            The subsets from the archive

        Raises:
            ValueError: If multiple manifest files are found in the ZIP archive.
            FileNotFoundError: If no manifest file is found in the ZIP archive.
        """
        # While a SE practice is to avoid IO to disk where possible,
        # we use a temporary directory here as long as dataset dump requires
        # it.
        with ZipFile(path, "r") as zip, TemporaryDirectory() as temp_dir:
            dataset_archive = zip.extract(
                SubsetsArchiveLayout.DATASET_ARCHIVE, path=temp_dir
            )
            dataset = Dataset.from_path(dataset_archive)
            slices_str = json.loads(zip.read(SubsetsArchiveLayout.SLICES_FILE))
            slices = [DatasetSlice.from_json(slc) for slc in slices_str]
        return cls(dataset=dataset, slices=slices)

    def dump(self, *, path: Path | str | None = None) -> Path:
        """Dump the subsets.

        Args:
            path (Path | str | None): The path to dump the dataset in. If None,
                the current working directory is used. Defaults to None.

        Returns:
            Path: The path to the dumped dataset archive.
        """
        if isinstance(path, str):  # User-friendly interface to support str
            path = Path(path)
        path = path or Path.cwd()
        if path.is_dir():
            path = path / f"{self.dataset.name}{SubsetsArchiveLayout.SUFFIX}"
        # While a SE practice is to avoid IO to disk where possible,
        # we use a temporary directory here as long as dataset dump requires
        # it.
        with ZipFile(path, "w") as zip, TemporaryDirectory() as temp_dir:
            dataset_archive = self.dataset.dump(path=Path(temp_dir))
            zip.write(dataset_archive, arcname=SubsetsArchiveLayout.DATASET_ARCHIVE)
            slices_str = json.dumps([slc.to_json() for slc in self.slices])
            zip.writestr(SubsetsArchiveLayout.SLICES_FILE, slices_str)
        return path

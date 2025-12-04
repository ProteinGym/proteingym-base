import collections
import dataclasses
import itertools
import json
import warnings
from collections.abc import Callable, Collection
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator
from zipfile import ZipFile

import polars as pl
from Bio.Seq import Seq
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from .assay import Assay, AssayRaw, AssaySlice, AssayTarget, AssayVariable
from .manifest import MANIFEST_LATEST_VERSION, Manifest
from .msa import MSA
from .publication import Publication
from .sequence import Sequence, SequenceAlphabet, SequenceType
from .structure import Structure


class DatasetArchiveLayout:
    """The layout of the dataset archive."""

    SUFFIX = ".pgdata"
    """The suffix of the dataset archive."""

    MANIFEST_FILE = Path("manifest.lock")
    """The internal manifest file inside the dataset archive."""

    ASSAYS_DIRECTORY = Path("assays/")
    """The directory for assays."""

    ASSAYS_RAW_DIRECTORY = Path("assays_raw/")
    """The directory for raw assay data."""

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

    assays: list[AssaySlice | list[bool | str]] | None = None
    """The list of assay slices. If None, all assays are included."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetSlice":
        """Create a dataset slice from a dictionary.

        This method is useful when deserializing from JSON including the sub-objects.

        Args:
            data (dict[str, Any]): The dictionary to create the dataset slice from.

        Returns:
            The dataset slice created from the dictionary.
        """
        if data.get("assays") is None:
            assays = None
        else:
            assays = [AssaySlice(**assay) for assay in data.get("assays", [])]
        return cls(assays=assays)

    @classmethod
    def from_json(cls, contents: str) -> "DatasetSlice":
        """Create a dataset slice from a JSON string.

        Args:
            contents (str): The JSON string to create the dataset slice from.

        Returns:
            The dataset slice created from the JSON string.
        """
        data = json.loads(contents)
        return cls.from_dict(data)

    def to_json(self) -> str:
        """Convert the dataset slice to a JSON string.

        Returns:
            A JSON string representation of the dataset slice.
        """
        data = {}
        if self.assays is not None:
            data["assays"] = [dataclasses.asdict(slc) for slc in self.assays]
        return json.dumps(data)


class Dataset(BaseModel):
    """A Protein Gym dataset.

    The dataset provides access to metadata and protein data such as assays,
    raw assays, sequences, structures, and multiple sequence alignments (MSAs).

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

    assays_raw: list[AssayRaw] = Field(default_factory=list)
    """The raw assays present in the dataset."""

    sequences: list[Sequence] = Field(default_factory=list)
    """The sequences included in the dataset."""

    structures: list[Structure] = Field(default_factory=list)
    """The structures included in the dataset."""

    msas: list[MSA] = Field(default_factory=list)
    """The multiple sequence alignments included in the dataset."""

    publication: Publication | None = Field(default=None)
    """Publication information for the dataset."""

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
            union = left + [item for item in right if item not in left]

            # Deduplicate names to create a valid Dataset (see @model_validator)
            name_counts = collections.Counter(item.name for item in union)
            union_with_unique_names = []
            for i, item in enumerate(union):
                unique_name = (
                    item.name if name_counts[item.name] == 1 else f"{item.name}{i}"
                )
                union_with_unique_names.append(
                    dataclasses.replace(item, name=unique_name)
                )

            return union_with_unique_names

        # We expect only single publication,
        # and to be the same between dataset splits
        publication = self.publication or other.publication

        return Dataset(
            name=f"{self.name}_union_{other.name}",
            description=(
                f"Union of {self.name} and {other.name} datasets."
                f"\n{self.description}\n{other.description}"
            ),
            publication=publication,
            assay_variables=list_union(self.assay_variables, other.assay_variables),
            assay_targets=list_union(self.assay_targets, other.assay_targets),
            assays=list_union(self.assays, other.assays),
            assays_raw=list_union(self.assays_raw, other.assays_raw),
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
        is_assay_raw_match = sort_by_name(self.assays_raw) == sort_by_name(
            item.assays_raw
        )
        is_sequence_match = sort_by_name(self.sequences) == sort_by_name(item.sequences)
        is_structure_match = sort_by_name(self.structures) == sort_by_name(
            item.structures
        )
        is_msa_match = sort_by_name(self.msas) == sort_by_name(item.msas)
        is_publication_match = self.publication == item.publication
        return (
            is_assay_match
           
            and is_assay_raw_match
            and is_sequence_match
           
            and is_structure_match
           
            and is_msa_match
            and is_publication_match
        )

    def __contains__(self, other: Any) -> bool:
        """Implements the 'in' operator for Dataset."""
        if not isinstance(other, Dataset):
            return False
        # If a protein data type is empty,
        # it is a (mathematical) subset of any other
        is_assay_subset = (
            len(other.assays) == 0
            # An assay can be a subset of another assay, hence the double loop
            or all(
                any(other_assay in self_assay for self_assay in self.assays)
                for other_assay in other.assays
            )
        )
        is_assay_raw_subset = len(other.assays_raw) == 0 or all(
            raw_assay in self.assays_raw for raw_assay in other.assays_raw
        )
        is_sequence_subset = len(other.sequences) == 0 or all(
            seq in self.sequences for seq in other.sequences
        )
        is_structure_subset = len(other.structures) == 0 or all(
            struct in self.structures for struct in other.structures
        )
        is_msa_subset = len(other.msas) == 0 or all(
            msa in self.msas for msa in other.msas
        )
        # If none its always a subset of any set
        # If other.pub == self.pub, other is a subset
        # Other is not a subset when other != self
        is_publication_subset = (
            other.publication is None or other.publication == self.publication
        )
        return (
            is_assay_subset
            and is_assay_raw_subset
            and is_sequence_subset
            and is_structure_subset
            and is_msa_subset
            and is_publication_subset
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
        lines.append(f"\t\tassays_raw: {len(self.assays_raw)},")
        lines.append(f"\t\tsequences: {len(self.sequences)},")
        lines.append(f"\t\tstructures: {len(self.structures)},")
        lines.append(f"\t\tmsas: {len(self.msas)},")
        lines.append(f"\t\tassay_variables: {len(self.assay_variables)},")
        if self.publication:
            lines.append(f"\t\tpublication: {repr(self.publication)},")
        else:
            lines.append("\t\tpublication: None,")
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

        def _get_duplicate_names(items) -> list[str]:
            """Get duplicate names from a list of items."""
            name_counts = collections.Counter(item.name for item in items if item.name)
            return [name for name, count in name_counts.items() if count > 1]

        data_types = {
            Assay: self.assays,
            AssayVariable: self.assay_variables,
            AssayTarget: self.assay_targets,
            AssayRaw: self.assays_raw,
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

    @model_validator(mode="after")
    def _validate_msa_reference_sequences(self) -> "Dataset":
        """Ensure that MSA reference sequences are present in the sequences.

        Returns:
            Dataset: The validated dataset instance.

        Raises:
            ValueError: If a reference sequence is specified in an MSA but not found
                in the dataset's sequences.
        """
        sequence_names = {seq.name for seq in self.sequences}
        for msa in self.msas:
            if (
                msa.reference_sequence_name
                and msa.reference_sequence_name not in sequence_names
            ):
                raise ValueError(
                    f"MSA '{msa.name}' reference sequence "
                    f"'{msa.reference_sequence_name}' is not present in the dataset's "
                    "sequences."
                )
        return self

    @model_validator(mode="after")
    def _validate_assays_raw_have_reference_assay(self) -> "Dataset":
        """Ensure that each raw assay has a reference assay.

        Returns:
            Dataset: The validated dataset instance.

        Raises:
            ValueError: If a reference assay is specified in a raw assay but not
                found in the dataset's assays.
        """
        assay_names = {assay.name for assay in self.assays}
        for assay_raw in self.assays_raw:
            if assay_raw.name not in assay_names:
                raise ValueError(
                    f"Raw assay '{assay_raw.name}' must be matched to the corresponding assay by its name."
                )
        return self

    def fill_from_database(self, overwrite: bool = False) -> "Dataset":
        """Fill metadata from database for all available databases.
        Currently supports UniProt (in sequence) and DOI (in publication) identifiers.

        Args:
            overwrite (bool): If True, overwrite existing values.
            If False, only fill empty fields.

        Returns:
            Dataset: A new Dataset instance with updated metadata.
        """
        updated_sequences = [
            seq.fill_from_database(overwrite=overwrite) for seq in self.sequences
        ]
        updated_publication = (
            self.publication.fill_from_database(overwrite=overwrite)
            if self.publication
            else None
        )

        return self.model_copy(
            update={"sequences": updated_sequences, "publication": updated_publication}
        )

    def model_dump_json(self, **kwargs) -> str:
        """Override to ensure JSON serialization works with Bio objects.

        Biopython objects: Seq, Structure, MultipleSeqAlignment,
        don't have custom JSONEncoder, thus we rely on their __str__ method
        to return a string representation in order for
        Bio objects to be serializable.

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
        assays_raw = [AssayRaw.from_manifest_section(m) for m in manifest.assays_raw]
        sequences = itertools.chain(
            *[Sequence.from_manifest_section(s) for s in manifest.sequences]
        )
        structures = [Structure.from_manifest_section(s) for s in manifest.structures]
        msas = [MSA.from_manifest_section(m) for m in manifest.msas]

        return cls(
            name=manifest.name,
            description=manifest.description,
            publication=manifest.publication,
            assay_variables=manifest.assay_variables,
            assay_targets=manifest.assay_targets,
            assays=assays,
            assays_raw=assays_raw,
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
            (
                AssayRaw,
                DatasetArchiveLayout.ASSAYS_RAW_DIRECTORY,
                self.assays_raw,
            ),
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
            publication=self.publication,
            assay_targets=self.assay_targets,
            assay_variables=self.assay_variables,
            assays=[
                a.as_manifest_section(path=path)
                for a, path in zip(self.assays, data_paths.get(Assay, []), strict=True)
            ],
            assays_raw=[
                m.as_manifest_section(path=path)
                for m, path in zip(
                    self.assays_raw, data_paths.get(AssayRaw, []), strict=True
                )
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

    @staticmethod
    def _write_paths_to_zip(
        zip_: ZipFile,
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
            zip_.write(path, arcname=arcname_prefix / (arcname or path.name))

    def _create_archive(self, path: Path, *, temporary_directory: Path) -> Path:
        """Create a ZIP archive of the dataset."""
        archive_path = path / f"{self.name}{DatasetArchiveLayout.SUFFIX}"
        # The manifest Pydantic base model checks if the data path exists,
        # hence, we dump the data before creating and dumping the Manifest
        data_paths = self._dump_data(temporary_directory)
        manifest = self._create_manifest(data_paths)
        manifest_path = manifest.dump(path=temporary_directory)
        with ZipFile(archive_path, "w") as zip_:
            self._write_paths_to_zip(
                zip_, manifest_path, arcname=DatasetArchiveLayout.MANIFEST_FILE
            )
            self._write_paths_to_zip(
                zip_,
                *[assay.path for assay in manifest.assays],
                arcname_prefix=DatasetArchiveLayout.ASSAYS_DIRECTORY,
            )
            self._write_paths_to_zip(
                zip,
                *[assay_raw.path for assay_raw in manifest.assays_raw],
                arcname_prefix=DatasetArchiveLayout.ASSAYS_RAW_DIRECTORY,
            )
            self._write_paths_to_zip(
                zip,
                *[sequence.path for sequence in manifest.sequences],
                arcname_prefix=DatasetArchiveLayout.SEQUENCES_DIRECTORY,
            )
            self._write_paths_to_zip(
                zip_,
                *[structure.path for structure in manifest.structures],
                arcname_prefix=DatasetArchiveLayout.STRUCTURES_DIRECTORY,
            )
            self._write_paths_to_zip(
                zip_,
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

    @staticmethod
    def _default_aggregation_fn(col: pl.Expr, dtype: pl.DataType) -> pl.Expr:
        """Default aggregation function that adapts to data type.

        Example custom aggregation functions:
        - lambda col, dtype: col.median()  # Use median for all
        - lambda col, dtype: col.first()   # Use first for all
        - lambda col, dtype: col.max() if dtype.is_numeric() else col.mode().first()
            # Max for numeric, mode for categorical
        """
        if dtype.is_numeric():
            return col.mean()
        else:
            return col.first()

    def to_df(
        self,
        *,
        target_names: Collection[str] | str | None = None,
        agg: (
            Callable[[pl.Expr, pl.DataType], pl.Expr]
            | dict[str, Callable[[pl.Expr, pl.DataType], pl.Expr]]
            | None
        ) = None,
    ) -> pl.DataFrame:
        """Returns the dataset assay records as a Polars DataFrame.

        Args:
            target_names (Collection[str] | str | None): The target name(s) to include.
                If None, all target names are included. Defaults to None.
            agg (
                Callable[[pl.Expr, pl.DataType], pl.Expr]
                | dict[str, Callable[[pl.Expr, pl.DataType], pl.Expr]]
                | None
            ):
                Aggregation function or mapping. Can be:
                - Function: Applied to all targets
                - Dict: Maps target names to specific functions
                - None: Uses default (mean for numeric, first for categorical)

        Returns:
            pl.DataFrame: The DataFrame containing all records from all assays.

        Examples:
            >>> # Use median for all numeric targets
            >>> dataset = dummy_dataset()
            >>> dataset.to_df(
            ...     agg=lambda col, dtype: col.median() if dtype.is_numeric()
            ...     else col.first()
            ... )[["sequence", "var1", "numerical", "categorical"]]
            shape: (2, 4)
            ┌──────────┬──────┬───────────┬─────────────┐
            │ sequence ┆ var1 ┆ numerical ┆ categorical │
            │ ---      ┆ ---  ┆ ---       ┆ ---         │
            │ str      ┆ i32  ┆ f64       ┆ str         │
            ╞══════════╪══════╪═══════════╪═════════════╡
            │ ACDEFG   ┆ 2    ┆ 1.25      ┆ foo         │
            │ GFEDCA   ┆ 2    ┆ 2.25      ┆ bar         │
            └──────────┴──────┴───────────┴─────────────┘
            >>> # Custom per-target aggregation
            >>> dataset.to_df(agg={
            ...     "numerical": lambda col, dtype: col.max(),
            ...     "categorical": lambda col, dtype: col.mode().sort().first()
            ... })[["sequence", "var1", "categorical", "numerical"]]
            shape: (2, 4)
            ┌──────────┬──────┬─────────────┬───────────┐
            │ sequence ┆ var1 ┆ categorical ┆ numerical │
            │ ---      ┆ ---  ┆ ---         ┆ ---       │
            │ str      ┆ i32  ┆ str         ┆ f64       │
            ╞══════════╪══════╪═════════════╪═══════════╡
            │ ACDEFG   ┆ 2    ┆ bar         ┆ 1.5       │
            │ GFEDCA   ┆ 2    ┆ bar         ┆ 2.5       │
            └──────────┴──────┴─────────────┴───────────┘
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

        # If no duplication no need for aggregation
        group_cols = ["sequence"] + variable_names
        duplicate_count = df.group_by(group_cols).len().filter(pl.col("len") > 1).height
        if duplicate_count == 0:
            return df.sort(group_cols)

        if callable(agg):
            agg_fn = agg
            custom_agg = None
        elif isinstance(agg, dict):
            agg_fn = self._default_aggregation_fn
            custom_agg = agg
        else:
            agg_fn = self._default_aggregation_fn
            custom_agg = None

        agg_exprs = []
        applied_methods = []

        for t in target_names:
            dtype = df[t].dtype

            if custom_agg and t in custom_agg:
                try:
                    agg_expr = custom_agg[t](pl.col(t), dtype).alias(t)
                    agg_exprs.append(agg_expr)
                    applied_methods.append(f"{t}: custom")
                except Exception as e:
                    raise ValueError(f"Custom aggregation failed for '{t}': {e}") from e
            else:
                try:
                    agg_expr = agg_fn(pl.col(t), dtype).alias(t)
                    agg_exprs.append(agg_expr)
                    if agg_fn == self._default_aggregation_fn:
                        method = "mean" if dtype.is_numeric() else "first"
                    else:
                        method = "custom"
                    applied_methods.append(f"{t}: {method}")
                except Exception as e:
                    raise ValueError(f"Aggregation failed for '{t}': {e}") from e

        if duplicate_count > 0:
            warnings.warn(
                (
                    f"Found {duplicate_count} groups with duplicates. "
                    f"Aggregation applied: {', '.join(applied_methods)}"
                ),
                UserWarning,
                stacklevel=2,
            )

        df = df.group_by(group_cols).agg(agg_exprs).sort(group_cols)
        return df


def dummy_dataset() -> Dataset:
    """Create a trivial dataset for illustrative purposes."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay = Assay(
        name="assay1",
        records=[
            (sequence1, 1.0, "foo"),
            (sequence1, 1.5, "bar"),
            (sequence2, 2.0, "bar"),
            (sequence2, 2.5, "bar"),
        ],
        variables={"var1": 2},
        columns=["sequence", "numerical", "categorical"],
    )
    dataset = Dataset(
        name="dataset_with_single_assay",
        description="A dataset containing a single assay.",
        assay_variables=[AssayVariable(name="var1", description="")],
        assay_targets=[
            AssayTarget(name="numerical", description=""),
            AssayTarget(name="categorical", description=""),
        ],
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


class SubsetsArchiveLayout:
    """The layout of a subsets archive."""

    SUFFIX = f".splits{DatasetArchiveLayout.SUFFIX}"
    """The suffix of a subsets archive."""

    DATASET_ARCHIVE = f"dataset{DatasetArchiveLayout.SUFFIX}"
    """The directory containing the dataset."""

    SLICES_FILE = "slices.json"
    """The file containing the slices."""


@dataclasses.dataclass(kw_only=True)
class Subsets:
    """A collection of dataset subsets (slices).

    References:
    ../../docs/decisions/0007-dataset-splits.md
    """

    dataset: Dataset
    """The dataset that is sliced."""

    slices: list[DatasetSlice] | dict[str, list[DatasetSlice]] = dataclasses.field(
        default_factory=dict
    )
    """The slices that create the collection of subsets.

    Slices can be stored either as a list, or as a dict where the key is an
    arbitrary label associated with a list of slices. The latter is useful for
    storing slices obtained from different ways to slice the dataset and when it
    is of interest to compare these.
    """

    def __len__(self) -> int:
        """The length of the subset collection."""
        return len(tuple(self.__iter__()))

    def __getitem__(self, key: str) -> "Subsets":
        """Get a subset by key.

        Args:
            key (str): The key of the subset to get.

        Returns:
            Subset: The subset corresponding to the key.

        Raises:
            TypeError: If the slices are not stored as a dictionary.
            KeyError: If the key is not found in the slices.
        """
        if not isinstance(self.slices, dict):
            raise TypeError("Subsets slices are not stored as a dictionary.")
        if key not in self.slices:
            raise KeyError(f"Key '{key}' not found in subsets slices.")
        slices = self.slices[key]
        return Subsets(dataset=self.dataset, slices=slices)

    def __iter__(self) -> Iterator[Dataset]:
        """Iterate over the slices in this subset collection."""
        if not isinstance(self.slices, list):
            raise TypeError(
                "Cannot iterate over subsets when slices are not a list. "
                "Use `for split in subsets[strategy_name]:` instead."
            )
        for slc in self.slices:
            yield self.dataset[slc]

    def update(self, **subsets: "Subsets") -> None:
        """Update the subsets with other subsets.

        Args:
            **subsets (Subsets) : The subsets to update. The keys are used as
                keys in the slices dictionary.
        """
        if not isinstance(self.slices, dict):
            raise TypeError("Cannot update subsets when slices are not a dictionary.")
        for subset in subsets.values():
            if subset.dataset != self.dataset:
                raise ValueError(
                    "Cannot update subsets with different datasets. "
                    f"Got {subset.dataset} while having {self.dataset}."
                )
        slices = {subset_name: subset.slices for subset_name, subset in subsets.items()}
        self.slices = {**self.slices, **slices}

    @staticmethod
    def _loads_slices(
        slices_str: str,
    ) -> list[DatasetSlice] | dict[str, list[DatasetSlice]]:
        """Load the slices from a JSON string.

        Args:
            slices_str (str): The JSON string representation of the slices.
        """
        data = json.loads(slices_str)
        if isinstance(data, dict):
            slices = {
                key: [DatasetSlice.from_dict(slc) for slc in slc_list]
                for key, slc_list in data.items()
            }
        else:
            slices = [DatasetSlice.from_dict(slc) for slc in data]
        return slices

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
        with ZipFile(path, "r") as zip_, TemporaryDirectory() as temp_dir:
            dataset_archive = zip_.extract(
                SubsetsArchiveLayout.DATASET_ARCHIVE, path=temp_dir
            )
            dataset = Dataset.from_path(Path(dataset_archive))
            slices_str = zip_.read(SubsetsArchiveLayout.SLICES_FILE)
            slices = cls._loads_slices(slices_str.decode())
        return cls(dataset=dataset, slices=slices)

    def _dumps_slices(self) -> str:
        """Dump the slices to a JSON string.

        Returns:
            str: The JSON string representation of the slices.
        """
        if isinstance(self.slices, dict):
            data = {
                key: [dataclasses.asdict(slc) for slc in slices]
                for key, slices in self.slices.items()
            }
        else:
            data = [dataclasses.asdict(slc) for slc in self.slices]
        slices_str = json.dumps(data)
        return slices_str

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
            path /= f"{self.dataset.name}{SubsetsArchiveLayout.SUFFIX}"
        # While a SE practice is to avoid IO to disk where possible,
        # we use a temporary directory here as long as dataset dump requires
        # it.
        with ZipFile(path, "w") as zip_, TemporaryDirectory() as temp_dir:
            dataset_archive = self.dataset.dump(path=Path(temp_dir))
            zip_.write(dataset_archive, arcname=SubsetsArchiveLayout.DATASET_ARCHIVE)
            slices_str = self._dumps_slices()
            zip_.writestr(SubsetsArchiveLayout.SLICES_FILE, slices_str)
        return path

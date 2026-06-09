import dataclasses
import functools
import itertools
import json
from collections.abc import Collection
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Union

import annotated_types
import polars as pl
import pydantic
from Bio.Seq import Seq
from pydantic import (
    BaseModel,
    ConfigDict,
    FilePath,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from .sequence import Sequence, SequenceAlphabet, SequenceType

SEQUENCE = "sequence"
RECORDS = list[tuple[Sequence | str | int | float | bool | str | None, ...]]


class AssayFormat(StrEnum):
    """AssayFormat.

    Supported assay file formats.
    """

    CSV = ".csv"
    """A comma separated text file"""


class FieldEncoding(StrEnum):
    """FieldEncoding.

    How to encode the variable when used as regression input.

    A variable may be best represented as a categorical, e.g., 1-hot encoded,
    or directly as a numerical float.
    """

    CATEGORICAL = "categorical"
    """Categorical: e.g., 1-hot encoded"""

    NUMERICAL = "numerical"
    """Numerical: e.g., float"""


class LibraryConstructionMethod(StrEnum):
    """LibraryConstructionMethod.

    The method used to construct the protein library.
    """

    RANDOM_MUTAGENESIS = "random_mutagenesis"
    """Random mutagenesis

    Uncontrolled introduction of
    mutations across random positions (ex. epPCR)"""

    SITE_SATURATED_MUTAGENESIS = "site_saturated_mutagenesis"
    """Site-saturated mutageneisis

    Introduction of mutants
    at specific sites with complete coverage (ex. NNK/S)"""

    DISCRETE = "discrete"
    """Discrete

    Designed libraries targeting specific positions
    and specific amino acid coverage (ex. oligo pools)"""

    SHUFFLING = "shuffling"
    """Shuffling

    Random motif splitting/assembly-based methods"""


class AssayMethod(StrEnum):
    """AssayMethod.

    The type of assay used to measure variant fitness.
    """

    SELECTION = "selection"
    """Selection

    Fitness measurement is coupled to cell growth"""

    SCREEN = "screen"
    """Screen

    Fitness measurement is not coupled to cell growth"""


class AssayReadout(StrEnum):
    """AssayReadout.

    The readout method used in the assay.
    """

    RNA_SEQUENCING = "rna_sequencing"
    """RNA sequencing

    Fitness is estimated from RNA sequencing"""

    DNA_SEQUENCING = "dna_sequencing"
    """DNA sequencing

    Fitness is estimated from DNA sequencing"""

    FLUORESCENCE = "fluorescence"
    """Fluorescence

    Fitness is estimated from product and/or
    reporter fluorescence"""

    PRODUCT = "product"
    """Product

    Fitness is estimated from product concentration
    measured in some manner other than fluorescence"""


class AssayTransformation(StrEnum):
    """AssayTransformation.

    The transformation applied to the raw assay data.
    """

    NONE = "none"
    """none

    Raw read counts, product amounts, etc."""

    NON_PARAMETRIC = "non_parametric"
    """Non-parametric

    Some basic data transformation applied
    (ex. ratio of read counts, log transformation, etc.)"""

    FIT = "fit"
    """Fit

    Some regression/ML-based fit applied to data
    (ex. MoCHI, Enrich2, etc.)"""


class TargetPhenotype(StrEnum):
    """Target phenotype.

    Target phenotype the assay attempts to capture.
    """

    BINDING = "binding"
    """Binding

    Protein binding to something"""

    ACTIVITY = "activity"
    """Activity

    Some chemical reaction the protein performs"""

    ABUNDANCE = "abundance"
    """Abundance

    Measurement of protein/RNA abundance"""

    EXPRESSION = "expression"
    """Expression

    Measurement of protein expression"""

    STABILITY = "stability"
    """Stability

    Thermostability measurements"""

    OTHER = "other"
    """Other

    Placeholder for things that don't fit above"""


@dataclasses.dataclass(kw_only=True, frozen=False)
class Field:
    """A data field for an assay associated quantity or protein property.

    A field is used to describe assay variables, e.g., assay conditions such as the
    pH, or the prediction target, e.g., the observed activity or stability.

    Todo:
    ----
    Add field for setting the type.
    """

    name: str
    """The name of the field."""

    value: bool | int | float | str | None = None
    """The value of the field."""

    unit: str | None = None
    """The unit of the field."""

    description: str | None = None
    """Description of the field."""

    encoding: FieldEncoding | None = None

    alias: str | None = None
    """An alias for this field.

    Example use is when a field is referred to be a different name in an input csv file.
    """

    def fill_from_parent(self, parent: "Field") -> None:
        """Fill value, unit and description this field from another field.

        Raises:
            ValueError if names do not match (expected for parent / child) relationship.
            ValueError if an attribute is set of self but differs on parent.
        """
        if self.name != parent.name:
            raise ValueError("Expected names to match")
        for attr in ("value", "unit", "description", "encoding"):
            own = getattr(self, attr)
            if own is not None and own != getattr(parent, attr):
                raise ValueError(f"Attribute {attr} for field {self.name} redefined")
            setattr(self, attr, getattr(parent, attr))

    def without_alias(self) -> "Field":
        """Get a Field identical to this one but without its alias."""
        return Field(
            name=self.name,
            value=self.value,
            unit=self.unit,
            description=self.description,
            encoding=self.encoding,
        )

    @property
    def alias_(self) -> str:
        """Get the alias for this field (i.e., name if no alias available)."""
        # The obvious getter/setter pattern is not compatible with dataclasses
        return self.name if self.alias is None else self.alias

    def __eq__(self, other: "Field") -> bool:
        """Implements the '==' operator for Field."""
        if not isinstance(other, Field):
            return False
        return (
            # Description is not considered for equality
            self.name == other.name
            and self.unit == other.unit
            and self.value == other.value
            and self.encoding == other.encoding
        )

    def to_dict(self):
        result = dataclasses.asdict(self)
        result["encoding"] = str(self.encoding) if self.encoding is not None else None
        return result

    # noinspection PyTypeChecker
    @functools.cached_property
    def polars_type(self) -> pl.DataType:
        """Returns the Polars data type of the field."""
        match self.value:
            case bool():
                return pl.Boolean
            case int():
                return pl.Int64
            case float():
                return pl.Float64
            case str():
                return pl.Utf8
            case None:
                return pl.Unknown
            case _:
                raise ValueError(f"Unsupported field type: {type(self.value)}")


class _ManifestSection(BaseModel):
    """The base class for the assay manifest sections."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The assay name to which the raw data belongs."""

    path: FilePath
    """The path to the assay file, csv only."""

    description: str | None = None
    """A brief description"""

    @field_validator("path", mode="before", check_fields=True)
    @classmethod
    def validate_path_before(cls, path: Path, info: ValidationInfo) -> Path:
        """Optionally, extend the path with the `relative_to_path` from the context.

        This validator runs before other validations because the `FilePath`
        validates if the file exists, which requires the full path.
        """
        if info.context and info.context.get("relative_to_path"):
            path = info.context["relative_to_path"] / path
        return path

    @field_validator("path", mode="after", check_fields=True)
    @classmethod
    def validate_path_after(cls, path: Path) -> Path:
        """Validate that the file format is supported."""
        fmt = path.suffix.lower()
        if fmt not in AssayFormat:
            raise ValueError(f"Unsupported file format: {fmt}")
        return path

    @field_serializer("path", check_fields=True)
    def serialize_path(self, path: Path, info: SerializationInfo) -> str:
        """Serialize the path as a Posix path."""
        if info.context and info.context.get("relative_to_path"):
            path = path.relative_to(info.context["relative_to_path"])
        return path.as_posix()

    @functools.cached_property
    def _header(self) -> str:
        """Returns the header of the assay file."""
        message = "Update header reading for new formats"
        assert [f.value for f in AssayFormat] == [".csv"], message
        # Not splitting the header to maintain consistency across formats
        with self.path.open("r") as f:
            header = f.readline()
        return header


class AssayRawManifestSection(_ManifestSection):
    """The manifest section describing the raw assay data."""

    fields: Annotated[list[Field], annotated_types.Len(min_length=1)]
    """The list of fields in the raw assay."""

    @model_validator(mode="after")
    def validate_field_names(self) -> "AssayRawManifestSection":
        """Validate whether field names are present in the `path` file."""
        for field in self.fields:
            if field.name not in self._header:
                raise ValueError(
                    f"Field '{field.name}' not found in the file: {self.path}"
                )
        return self


class AssayManifestSection(_ManifestSection):
    """The manifest section describing an assay."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    sequence_alias: str | None = None
    """The sequence feature name given in the file."""

    sequence_alphabet: SequenceAlphabet | None = None
    """The alphabet of the sequences of the assay."""

    targets: list[Field] = pydantic.Field(default_factory=list)
    """The list of prediction targets in this assay."""

    non_targets: list[Field] = pydantic.Field(default_factory=list)
    """List of non-target fields that are included but are not prediction targets."""

    variables: dict[str, bool | int | float | str] = pydantic.Field(
        default_factory=dict
    )
    """The variable key:value pairs, key is the name of the assay variable (defined in
    dataset manifest and value of the variable."""

    path: FilePath
    """The path to the assay file, csv only."""

    readout: AssayReadout | None = None
    """The readout method used in the assay."""

    library_construction_method: LibraryConstructionMethod | None = None
    """The method used to construct the protein library."""

    assay_method: AssayMethod | None = None
    """The type of assay used to measure variant fitness."""

    transformation: AssayTransformation | None = None
    """The transformation applied to the raw assay data."""

    target_phenotype: TargetPhenotype | None = None
    """The property the assay attempts to capture."""

    has_uncertainty: bool | None = None
    """Has uncertainty

    Authors include some form of assay uncertainty measure (they have replicate
    experiments and/or correlation to low-throughput data)"""

    @model_validator(mode="after")
    def validate_fields(self) -> "AssayManifestSection":
        """Validate whether field names are present in the `path` file."""
        sequence = Field(name="sequence", alias=self.sequence_alias)
        for v in [sequence] + self.targets + self.non_targets:
            if v.alias_ not in self._header:
                raise ValueError(
                    f"Feature '{v.alias_}' not found in the file: {self.path}"
                )
        return self

    @field_serializer("sequence_alphabet")
    def serialize_sequence_alphabet(self, sequence_alphabet: SequenceAlphabet) -> str:
        """Serialize the sequence alphabet as a string."""
        return str(sequence_alphabet.value)


@dataclasses.dataclass(kw_only=True, frozen=True)
class AssaySlice:
    """A slice of an assay.

    Python builtin slices are also supported for slicing assays. However, if
    both columns and records need to be sliced, this class can be used.

    See :func:Assay.__getitem__ for more information.
    """

    columns: list[str] | None = None
    """The list of column names to get. If None, all columns are included."""

    records: list[bool] | None = None
    """The boolean mask for the records. If None, all records are included."""

    metadata: dict[str, Union[str, float]] | None = None
    """Metadata associated with the AssaySlice."""

    @classmethod
    def from_json(cls, contents: str) -> "AssaySlice":
        """Create an assay slice from a JSON string.

        Args:
            contents: The JSON string to create the assay slice from.

        Returns:
            The assay slice created from the JSON string.
        """
        return cls(**json.loads(contents))

    def to_json(self) -> str:
        """Convert the assay slice to a JSON string.

        Returns:
            A JSON string representation of the assay slice.
        """
        return json.dumps(dataclasses.asdict(self))

    def __repr__(self):
        """Returns a concise string representation of the slice."""
        if self.records is None:
            return f"AssaySlice(columns={self.columns})"

        n_items = len(self.records)

        if n_items <= 5:
            records_repr = "[" + ", ".join(repr(x) for x in self.records) + "]"
            return (
                f"AssaySlice(columns={self.columns}, records={records_repr}, "
                f"metadata={self.metadata})"
            )
        else:
            records_repr = (
                f"[{self.records[0]}, ..., {self.records[-1]}] (len={n_items})"
            )
            return (
                f"AssaySlice(columns={self.columns}, records={records_repr}, "
                f"metadata={self.metadata})"
            )


@dataclasses.dataclass(kw_only=True, frozen=True)
class AssayRaw:
    """The raw data on which the assay is based."""

    name: str
    """The name of the assay."""

    description: str | None = None
    """A brief description"""

    fields: list[Field] = dataclasses.field(
        default_factory=lambda: [Field(name=SEQUENCE)]
    )
    """The raw assay fields."""

    records: RECORDS = dataclasses.field(default_factory=list)
    """The raw assay records."""

    def __len__(self) -> int:
        """The length of the assay, i.e. the number of records."""
        return len(self.records)

    def is_empty(self) -> bool:
        """Returns True if the assay has no records."""
        return len(self) == 0

    @classmethod
    def from_manifest_section(
        cls,
        section: AssayRawManifestSection,
    ) -> "AssayRaw":
        """Creates AssayRaw from a manifest section.

        Args:
            section: The manifest section
                describing the raw assay data.

        Returns:
            AssayRaw: The created AssayRaw object.
        """
        schema = {
            field.name: field.polars_type
            for field in section.fields
            if field.polars_type != pl.Unknown  # Let polars infer Unknown types
        }
        # Reusing polars as we already depend on it for assays
        records = list(pl.read_csv(section.path, schema_overrides=schema).iter_rows())
        return cls(
            name=section.name,
            records=records,
            fields=section.fields,
            description=section.description,
        )

    def as_manifest_section(self, *, path: Path) -> AssayRawManifestSection:
        """Converts the AssayRaw to a manifest section.

        Args:
            path: The path to the raw assay file.

        Returns:
            AssayRawManifestSection: The manifest section representing
                the raw assay.
        """
        return AssayRawManifestSection(
            name=self.name,
            path=path,
            description=self.description,
            fields=self.fields,
        )

    def dump(
        self,
        *,
        path: Path | None = None,
        fmt: AssayFormat = AssayFormat.CSV,
    ) -> Path:
        """Dump the raw assay data to a file.

        Args:
            path: The output directory to dump the raw assay
                file in. If None, the current working directory is used.
            fmt: The file format. Defaults to
                AssayRawFormat.CSV.

        Raises:
            NotImplementedError: if the file type is not supported.
        """
        path = path or Path.cwd()
        if path.is_dir():
            path /= f"{self.name}{fmt}"

        schema = {f.name: f.polars_type for f in self.fields}
        df = pl.DataFrame(self.records, schema=schema, strict=True, orient="row")
        match fmt:
            case AssayFormat.CSV:
                df.write_csv(path)
            case _:
                raise NotImplementedError(f"Unsupported file format: {fmt}")
        return path

    def to_df(self, *, fields: list[Field] | None = None) -> pl.DataFrame:
        """Returns the assay records as a Polars DataFrame.

        Args:
            fields: The fields to include.
                If None, all fields are included. Defaults to None.

        Returns:
            pl.DataFrame: The DataFrame containing the assay data.
        """
        fields = fields or self.fields
        data = {
            f.name: [r[i] for r in self.records]
            for i, f in enumerate(self.fields)
            if f in fields
        }
        schema = {f.name: f.polars_type for f in self.fields if f in fields}
        return pl.DataFrame(data, schema=schema, strict=True)


@dataclasses.dataclass(kw_only=True, frozen=True)
class Assay(AssayRaw):
    """An assay in the dataset."""

    variables: dict[str, int | float | bool | str] = dataclasses.field(
        default_factory=dict
    )
    """The variables of the assay, defined in the manifest."""

    non_targets: list[Field] = dataclasses.field(default_factory=list)
    """List of non-target feature names that are included but not targets."""

    readout: AssayReadout | None = None
    """The readout method used in the assay."""

    library_construction_method: LibraryConstructionMethod | None = None
    """The method used to construct the protein library."""

    assay_method: AssayMethod | None = None
    """The type of assay used to measure variant fitness."""

    transformation: AssayTransformation | None = None
    """The transformation applied to the raw assay data."""

    target_phenotype: TargetPhenotype | None = None
    """The property the assay attempts to capture."""

    has_uncertainty: bool | None = None
    """Has uncertainty

    Authors include some form of assay uncertainty measure (they have replicate
    experiments and/or correlation to low-throughput data)"""

    @property
    def sequence_feature_name(self) -> str:
        """The sequence feature name.

        Manifest defines first field to be the sequence - here we take it for granted
        that this is adhered to.
        """
        return self.fields[0].name

    @property
    def target_feature_names(self) -> list[str]:
        """Returns the target feature names in the assay records."""
        all_names = [f.name for f in self.fields[1:]]  # Exclude sequence
        non_target_names = [f.name for f in self.non_targets]
        return [name for name in all_names if name not in non_target_names]

    @property
    def number_of_variants(self) -> int:
        """Returns the number of variants in the assay."""
        return len({str(e[0]) for e in self.records})

    def __contains__(self, item: "Assay") -> bool:
        """Implements the 'in' operator for Assay.

        If the given item is an Assay, checks if all its records and variables
        are contained in this assay.
        """
        if not isinstance(item, Assay):
            return False
        return all(record in self.records for record in item.records) and all(
            k in self.variables and self.variables[k] == v
            for k, v in item.variables.items()
        )

    def __eq__(self, item: "Assay") -> bool:
        """Implements the '==' operator for Assay."""
        if not isinstance(item, Assay):
            return False
        return (
            self.records == item.records
            and self.variables == item.variables
            and self.fields == item.fields
            and self.non_targets == item.non_targets
            and self.readout == item.readout
            and self.library_construction_method == item.library_construction_method
            and self.assay_method == item.assay_method
            and self.transformation == item.transformation
            and self.target_phenotype == item.target_phenotype
            and self.has_uncertainty == item.has_uncertainty
        )

    @staticmethod
    def _slice_columns(assay: "Assay", slc: list[str] | None) -> "Assay":
        """Slice the assay columns given a list of column names."""
        is_columns_slice = (
            isinstance(slc, list) and len(slc) > 0 and isinstance(slc[0], str)
        ) or (isinstance(slc, list) and len(slc) == 0)  # Empty slice
        if not is_columns_slice or slc is None:
            return assay

        fields_by_name = {e.name: e for e in assay.fields}
        try:
            fields_slice = [fields_by_name[e] for e in slc]
        except KeyError as e:
            raise KeyError(f"Undefined columns: {e}") from e

        if not fields_slice:
            records = []
        else:
            field_indices = [assay.fields.index(column) for column in fields_slice]
            records = [
                tuple(record[column_index] for column_index in field_indices)
                for record in assay.records
            ]
        return dataclasses.replace(assay, records=records, fields=fields_slice)

    @staticmethod
    def _slice_records(assay: "Assay", slc: list[bool] | None) -> "Assay":
        """Slice the assay records given a slice or a boolean masks."""
        is_records_slice = (
            isinstance(slc, list) and len(slc) > 0 and isinstance(slc[0], bool)
        ) or (isinstance(slc, list) and len(slc) == 0)  # Empty slice
        if not is_records_slice or slc is None:
            return assay

        if len(slc) == 0:
            records = []
        else:
            records = list(itertools.compress(assay.records, slc))
        return dataclasses.replace(assay, records=records)

    def __getitem__(self, slc: AssaySlice | list[bool | str]) -> "Assay":
        """Slice the assay to get a subset.

        Args:
            slc:
                1. If an AssaySlice is given, it can contain both column names and
                    a boolean mask for the records.
                2. If a list of strings is given, it is treated as a list of
                    column names.
                3. If a list of booleans, it is treated as a boolean mask for
                    the records.

        Note:
        An empty list returns an assay WITHOUT records and WITH the columns. If
        you want to slice to have no columns, use `AssaySlice(columns=[])`
        instead.
        """
        if isinstance(slc, int):
            # The Assay is a container with more than records, getting a single record
            # would mean losing the other information or returning an Assay with
            # a list of one record. The former is not desired and the latter is
            # ambiguous with the slicing operation.
            raise NotImplementedError("Getting a single record is not supported.")
        if isinstance(slc, str):
            # This would return a vector, but we are sticking with a matrix-like
            # structure.
            raise NotImplementedError(
                "Getting a single column is not supported. "
                f"Use a list with one element instead: [{slc}]"
            )

        assay = self
        is_assay_slice = isinstance(slc, AssaySlice)
        if is_assay_slice or len(slc) > 0:
            # An empty list is treated as an empty records slice. If you want to
            # have an empty column slice use `AssaySlice(columns=[])`
            assay = self._slice_columns(assay, slc.columns if is_assay_slice else slc)
        assay = self._slice_records(assay, slc.records if is_assay_slice else slc)

        return assay

    def __repr__(self) -> str:
        """Return a string representation of the Assay object."""
        lines = [f"Assay(\n\tname='{self.name}',"]
        if self.description:
            desc = (
                self.description[:60] + "..."  # noqa
                if len(self.description) > 60
                else self.description
            )
            lines.append(f"\tdescription: {desc},")
        else:
            lines.append("\tdescription: None,")

        if self.variables:
            lines.append(f"\tvariables: {len(self.variables)},")
            for k, v in self.variables.items():
                lines.append(f"\t\t{k}: {v},")
        else:
            lines.append("\tvariables: 0,")

        lines.append("\trecords:")
        n_recs = min(len(self.records), 3)
        if n_recs == 0:
            lines.append("\t\t<no records>")
        for i, record in enumerate(self.records[:n_recs]):
            seq = record[0]
            targets = record[1:]
            seq_str = str(seq.value)
            if len(seq_str) > 30:
                seq_str = seq_str[:30] + "..."
            lines.append(f"\t\t{seq_str}, {targets},")
            if i == 2 and len(self.records) > 3:
                lines.append("\t\t...")
                break
        lines.append(")")
        return "\n".join(lines)

    @classmethod
    def from_manifest_section(cls, section: AssayManifestSection) -> "Assay":
        """Create an Assay instance from a manifest section."""
        sequence_field = Field(name=SEQUENCE, alias=section.sequence_alias)
        all_fields = [sequence_field] + section.targets + section.non_targets
        df = pl.read_csv(section.path, columns=[f.alias_ for f in all_fields])

        df = df.with_columns(
            # Sequences are created from sequence strings present in the file
            # The sequence name is taken from the string itself as the name is not
            # provided in the assay file.
            pl.col(sequence_field.alias_)
            .map_elements(
                lambda seq: Sequence(
                    # The type of the sequence is set to "standard". This would be
                    # removed in future and support lookup into dataset.sequences.
                    name=seq,
                    value=Seq(seq),
                    type=SequenceType.STANDARD,
                    alphabet=section.sequence_alphabet,
                ),
                return_dtype=pl.Object,
            )
            .alias("sequence_object")
        )
        records = list(
            df.select(
                "sequence_object",
                *[f.alias_ for f in section.targets],
                *[f.name for f in section.non_targets],
            ).iter_rows()
        )

        return cls(
            name=section.name or section.path.stem,
            records=records,
            fields=[sequence_field] + section.targets + section.non_targets,
            description=section.description,
            variables=section.variables,
            non_targets=section.non_targets,
            readout=section.readout,
            library_construction_method=section.library_construction_method,
            assay_method=section.assay_method,
            transformation=section.transformation,
            target_phenotype=section.target_phenotype,
            has_uncertainty=section.has_uncertainty,
        )

    def as_manifest_section(self, *, path: Path) -> AssayManifestSection:
        """Create `AssayManifestSection` from the assay.

        Args:
            path: The path to the assay file.

        Returns:
            AssayManifestSection: The manifest section for the assay.
        """
        # Get the sequence alphabet from the first record
        if self.is_empty():
            sequence_alphabet = None
        else:
            sequence_alphabet = self.records[0][0].alphabet
        return AssayManifestSection(
            name=self.name,
            description=self.description,
            sequence_alias=None,
            sequence_alphabet=sequence_alphabet,
            targets=[
                f.without_alias()
                for f in self.fields
                if f.name in self.target_feature_names
            ],
            non_targets=self.non_targets,
            variables=self.variables,
            path=path,
            readout=self.readout,
            library_construction_method=self.library_construction_method,
            assay_method=self.assay_method,
            transformation=self.transformation,
            target_phenotype=self.target_phenotype,
            has_uncertainty=self.has_uncertainty,
        )

    def to_df(
        self, *, target_names: Collection[str] | str | None = None
    ) -> pl.DataFrame:
        """Returns the assay records with assay variables as a Polars DataFrame.

        Args:
            target_names: The target name(s) to include.
                If None, all target names are included. Defaults to None.

        Returns:
            pl.DataFrame: The DataFrame containing all records from the assay.
        """
        if self.is_empty():
            # If no records are present, return empty DataFrame
            return pl.DataFrame(schema=[SEQUENCE])
        if target_names:
            if isinstance(target_names, str):
                target_names = {target_names}
            else:
                target_names = set(target_names).intersection(self.target_feature_names)
            if not target_names:
                # If not matching target names, return empty DataFrame
                return pl.DataFrame(schema=[SEQUENCE])
        else:
            target_names = self.target_feature_names

        variables = [
            pl.lit(var_value).alias(var_name)
            for var_name, var_value in self.variables.items()
        ]
        schema = {f.name: f.polars_type for f in self.fields}
        df = (
            pl.DataFrame(self.records, schema=schema, orient="row")
            .select([self.sequence_feature_name] + list(target_names))
            .with_columns(
                pl.col(self.sequence_feature_name).map_elements(
                    lambda seq: str(seq.value), return_dtype=pl.Utf8
                )
            )
            .rename({self.sequence_feature_name: SEQUENCE})
            .with_columns(variables)
        )

        return df

    def dump(
        self, *, path: Path | None = None, fmt: AssayFormat = AssayFormat.CSV
    ) -> Path:
        """Dump the assay data to a file.

        Supported formats:
        - CSV (.csv)

        Args:
            path: The output directory to dump the assay file in. If
                None, the current working directory is used.
            fmt: The file format

        Raises:
            NotImplementedError: if the file type is not supported.
        """
        path = path or Path.cwd()
        if path.is_dir():
            path /= f"{self.name}{fmt.value}"

        schema = {f.name: f.polars_type for f in self.fields}
        df = pl.DataFrame(
            self.records,
            schema=schema,
            orient="row",
        )
        if self.sequence_feature_name:
            df = df.with_columns(
                pl.col(self.sequence_feature_name).map_elements(
                    lambda seq: str(seq.value), return_dtype=pl.Utf8
                )
            )
        match fmt:
            case AssayFormat.CSV:
                df.write_csv(path)
            case _:
                raise NotImplementedError(f"Unsupported file type: {fmt.value}")  # noqa
        return path

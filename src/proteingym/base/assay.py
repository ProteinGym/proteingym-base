import dataclasses
from enum import StrEnum
from pathlib import Path

import polars as pl
from Bio.Seq import Seq
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from .sequence import Sequence, SequenceAlphabet, SequenceType


class AssayFormat(StrEnum):
    """Supported assay file formats."""

    CSV = ".csv"
    """A comma separated text file"""


class AssayVariable(BaseModel):
    """Definition of an assay variable."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The name of the variable."""

    unit: str | None = None
    """The unit of the variable."""

    value: bool | int | float | str | None = None
    """The value of the variable, can be a bool, int, float, or str."""

    description: str | None = None
    """Description of the variable."""


class AssayTarget(BaseModel):
    """Definition of an assay target."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The name of the target."""

    unit: str | None = None
    """The unit of the target."""

    value: bool | int | float | str | None = None
    """The value of the target, can be a bool, int, float, or str."""

    description: str | None = None
    """Description of the target."""


class AssayManifestSection(BaseModel):
    """This is the manifest section for Assays.

    They can be loaded from a file. This object is used to
    validate the assay manifest.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str | None = None
    """The name of the assay."""

    description: str | None = None
    """Description of the assay."""

    sequence: str = "sequence"
    """The sequence feature name given in the file."""

    sequence_alphabet: SequenceAlphabet
    """The alphabet of the sequences of the assay."""

    targets: list[str] = Field(default_factory=list)
    """The list of target names that are present in the file."""

    variables: dict[str, bool | int | float | str] = Field(default_factory=dict)
    """The variable key:value pairs, key is the name of the assay variable (defined in
    dataset manifest and value of the variable."""

    path: FilePath
    """The path to the assay file, csv only."""

    @field_validator("path", mode="before", check_fields=True)
    def validate_path(cls, path: Path, info: ValidationInfo) -> Path:
        """Optionally, extend the path with the `relative_to_path` from the context."""
        if info.context and info.context.get("relative_to_path"):
            path = info.context["relative_to_path"] / path
        return path

    @field_serializer("path", check_fields=True)
    def serialize_path(self, path: Path, info: SerializationInfo) -> str:
        """Serialize the path as a Posix path."""
        if info.context and info.context.get("relative_to_path"):
            path = path.relative_to(info.context["relative_to_path"])
        return path.as_posix()

    @model_validator(mode="after")
    def validate_feature_names(self) -> "AssayManifestSection":
        """Validate whether feature names are present in the `path` file."""
        with self.path.open("r") as f:
            header = f.readline()
        for v in (self.sequence, *self.targets):
            if v not in header:
                raise ValueError(f"Feature '{v}' not found in the file: {self.path}")
        return self

    @field_serializer("sequence_alphabet")
    def serialize_sequence_alphabet(self, sequence_alphabet: SequenceAlphabet) -> str:
        """Serialize the sequence alphabet as a string."""
        return sequence_alphabet.value


@dataclasses.dataclass
class Assay:
    """An assay in the dataset."""

    name: str
    """The name of the assay."""

    records: list[tuple[Sequence | str | int | float | bool | str]]
    """The records of the assay, tuple with Sequence, target values."""

    columns: list[str] = dataclasses.field(default_factory=lambda: ["sequence"])
    """The column names in the assay records."""

    variables: dict[str, int | float | bool | str] = dataclasses.field(
        default_factory=dict
    )
    """The variables of the assay, defined in the manifest."""

    description: str | None = None
    """The description of the assay."""

    @property
    def sequence_feature_name(self) -> str:
        """Returns the sequence feature name in the assay records."""
        return self.columns[0]

    @property
    def target_feature_names(self) -> list[str]:
        """Returns the target feature names in the assay records."""
        # Get the target feature names from the columns
        # The first column is the sequence
        return list(self.columns[1:])

    def __contains__(self, item: "Assay") -> bool:
        """Implements the 'in' operator for Assay.

        If the given item is an Assay, checks if all its records and variables
        are contained in this assay.
        """
        if not isinstance(item, Assay):
            return False
        return set(item.records).issubset(self.records) and all(
            k in self.variables and self.variables[k] == v
            for k, v in item.variables.items()
        )

    def __repr__(self) -> str:
        """Return a string representation of the Assay object."""
        lines = [f"Assay(\n\tname='{self.name}',"]
        if self.description:
            desc = (
                self.description[:60] + "..."
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
        if len(self.records) > 3:
            n_recs = 3
        else:
            n_recs = len(self.records)
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

        df = pl.read_csv(section.path, columns=[section.sequence] + section.targets)
        df = df.with_columns(
            # Sequences are created from sequence strings present in the file
            # The sequence name is taken from the string itself as the name is not
            # provided in the assay file.
            pl.col(section.sequence)
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

        # df = df.with_columns(
        #     # Create a dict of target_name: target_value for each record
        #     pl.struct(section.targets)
        # )
        # Get the records as a list of tuples of (Sequence, target, target, ...)
        records = list(df.select("sequence_object", *section.targets).iter_rows())

        return cls(
            name=section.name or section.path.stem,
            records=records,
            columns=[section.sequence] + section.targets,
            description=section.description,
            variables=section.variables,
        )

    def as_manifest_section(self, *, path: Path) -> AssayManifestSection:
        """Create `AssayManifestSection` from the assay.

        Args:
            path (Path): The path to the assay file.

        Returns:
            AssayManifestSection: The manifest section for the assay.
        """

        # Get the sequence alphabet from the first record
        if not self.records:
            sequence_alphabet = SequenceAlphabet.AA
        else:
            sequence_alphabet = self.records[0][0].alphabet
        return AssayManifestSection(
            name=self.name,
            description=self.description,
            sequence=self.sequence_feature_name,
            sequence_alphabet=sequence_alphabet,
            targets=self.target_feature_names,
            variables=self.variables,
            path=path,
        )

    def dump(
        self, *, path: Path | None = None, format: AssayFormat = AssayFormat.CSV
    ) -> Path:
        """Dump the assay data to a file.

        Supported formats:
        - CSV (.csv)

        Args:
            path (Path): The output directory to dump the assay file in. If
                None, the current working directory is used.
            format (AssayFormat): The file format

        Raises:
            NotImplementedError if the file type is not supported.
        """

        path = path or Path.cwd()
        if path.is_dir():
            path = path / f"{self.name}{format.value}"

        rows = []
        for record in self.records:
            row = [str(record[0].value)]
            for target_value in record[1:]:
                row.append(target_value)
            rows.append(row)

        df = pl.DataFrame(rows, schema=self.columns, orient="row")

        match format:
            case AssayFormat.CSV:
                df.write_csv(path)
            case _:
                raise NotImplementedError(f"Unsupported file type: {format.value}")
        return path

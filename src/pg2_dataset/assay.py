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

from pg2_dataset.sequence import Sequence, SequenceAlphabet


class AssayFormat(StrEnum):
    """Supported assay file formats."""

    CSV = ".csv"
    """A comma separated text file"""


class AssayCondition(BaseModel):
    """Definition of an assay condition."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The name of the condition."""

    unit: str | None = None
    """The unit of the condition."""

    value: bool | int | float | str | None = None
    """The value of the condition, can be a bool, int, float, or str."""

    description: str | None = None
    """Description of the condition."""


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

    target: str = "target"
    """The target feature name given in the file."""

    conditions: dict[str, bool | int | float | str] = Field(default_factory=dict)
    """The condition key:value pairs, key is the name of the assay condition (defined in
    dataset manifest and value of the condition."""

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
        for v in (self.sequence, self.target):
            if v not in header:
                raise ValueError(f"Feature '{v}' not found in the file: {self.path}")
        return self

    @field_serializer("sequence_alphabet")
    def serialize_sequence_alphabet(self, sequence_alphabet: SequenceAlphabet) -> str:
        """Serialize the sequence alphabet as a string."""
        return sequence_alphabet.value


class Assay(BaseModel):
    """An assay in the dataset."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The name of the assay."""

    records: list[tuple[Sequence, int | float | bool | str]]
    """The records of the assay, pairs of Sequence and target values."""

    sequence_alphabet: SequenceAlphabet

    conditions: dict[str, int | float | bool | str] = Field(default_factory=dict)
    """The conditions of the assay, defined in the manifest."""

    description: str | None = None
    """The description of the assay."""

    sequence_feature_name: str = "sequence"
    """The sequence feature name in the assay records."""

    target_feature_name: str = "target"
    """The target feature name in the assay records."""

    @classmethod
    def from_manifest_section(cls, section: AssayManifestSection) -> "Assay":
        """Create an Assay instance from a manifest section."""

        df = pl.read_csv(section.path, columns=[section.sequence, section.target])
        df = df.with_columns(
            # Sequences are created from sequence strings present in the file
            # The sequence name is taken from the string itself as the name is not
            # provided in the assay file.
            pl.col(section.sequence).map_elements(
                lambda seq: Sequence(
                    name=seq, value=Seq(seq), alphabet=section.sequence_alphabet
                ),
                return_dtype=pl.Object,
            )
        )

        return cls(
            name=section.name or section.path.stem,
            records=list(df.iter_rows()),
            sequence_alphabet=section.sequence_alphabet,
            description=section.description,
            conditions=section.conditions,
        )

    def as_manifest_section(self, *, path: Path) -> AssayManifestSection:
        """Create `AssayManifestSection` from the assay.

        Args:
            path (Path): The path to the assay file.

        Returns:
            AssayManifestSection: The manifest section for the assay.
        """

        return AssayManifestSection(
            name=self.name,
            description=self.description,
            sequence=self.sequence_feature_name,
            sequence_alphabet=self.sequence_alphabet,
            target=self.target_feature_name,
            conditions=self.conditions,
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
        df = pl.DataFrame(
            self.records,
            schema=[self.sequence_feature_name, self.target_feature_name],
            orient="row",
        )
        df = df.with_columns(
            # The sequence column is converted to string for saving
            # it to tabular text format.
            pl.col(self.sequence_feature_name).map_elements(
                lambda seq: str(seq.value), return_dtype=pl.String
            )
        )
        match format:
            case AssayFormat.CSV:
                df.write_csv(path)
            case _:
                raise NotImplementedError(f"Unsupported file type: {format.value}")
        return path

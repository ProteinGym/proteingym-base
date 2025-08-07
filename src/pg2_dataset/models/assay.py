from enum import StrEnum
from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class AssayDataType(StrEnum):
    """Supported assay data types."""

    CATEGORICAL = "categorical"
    NUMERICAL = "numerical"
    BOOLEAN = "boolean"


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

    type: AssayDataType
    """The data type of the condition."""

    value: int | float | bool | str | None = None
    """The value of the condition, can be a any type."""

    description: str | None = None
    """Optional description of the condition."""

    @field_serializer("type")
    def serialize_type(self, type: AssayDataType) -> str:
        return type.value

    @classmethod
    def assign_from_name(
        cls, name: str, available_conditions: list["AssayCondition"]
    ) -> "AssayCondition":
        """Auto-assign conditions based on the name."""
        for condition in available_conditions:
            if condition.name == name:
                return condition.model_copy(deep=True)
        raise ValueError(f"Condition '{name}' not found in available conditions.")


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

    description: str | None = None
    """Description of the assay."""

    sequence: str
    """The sequence feature name given in the file."""

    target: str
    """The target feature name given in the file."""

    conditions: dict[str, int | float | bool | str] = {}
    """The condition key:value pairs, key is the name of the assay condition (defined in
    dataset manifest and value of the condition."""

    path: Path
    """The path to the assay file, csv only."""

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        """Serialize the path as a Posix path."""
        return path.as_posix()


class AssayFormat(StrEnum):
    """Supported assay file formats."""

    CSV = ".csv"


class Assay(BaseModel):
    """An assay in the dataset."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str | None = None
    """The name of the assay."""

    records: list[tuple[str, int | float | bool | str]]
    """The records of the assay, pairs of Sequence and target values."""

    sequence: str = "sequence"
    """The sequence feature name in the assay records."""

    target: str = "target"
    """The target feature name in the assay records."""

    conditions: list[AssayCondition] = Field(default_factory=list)
    """The conditions of the assay, defined in the manifest."""

    description: str | None = None
    """The description of the assay."""

    @classmethod
    def from_manifest_section(
        cls, section: AssayManifestSection, conditions: list[AssayCondition]
    ) -> "Assay":
        """Create an Assay instance from a manifest section."""
        df = pl.read_csv(section.path)
        if section.sequence not in df.columns:
            return ValueError(
                f"Sequence column '{section.sequence}' not found in the file."
            )
        if section.target not in df.columns:
            return ValueError(
                f"Target column '{section.target}' not found in the file."
            )
        records = []
        for row in df.iter_rows(named=True):
            records.append((row[section.sequence], row[section.target]))

        assay_conditions = []
        for condition_name, condition_value in section.conditions.items():
            try:
                condition = AssayCondition.assign_from_name(condition_name, conditions)
                condition.value = condition_value
                assay_conditions.append(condition)
            except ValueError as err:
                raise err
        return cls(
            name=section.description,
            sequence=section.sequence,
            target=section.target,
            records=records,
            description=section.description,
            conditions=assay_conditions,
        )

    def as_manifest_section(self, *, path: Path) -> AssayManifestSection:
        """Create `AssayManifestSection` from the assay.
        Args:
            path (Path): The path to the assay file.

        Returns:
            AssayManifestSection: The manifest section for the assay.
        """

        return AssayManifestSection(
            description=self.description,
            sequence=self.sequence,
            target=self.target,
            conditions={cond.name: cond.value for cond in self.conditions},
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
        df = pl.DataFrame(self.records, schema=[self.sequence, self.target]).transpose()
        match format:
            case AssayFormat.CSV:
                assay_path = path / f"{self.name}{format.value}"
                df.write_csv(assay_path)
            case _:
                raise NotImplementedError(f"Unsupported file type: {format.value}")
        return assay_path

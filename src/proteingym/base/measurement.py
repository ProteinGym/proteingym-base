"""The measurements on which the assays are based."""

import dataclasses
from enum import StrEnum
from pathlib import Path

import polars as pl
from pydantic import (
    BaseModel,
    ConfigDict,
    FilePath,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
)


class MeasurementsFormat(StrEnum):
    """Supported assay file formats."""

    CSV = ".csv"
    """A comma separated text file"""


@dataclasses.dataclass(kw_only=True, frozen=True)
class Field:
    """A measurement field in an assay.

    A field contains the metadata about a measurement, like the schema
    definition of a dataset.

    TODO
    ----
    Reuse this class across the code base.
    """

    name: str
    """The name of the field."""

    value: bool | int | float | str | None = None
    """The value of the field."""

    unit: str | None = None
    """The unit of the field."""

    description: str | None = None
    """Description of the field."""


class MeasurementsManifestSection(BaseModel):
    """The manifest section describing the measurements in an assay."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The assay name to which the measurements belong."""

    path: FilePath
    """The path to the assay file, csv only."""

    description: str | None = None
    """A brief description"""

    fields: list[Field]
    """The list of fields in the measurement manifest."""

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


@dataclasses.dataclass(kw_only=True, frozen=True)
class Measurements:
    """The measurements on which an assay is based."""

    name: str
    """The name of the measurement."""

    description: str | None = None
    """A brief description"""

    fields: list[Field] = dataclasses.field(default_factory=list)
    """The measurement fields."""

    records: list[tuple[str | int | float | bool | str, ...]] = dataclasses.field(
        default_factory=list
    )
    """The measurement records."""

    @classmethod
    def from_manifest_section(
        cls,
        section: MeasurementsManifestSection,
    ) -> "Measurements":
        """Creates Measurements from a manifest section.

        Args:
            section (MeasurementsManifestSection): The manifest section
                describing the measurements.

        Returns:
            Measurements: The created Measurements object.
        """
        columns = [field.name for field in section.fields]
        # Reusing polars as we already depend on it for assays
        records = list(pl.read_csv(section.path, columns=columns).iter_rows())
        return cls(
            name=section.name,
            records=records,
            fields=section.fields,
            description=section.description,
        )

    def as_manifest_section(self, *, path: Path) -> MeasurementsManifestSection:
        """Converts the Measurements to a manifest section.

        Args:
            path (Path): The path to the measurements file.

        Returns:
            MeasurementsManifestSection: The manifest section representing
            the measurements.
        """
        return MeasurementsManifestSection(
            name=self.name,
            path=path,
            description=self.description,
            fields=self.fields,
        )

    def dump(
        self,
        *,
        path: Path | None = None,
        fmt: MeasurementsFormat = MeasurementsFormat.CSV,
    ) -> Path:
        """Dump the measurements to a file.

        Args:
            path (Path, optional): The output directory to dump the measurements
                file in. If None, the current working directory is used.
            fmt (MeasurementsFormat, optional): The file format. Defaults to
                MeasurementsFormat.CSV.

        Raises:
            NotImplementedError if the file type is not supported.
        """
        path = path or Path.cwd()
        if path.is_dir():
            path = path / f"{self.name}{fmt.value}"

        df = pl.DataFrame(
            self.records,
            schema=[field.name for field in self.fields],  # TODO: Use units
        )
        match format:
            case MeasurementsFormat.CSV:
                df.write_csv(path)
            case _:
                raise NotImplementedError(f"Unsupported file type: {fmt.value}")
        return path

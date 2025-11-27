"""The measurements on which the assays are based."""

import dataclasses

from pydantic import BaseModel, ConfigDict, FilePath


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

    fields: list[Field]
    """The list of fields in the measurement manifest."""

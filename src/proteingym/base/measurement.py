"""The measurements on which the assays are based."""

import dataclasses


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

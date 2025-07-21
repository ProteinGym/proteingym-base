"""The protein structure of the dataset."""

from pydantic import BaseModel, Field


class Structure(BaseModel):
    """A protein structure in the dataset."""

    name: str
    """The name of the protein structure."""

    value: object
    """The value of the protein structure, typically a file path or binary data."""

    description: str | None = None
    """The description of the protein structure."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the protein structure."""

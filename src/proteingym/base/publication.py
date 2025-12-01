import re
from typing import Optional, Self

import requests
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class PublicationManifestSection(BaseModel):
    """Manifest section for publication information."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        use_attribute_docstrings=True,
    )

    doi: Optional[str] = None
    """The DOI of the publication."""

    title: Optional[str] = None
    """The title of the publication."""

    authors: Optional[str] = None
    """The authors of the publication."""

    journal: Optional[str] = None
    """The journal of the publication."""

    volume: Optional[str] = None
    """The volume of the publication."""

    number: Optional[str] = None
    """The number of the publication issue."""

    year: Optional[str] = None
    """The year of publication."""

    pages: Optional[str] = None
    """The pages of the publication."""

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("10."):
            raise ValueError("DOI must start with '10.'")
        return v

    @model_validator(mode="after")
    def _fill_from_doi(self) -> "PublicationManifestSection":
        """Fill missing fields from DOI if available."""
        if self.doi:
            try:
                response = requests.get(
                    f"https://dx.doi.org/{self.doi}",
                    headers={"Accept": "text/bibliography; style=bibtex"},
                    allow_redirects=True,
                    timeout=10
                )
                response.raise_for_status()
                response.encoding = 'utf-8'
                fields = re.findall(r'(\w+)=\{([^}]+)\}', response.text)
                queried_data = dict(fields)

                if not self.title and "title" in queried_data:
                    self.title = queried_data["title"]
                if not self.authors and "author" in queried_data:
                    self.authors = queried_data["author"]
                if not self.journal and "journal" in queried_data:
                    self.journal = queried_data["journal"]
                if not self.volume and "volume" in queried_data:
                    self.volume = queried_data["volume"]
                if not self.number and "number" in queried_data:
                    self.number = queried_data["number"]
                if not self.year and "year" in queried_data:
                    self.year = queried_data["year"]
                if not self.pages and "pages" in queried_data:
                    self.pages = queried_data["pages"]

            # if we get no 200 response,
            # we still make the dataset
            except Exception:
                pass
        return self


class Publication(BaseModel):
    """Publication information for a dataset."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )

    title: Optional[str] = None
    """The title of the publication."""

    authors: Optional[str] = None
    """The authors of the publication."""

    journal: Optional[str] = None
    """The journal of the publication."""

    volume: Optional[str] = None
    """The volume of the publication."""

    number: Optional[str] = None
    """The number of the publication issue."""

    year: Optional[str] = None
    """The year of publication."""

    pages: Optional[str] = None
    """The pages of the publication."""

    doi: Optional[str] = None
    """The DOI of the publication."""

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("10."):
            raise ValueError("DOI must start with '10.'")
        return v

    def as_manifest_section(self) -> PublicationManifestSection:
        """Convert the publication information to a manifest section.

        Args:
            path (Path): The path to the publication file (as created by
                `method:dump`).

        Returns:
            PublicationManifestSection: The manifest section for the publication.
        """
        return PublicationManifestSection(
            doi=self.doi,
            title=self.title,
            authors=self.authors,
            journal=self.journal,
            volume=self.volume,
            number=self.number,
            year=self.year,
            pages=self.pages,
        )

    @classmethod
    def from_manifest_section(
        cls, section: PublicationManifestSection) -> Self:
        """Create a Publication instance from a manifest section."""
        return cls(**section.model_dump(exclude_none=True))

    def __repr__(self) -> str:
        """Return a string representation of the Publication object."""
        def _truncate(value: Optional[str]) -> str:
            return value[:60] + "..." if value and len(value) > 60 else value

        fields = [
            'title', 'authors', 'doi', 'journal',
            'volume', 'number', 'year', 'pages']
        lines = ["Publication("] + [
            f"\t{field}: {_truncate(getattr(self, field)) or 'None'}, "
            for field in fields
        ]
        return "\n".join(lines) + "\n)"

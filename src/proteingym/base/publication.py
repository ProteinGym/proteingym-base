import dataclasses
import re

import requests


@dataclasses.dataclass(kw_only=True, frozen=False)
class Publication():
    title: str | None = None
    """The title of the publication."""

    authors: str | None = None
    """The authors of the publication."""

    journal: str | None = None
    """The journal of the publication."""

    volume: str | None = None
    """The volume of the publication."""

    number: str | None = None
    """The number of the publication issue."""

    year: str | None = None
    """The year of publication."""

    pages: str | None = None
    """The pages of the publication."""

    doi: str | None = None
    """The DOI of the publication."""

    def fill_from_database(self) -> "Publication":
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

            # Do we actual raise the error
            # if we fill_from_db() manually?
            except Exception:
                pass
        return self

    def __repr__(self) -> str:
        """Return a string representation of the Publication object."""
        def _truncate(value: str | None) -> str:
            return value[:60] + "..." if value and len(value) > 60 else value

        fields = [
            'title', 'authors', 'doi', 'journal',
            'volume', 'number', 'year', 'pages']
        lines = ["Publication("] + [
            f"\t{field}: {_truncate(getattr(self, field)) or 'None'}, "
            for field in fields
        ]
        return "\n".join(lines) + "\n)"

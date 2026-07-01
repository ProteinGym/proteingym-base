import dataclasses
import re

import requests

from .lookup_field import LookupField


class DoiField(LookupField):
    """Query publication data from dx.doi.org."""

    identifier = "doi"

    def resolve(self, id_: str):
        response = requests.get(
            f"https://dx.doi.org/{id_}",
            headers={"Accept": "text/bibliography; style=bibtex"},
            allow_redirects=True,
            timeout=10,
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        fields = re.findall(r"(\w+)={([^}]+)}", response.text)
        queried_data = dict(fields)
        # DOI returns more, e.g. ISSNs, editors, types
        # Accepted keys follows APA entries
        accepted_keys = [
            "title",
            "author",
            "journal",
            "volume",
            "number",
            "year",
            "pages",
        ]
        return {k: v for k, v in queried_data.items() if k in accepted_keys}


@dataclasses.dataclass(kw_only=True, frozen=False)
class Publication:
    """Metadata about a publication."""

    # pyrefly: ignore[bad-assignment]
    title: str | None = dataclasses.field(default=DoiField())
    """The title of the publication."""

    # pyrefly: ignore[bad-assignment]
    author: str | None = dataclasses.field(default=DoiField())
    """The authors of the publication."""
    # singular since DOI returns author key

    # pyrefly: ignore[bad-assignment]
    journal: str | None = dataclasses.field(default=DoiField())
    """The journal of the publication."""

    # pyrefly: ignore[bad-assignment]
    volume: str | None = dataclasses.field(default=DoiField())
    """The volume of the publication."""

    # pyrefly: ignore[bad-assignment]
    number: str | None = dataclasses.field(default=DoiField())
    """The number of the publication issue."""

    # pyrefly: ignore[bad-assignment]
    year: str | None = dataclasses.field(default=DoiField())
    """The year of publication."""

    # pyrefly: ignore[bad-assignment]
    pages: str | None = dataclasses.field(default=DoiField())
    """The pages of the publication."""

    doi: str | None = None
    """The DOI of the publication."""

    def __repr__(self) -> str:
        """Return a string representation of the Publication object."""

        def _truncate(value: str) -> str:
            return value[:60] + "..." if value and len(value) > 60 else value

        fields = [
            "title",
            "author",
            "journal",
            "volume",
            "number",
            "year",
            "pages",
            "doi",
        ]
        lines = ["Publication("] + [
            f"\t{field}: {_truncate(getattr(self, field)) or 'None'}, "
            for field in fields
        ]
        return "\n".join(lines) + "\n)"

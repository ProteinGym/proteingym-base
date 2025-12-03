import dataclasses
import re

import requests


@dataclasses.dataclass(kw_only=True, frozen=False)
class Publication:
    title: str | None = None
    """The title of the publication."""

    author: str | None = None
    """The authors of the publication."""
    # singular since DOI returns author key

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

    def fill_from_database(self, overwrite: bool = False) -> "Publication":
        """Fill missing fields from DOI if available."""
        data = dataclasses.asdict(self)
        if self.doi:
            response = requests.get(
                f"https://dx.doi.org/{self.doi}",
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

            if overwrite:
                data.update(
                    **{k: v for k, v in queried_data.items() if k in accepted_keys}
                )
            else:
                data.update(
                    **{
                        k: v
                        for k, v in queried_data.items()
                        if k in accepted_keys and data.get(k) is None
                    }
                )

        return self.__class__(**data)

    def __repr__(self) -> str:
        """Return a string representation of the Publication object."""

        def _truncate(value: str | None) -> str:
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

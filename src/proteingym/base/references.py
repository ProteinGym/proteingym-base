import re
from typing import Literal, Union

import requests
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import core_schema


class XrefManager(BaseModel):
    """Base class for external reference managers."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )

    identifier: str
    """The identifier in the external database."""


class DOIXref(XrefManager):
    """DOI reference manager."""

    database: Literal["doi"] = "doi"

    @field_validator("identifier")
    @classmethod
    def _validate_doi(cls, v: str) -> str:
        if not v.startswith("10."):
            raise ValueError("DOI must start with '10.'")
        return v

    def get_bibliography(self) -> dict:
        """Get structured publication data from DOI API"""
        response = requests.get(
            f"http://dx.doi.org/{self.identifier}",
            headers = {"Accept": "text/bibliography; style=bibtex"},
            allow_redirects=True
        )
        fields = re.findall(r'(\w+)=\{([^}]+)\}', response.text)
        return dict(fields)


class UniProtXref(XrefManager):
    """UniProt reference manager."""

    database: Literal["uniprot"] = "uniprot"

    def get_metadata(self) -> dict:
        """Get structured metadata from UniProt API."""
        response = requests.get(
            f"https://rest.uniprot.org/uniprotkb/{self.identifier}",
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()

Xref = Union[DOIXref, UniProtXref]


class XrefCollection(list[Xref]):
    """Collection of external references with convenient access."""

    def __getattr__(self, name: str) -> Xref | None:
        """Get first reference by database name."""
        for xref in self:
            if xref.database == name:
                return xref
        return None

    def get_all(self, database: str) -> list[Xref]:
        """Get all references for a database."""
        return [xref for xref in self if xref.database == database]

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic core schema for XrefCollection."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.list_schema(handler(Xref))
        )

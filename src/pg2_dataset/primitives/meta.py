import tomllib
from functools import cached_property
from itertools import chain
from pathlib import Path

from pydantic import BaseModel, Field, FiniteFloat, computed_field

ENGINEERING_ROUND = "engineering_round"
SEQUENCE = "sequence"
SPLIT = "split"


class Resources(BaseModel):
    records: str | None = None
    structure: str | None = None
    msa: str | None = None


class AssayMeta(BaseModel, extra="allow"):
    description: str = ""
    features: list[str] = Field(default_factory=list)
    constants: dict[str, FiniteFloat | str] = Field(default_factory=dict)


class RecordsMeta(BaseModel):
    sequence_feature: str = Field(default=SEQUENCE, min_length=1)
    engineering_round_feature: str = ""
    split_feature: str = ""
    assays: dict[str, AssayMeta] = Field(default_factory=dict)

    @computed_field
    @cached_property
    def columns(self) -> list[str]:
        # TODO: may need to split this to X-columns and Y-columns
        return sorted(
            e
            for e in [
                self.sequence_feature,
                self.engineering_round_feature,
                self.split_feature,
                *self.assays,
                *chain.from_iterable(e.features for e in self.assays.values()),
            ]
            if e
        )


class StructuresMeta(BaseModel):
    structure_file_path: str = Field(default=str)
    structures: list[str] = Field(default_factory=list)


class Metadata(BaseModel):
    name: str = ""
    description: str = ""
    doi: str = ""
    source: str = ""
    xref: str = ""


class DatasetMeta(BaseModel):
    resources: Resources | None = None
    records: RecordsMeta | None = None
    structures: StructuresMeta | None = None
    metadata: Metadata | None = None

    @classmethod
    def parse_toml(cls, toml_file: Path | str):
        with open(toml_file, "rb") as fh:
            return cls.model_validate(tomllib.load(fh))

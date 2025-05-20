from pathlib import Path

import tomllib
from pydantic import BaseModel, Field, FiniteFloat

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
    columns: list[str] = Field(default_factory=list)
    assays: dict[str, AssayMeta] = Field(default_factory=dict)


class Metadata(BaseModel):
    name: str = ""
    description: str = ""
    doi: str = ""
    source: str = ""
    xref: str = ""


class DatasetSettings(BaseModel):
    resources: Resources | None = None
    records: RecordsMeta | None = None
    metadata: Metadata | None = None

    @classmethod
    def parse_toml(cls, toml_file: Path | str):
        with open(toml_file, "rb") as fh:
            return cls.model_validate(tomllib.load(fh))

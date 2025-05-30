"""Models for data that we store in toml file."""

from collections.abc import Collection
from functools import cached_property
from itertools import chain
from pathlib import Path
from typing import IO, Self

import toml
from pydantic import BaseModel, Field, FiniteFloat, computed_field

ENGINEERING_ROUND = "engineering_round"
SEQUENCE = "sequence"
SPLIT = "split"


class SingleAssayMeta(BaseModel, extra="allow"):
    description: str = ""
    features: list[str] = Field(default_factory=list)
    constants: dict[str, FiniteFloat | str] = Field(default_factory=dict)


class AssaysMeta(BaseModel):
    file_path: str = ""
    sequence_feature: str = Field(default=SEQUENCE, min_length=1)
    engineering_round_feature: str = ""
    split_feature: str = ""
    assays: dict[str, SingleAssayMeta] = Field(default_factory=dict)

    def features_for_targets(self, targets: Collection[str]) -> list[str]:
        return sorted(chain.from_iterable(self.assays[e].features for e in targets))

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
    file_path: str = ""


class DatasetMeta(BaseModel):
    name: str = ""
    description: str = ""
    doi: str = ""
    source: str = ""
    xref: str = ""
    assays_meta: AssaysMeta | None = None
    structures_meta: StructuresMeta | None = None

    @classmethod
    def from_toml(cls, toml_file: Path | str | IO["str"]) -> Self:
        if isinstance(toml_file, str):
            toml_file = Path(toml_file)
        return cls.model_validate(toml.load(toml_file))
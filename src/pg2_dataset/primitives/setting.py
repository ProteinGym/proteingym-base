from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    TomlConfigSettingsSource,
)

ENGINEERING_ROUND = "engineering_round"
SEQUENCE = "sequence"
SPLIT = "split"


class Resources(BaseModel):
    records: str | None = None
    structure: str | None = None
    msa: str | None = None


class RecordsMeta(BaseModel):
    sequence_feature: str = SEQUENCE
    engineering_round_feature: str = ""
    split_feature: str = ""

    columns: list[str] = Field(default_factory=list)


class Metadata(BaseModel):
    name: str | None = None
    description: str | None = None
    doi: str | None = None
    source: str | None = None
    xref: str | None = None


class Assay(BaseModel, extra="allow"):
    name: str | None = None
    description: str | None = None
    features: list[str] = Field(default_factory=list)
    target: str | None = None
    constants: dict[str, Any] = Field(default_factory=dict)


class DatasetSettings(BaseSettings):
    _toml_file: str | None = None

    resources: Resources | None = None
    records: RecordsMeta | None = None
    metadata: Metadata | None = None
    assays: dict[str, Assay] = Field(default_factory=dict)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = (init_settings, env_settings, dotenv_settings, file_secret_settings)

        # FIXME: this is always true - `self`?
        if cls._toml_file:
            sources = sources + (
                TomlConfigSettingsSource(settings_cls, toml_file=cls._toml_file),
            )

        return sources

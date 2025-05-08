from typing import Tuple, Type

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, TomlConfigSettingsSource


class Artifacts(BaseModel):
    records: str | None = None
    structure: str | None = None
    msa: str | None = None


class Records(BaseModel):
    features: list[str] = []
    targets: list[str] = []

    sequence_feature: str | None = None
    engineering_round_feature: str | None = None

    columns: list[str] = []
    schemas: list[str] = []

    @model_validator(mode="after")
    def check_schemas_should_not_exist_without_columns(self):
        if self.schemas and not self.columns:
            raise ValueError(f"schemas {self.schemas} should not exist without columns.")
        else:
            return self


class DatasetSettings(BaseSettings):
    _toml_file: str | None = None

    artifacts: Artifacts
    records: Records

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        sources = (init_settings, env_settings, dotenv_settings, file_secret_settings)

        if cls._toml_file:
            sources = sources + (TomlConfigSettingsSource(settings_cls, toml_file=cls._toml_file),)

        return sources

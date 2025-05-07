from typing import Tuple, Type

from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, TomlConfigSettingsSource


class Artifacts(BaseModel):
    records: str | None = None
    structure: str | None = None
    msa: str | None = None


class DatasetSettings(BaseSettings):
    _toml_file: str | None = None

    artifacts: Artifacts

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

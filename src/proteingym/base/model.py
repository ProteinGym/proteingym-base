from pathlib import Path
from typing import Any, Self

import frontmatter
from pydantic import BaseModel, ConfigDict, Field


class ModelCard(BaseModel):
    """A model card representing configuration for a machine learning model
    in the proteingym space.

    This class loads and validates model configuration from markdown files, containing
    model metadata and hyperparameters in the front matter for benchmarking tasks.

    The model allows extra fields beyond the defined attributes to accommodate
    varying model configurations.
    """

    model_config = ConfigDict(extra="allow")

    name: str
    """The name of the model."""

    hyper_params: dict[str, Any] = Field(default_factory=dict)
    """Dictionary containing model hyperparameters and configuration."""

    @classmethod
    def from_path(cls, path: Path) -> Self:
        with path.open("r", encoding="utf-8") as file:
            model_card = frontmatter.load(file)

        return cls.model_validate(model_card.metadata)

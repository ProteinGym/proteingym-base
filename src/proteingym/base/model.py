import inspect
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any, Generator, Self

import frontmatter
import toml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)


class ModelCard(BaseModel):
    """A model card representing configuration for a protein language model.

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


@dataclass
class EntryPoint:
    """Represents a model entry point with its name and parameters."""

    name: str
    """The name of the entry point function or command."""

    params: list[str] = field(default_factory=list)
    """List of parameter names that the entry point accepts."""


class ProjectSection(BaseModel):
    """Represents the project section of a pyproject.toml file."""

    name: str = Field(min_length=1)
    """The name of the project as defined in pyproject.toml."""


class ModelProject(BaseModel):
    """A model project containing configuration and entry points.

    This class loads and validates model project configuration from a project
    directory, validating the pyproject.toml file and discovering entry points
    for benchmarking tasks.
    """

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
    )

    project: ProjectSection
    """The project configuration section containing metadata from pyproject.toml."""

    @computed_field
    @property
    def entry_points(self) -> list[EntryPoint]:
        """Discover entry points for the project based on project_name."""

        console_scripts = [
            ep
            for ep in metadata.entry_points()
            if ep.dist.name == self.project.name and ep.group == "console_scripts"
        ]

        entry_points = []
        entry_points.extend(self._filter_entry_points(*console_scripts))

        return entry_points

    def _filter_entry_points(
        self, *entry_points: metadata.EntryPoint
    ) -> Generator[EntryPoint, None, None]:
        """Filter and extract entry points from metadata entry points."""
        for ep in entry_points:
            app = ep.load()
            is_entry_point = hasattr(app, "registered_commands")

            if not is_entry_point:
                continue

            for command in app.registered_commands:
                sig = inspect.signature(command.callback)
                entry_point = EntryPoint(
                    name=command.callback.__name__,
                    params=list(sig.parameters.keys()),
                )
                yield entry_point

    @model_validator(mode="after")
    def _validate_entry_points_exist(self) -> "ModelProject":
        if len(self.entry_points) == 0:
            raise ValueError(f"No entry points found for {self.project.name}")
        return self

    @classmethod
    def from_path(cls, path: Path) -> "ModelProject":
        """Create a ModelProject from a project directory path.

        Loads and validates the pyproject.toml file from the specified directory,
        then automatically discovers console script entry points for the project.

        Args:
            path: The root path to the model project directory

        Returns:
            ModelProject: The validated model project with discovered entry points

        Raises:
            ValueError: If pyproject.toml is missing, invalid, or no entry points found
        """
        pyproject_path = path / "pyproject.toml"

        if not pyproject_path.exists():
            raise ValueError(f"pyproject.toml not found at: {pyproject_path}")

        project_data = toml.load(pyproject_path)

        return cls(**project_data)

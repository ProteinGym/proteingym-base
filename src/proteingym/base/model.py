import inspect
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any, Generator, Self

import frontmatter
import toml
from pydantic import BaseModel, ConfigDict, Field, computed_field


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


class ModelProject(BaseModel):
    """A model project containing configuration and entry points.

    This class loads and validates model project configuration from a project
    directory, validating the pyproject.toml file and discovering entry points
    for benchmarking tasks.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    project_path: Path
    """The root path to the model project directory
    containing pyproject.toml and model configuration.
    """

    @computed_field
    @property
    def pyproject_path(self) -> Path:
        """Default path to the pyproject.toml file relative to the project path."""
        return self.project_path / "pyproject.toml"

    @computed_field
    @property
    def model_card_path(self) -> Path:
        """Default path to the model card file relative to the project path."""
        return self.project_path / "README.md"

    @computed_field
    @property
    def project_name(self) -> str:
        """Project name extracted from pyproject.toml with validation."""
        project_data = toml.load(self.pyproject_path)

        # Check if file contains a project header
        if "project" not in project_data:
            raise ValueError(
                f"File does not contain a project header: {self.pyproject_path}"
            )

        # Check if the project header contains a name
        project_section = project_data["project"]
        if not isinstance(project_section, dict):
            raise ValueError(
                f"Project header is not a valid dictionary: {self.pyproject_path}"
            )

        if "name" not in project_section:
            raise ValueError(
                f"The project header does not contain a name: {self.pyproject_path}"
            )

        project_name = project_section["name"]
        if not isinstance(project_name, str) or not project_name.strip():
            raise ValueError(
                f"Project name is not a valid non-empty string: {self.pyproject_path}"
            )

        return project_name

    def _filter_typer_entry_points(
        self, *entry_points: metadata.EntryPoint
    ) -> Generator[EntryPoint, None, None]:
        """Filter and extract typer entry points from metadata entry points."""
        for ep in entry_points:
            app = ep.load()
            is_typer_entry_point = hasattr(app, "registered_commands")

            if not is_typer_entry_point:
                continue

            for command in app.registered_commands:
                sig = inspect.signature(command.callback)
                entry_point = EntryPoint(
                    name=command.callback.__name__,
                    params=list(sig.parameters.keys()),
                )
                yield entry_point

    @computed_field
    @property
    def entry_points(self) -> list[EntryPoint]:
        """Discover entry points for the project based on project_name."""

        # Filter by package name and group
        console_scripts = [
            ep
            for ep in metadata.entry_points()
            if ep.dist.name == self.project_name and ep.group == "console_scripts"
        ]

        entry_points = []
        entry_points.extend(self._filter_typer_entry_points(*console_scripts))

        return entry_points

    @classmethod
    def from_path(cls, project_path: Path) -> "ModelProject":
        """Create a ModelProject from a project directory path.

        Validates the pyproject.toml file in the project directory and
        discovers available entry points via computed fields.

        Args:
            project_path: The root path to the model project directory

        Returns:
            ModelProject: The model project with validated configuration
                and entry points

        Raises:
            ValueError: If the project path or pyproject.toml validation fails
        """
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        # Create the instance - all validation and discovery happens via computed fields
        return cls(project_path=project_path)

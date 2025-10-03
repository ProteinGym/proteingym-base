from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from proteingym.base.__main__ import app
from proteingym.base.model import ModelCard, ModelProject


@pytest.fixture
def model_card_contents() -> str:
    return """
---
name: "dummy"

hyper_params:
    nogpu: false
---

# Model Card for Dummy
Some summary
"""


@pytest.fixture
def model_card_path(tmp_path: Path, model_card_contents: str) -> Path:
    """A (temporary) model card file."""
    model_card_file = tmp_path / "README.md"
    model_card_file.write_text(model_card_contents, encoding="utf-8")
    return model_card_file


def test_model_card_from_path(model_card_path: Path) -> None:
    """Happy flow for loading a model card from a file path."""
    try:
        ModelCard.from_path(model_card_path)
    except ValidationError as e:
        raise ValidationError("ValidationError raised") from e
    else:
        assert True, "Model card loaded successfully from path-like object."


def test_model_card_name(model_card_path: Path) -> None:
    try:
        model_card = ModelCard.from_path(model_card_path)
    except ValidationError as e:
        raise ValidationError("ValidationError raised") from e
    else:
        assert model_card.name == "dummy"


def test_manifest_hyper_params(model_card_path: Path) -> None:
    try:
        model_card = ModelCard.from_path(model_card_path)
    except ValidationError as e:
        raise ValidationError("ValidationError raised") from e
    else:
        assert not model_card.hyper_params["nogpu"]


@pytest.fixture
def runner() -> CliRunner:
    """Test runner for CLI commands."""
    return CliRunner()


@pytest.fixture
def valid_model_card_content() -> str:
    """Valid model card content for testing."""
    return """---
name: "test_model"
hyper_params:
    learning_rate: 0.001
    batch_size: 32
---

# Test Model
This is a test model card.
"""


@pytest.fixture
def valid_pyproject_content() -> str:
    """Valid pyproject.toml content for testing."""
    return """[project]
name = "test_model"
version = "1.0.0"
description = "Test model package"
"""


@pytest.fixture
def empty_pyproject_content_missing_project() -> str:
    """Invalid pyproject.toml content for testing."""
    return """[build-system]
requires = ["setuptools"]
# Missing [project] section
"""


@pytest.fixture
def empty_pyproject_content_missing_name() -> str:
    """Invalid pyproject.toml content for testing."""
    return """[project]
version = "1.0.0"
description = "Test model package"
# Missing name
"""


@pytest.fixture
def empty_pyproject_content_empty_name() -> str:
    """Invalid pyproject.toml content for testing."""
    return """[project]
name = ""
version = "1.0.0"
description = "Test model package"
# Missing name
"""


@pytest.fixture
def model_project(request, tmp_path: Path) -> Path:
    """Indirect fixture that creates model projects with specified content."""
    model_card_fixture_name, pyproject_fixture_name, project_name = request.param

    # Get the actual content from the fixture names
    model_card_content = request.getfixturevalue(model_card_fixture_name)
    pyproject_content = request.getfixturevalue(pyproject_fixture_name)

    project_dir = tmp_path / project_name
    project_dir.mkdir(parents=True)

    # Create the model card file
    (project_dir / "README.md").write_text(model_card_content)
    # Create the pyproject.toml file
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    return project_dir


@pytest.fixture
def mock_valid_entry_points():
    """Context manager fixture for mocking valid entry points."""
    mock_ep = Mock()
    mock_ep.dist.name = "test_model"
    mock_ep.group = "console_scripts"

    mock_app = Mock()
    mock_command = Mock()
    mock_command.callback.__name__ = "train"

    def mock_train_func():
        pass

    mock_command.callback = mock_train_func
    mock_app.registered_commands = [mock_command]
    mock_ep.load.return_value = mock_app

    return patch("proteingym.base.model.metadata.entry_points", return_value=[mock_ep])


@pytest.fixture
def mock_empty_entry_points():
    """Mock empty entry points."""
    mock_ep = Mock()
    mock_ep.dist.name = "test_model"
    mock_ep.group = "console_scripts"

    mock_app = Mock()
    del mock_app.registered_commands
    mock_ep.load.return_value = mock_app

    return patch("proteingym.base.model.metadata.entry_points", return_value=[mock_ep])


@pytest.mark.parametrize(
    "model_project",
    [
        ("valid_model_card_content", "valid_pyproject_content", "test_model"),
    ],
    indirect=True,
)
def test_validation_success(
    model_project: Path,
    mock_valid_entry_points,
    runner: CliRunner,
):
    """Test successful model validation with valid entry points and model card."""
    with mock_valid_entry_points:
        result = runner.invoke(app, ["validate", str(model_project)])

        assert result.exit_code == 0
        assert (
            "✅ Model test_model loaded successfully with entry points:"
            in result.stdout
        )
        assert "✅ Loaded test_model with hyper parameters" in result.stdout


def test_validation_missing_project_directory(runner: CliRunner):
    """Test validation when project directory doesn't exist."""
    nonexistent_project = "nonexistent_model"

    result = runner.invoke(app, ["validate", str(nonexistent_project)])

    # Typer returns exit code 2 for parameter validation errors
    assert result.exit_code == 2


@pytest.mark.parametrize(
    "model_project",
    [
        (
            "valid_model_card_content",
            "empty_pyproject_content_missing_project",
            "test_model",
        ),
    ],
    indirect=True,
)
def test_validation_pyproject_missing_project_section(
    model_project: Path,
    runner: CliRunner,
):
    """Test validation when pyproject.toml is missing [project] section."""
    result = runner.invoke(app, ["validate", str(model_project)])

    assert result.exit_code == 1
    assert "❌ Validation failed: 1 validation error for ModelProject" in result.stderr


@pytest.mark.parametrize(
    "model_project",
    [
        (
            "valid_model_card_content",
            "empty_pyproject_content_missing_name",
            "test_model",
        ),
    ],
    indirect=True,
)
def test_validation_pyproject_missing_name(
    model_project: Path,
    runner: CliRunner,
):
    """Test validation when pyproject.toml is missing name under [project] section."""
    result = runner.invoke(app, ["validate", str(model_project)])

    assert result.exit_code == 1
    assert "❌ Validation failed: 1 validation error for ModelProject" in result.stderr


def test_model_project_from_path_nonexistent():
    """Test ModelProject.from_path with non-existent path."""
    with pytest.raises(ValueError, match=r".*pyproject.toml not found.*"):
        ModelProject.from_path(Path("nonexistent_project"))


@pytest.mark.parametrize(
    "model_project",
    [
        ("valid_model_card_content", "valid_pyproject_content", "test_model"),
    ],
    indirect=True,
)
def test_validation_empty_entry_points(
    model_project: Path,
    mock_empty_entry_points,
):
    with mock_empty_entry_points:
        with pytest.raises(ValueError, match=r".*No entry points found.*"):
            _ = ModelProject.from_path(model_project)


@pytest.mark.parametrize(
    "model_project",
    [
        (
            "valid_model_card_content",
            "empty_pyproject_content_empty_name",
            "test_model",
        ),
    ],
    indirect=True,
)
def test_validation_pyproject_empty_name(
    model_project: Path,
    mock_valid_entry_points,
):
    with mock_valid_entry_points:
        with pytest.raises(ValueError, match=r".*project name is empty.*"):
            _ = ModelProject.from_path(model_project)

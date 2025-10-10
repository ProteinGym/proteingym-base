import json
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

hyper_parameters:
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


def test_manifest_hyper_parameters(model_card_path: Path) -> None:
    try:
        model_card = ModelCard.from_path(model_card_path)
    except ValidationError as e:
        raise ValidationError("ValidationError raised") from e
    else:
        assert not model_card.hyper_parameters["nogpu"]


@pytest.fixture
def runner() -> CliRunner:
    """Test runner for CLI commands."""
    return CliRunner()


@pytest.fixture
def valid_model_card_content() -> str:
    """Valid model card content for testing."""
    return """---
name: "test_model"
hyper_parameters:
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
        ("valid_model_card_content", "valid_pyproject_content", "test_model"),
    ],
    indirect=True,
)
def test_validation_general_exception_handling(
    model_project: Path,
    runner: CliRunner,
):
    """Test validation handles general exceptions with proper logging."""
    with patch("proteingym.base.model.ModelProject.from_path") as mock_from_path:
        mock_from_path.side_effect = RuntimeError("Unexpected error occurred")

        result = runner.invoke(app, ["-vv", "validate", str(model_project)])

        assert result.exit_code == 1
        assert "❌ Error running validation" in result.stderr


def test_list_models_command(runner: CliRunner, model_card_path: Path) -> None:
    """Test the list-models CLI command."""
    result = runner.invoke(app, ["list-models", str(model_card_path)])

    assert result.exit_code == 0

    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 1

    model_data = output_data[0]
    assert model_data["name"] == "dummy"
    assert "input_filename" in model_data
    assert model_data["hyper_parameters"]["nogpu"] is False


def test_list_models_directory_with_multiple_cards(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Test list-models with a directory containing multiple model cards."""
    model1 = tmp_path / "model1.md"
    model1.write_text(
        """
---
name: "model_one"
hyper_parameters:
    learning_rate: 0.001
---

# Model One
First model description
""",
        encoding="utf-8",
    )

    model2 = tmp_path / "model2.md"
    model2.write_text(
        """
---
name: "model_two"
hyper_parameters:
    learning_rate: 0.001
---

# Model Two
Second model description
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["list-models", str(tmp_path)])

    assert result.exit_code == 0
    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 2

    model_names = [model["name"] for model in output_data]
    assert "model_one" in model_names
    assert "model_two" in model_names


def test_list_models_directory_empty(runner: CliRunner, tmp_path: Path) -> None:
    """Test list-models with a directory containing no model cards."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = runner.invoke(app, ["list-models", str(empty_dir)])

    assert result.exit_code == 0
    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 0


def test_list_models_mixed_valid_invalid(runner: CliRunner, tmp_path: Path) -> None:
    """Test list-models with a directory
    containing both valid and invalid model cards."""
    valid_card = tmp_path / "valid.md"
    valid_card.write_text(
        """
---
name: "valid_model"
---

# Valid Model
This is a valid model card
""",
        encoding="utf-8",
    )

    invalid_file = tmp_path / "invalid.md"
    invalid_file.write_text("This is just a regular markdown file", encoding="utf-8")

    result = runner.invoke(app, ["list-models", str(tmp_path)])

    assert result.exit_code == 0
    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 1
    assert output_data[0]["name"] == "valid_model"


def test_list_models_validation_error(runner: CliRunner, tmp_path: Path) -> None:
    """Test list-models logs error message when skipping invalid model card."""
    invalid_card = tmp_path / "invalid.md"
    invalid_card.write_text(
        """
---
hyper_parameters:
    learning_rate: 0.001
---

# Invalid Model Card
This model card is missing the required 'name' field
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["-vv", "list-models", str(invalid_card)])

    assert result.exit_code == 0
    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 0
    assert f"Skipping {invalid_card}" in result.stderr


def test_list_models_nonexistent_path(runner: CliRunner, tmp_path: Path) -> None:
    """Test list-models with a non-existent path."""
    nonexistent_path = tmp_path / "does_not_exist"

    result = runner.invoke(app, ["list-models", str(nonexistent_path)])

    assert result.exit_code == 2


def test_list_models_invalid_format(runner: CliRunner, model_card_path: Path) -> None:
    """Test list-models with invalid format option."""
    result = runner.invoke(
        app, ["list-models", str(model_card_path), "--format", "xml"]
    )

    assert result.exit_code == 2

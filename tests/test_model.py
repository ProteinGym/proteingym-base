from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from proteingym.base.__main__ import app
from proteingym.base.model import EntryPoint, ModelCard, ModelProject


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
def invalid_model_card_content() -> str:
    """Invalid model card content for testing."""
    return """---
invalid_yaml: [
---

# Invalid model card format
"""


@pytest.fixture
def empty_model_card_content() -> str:
    return """---
hyper_params:
    learning_rate: 0.001
    batch_size: 32
---

# Empty model card with a missing name
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
def invalid_pyproject_content_missing_project() -> str:
    """Invalid pyproject.toml content for testing."""
    return """[build-system]
requires = ["setuptools"]
# Missing [project] section
"""


@pytest.fixture
def invalid_pyproject_content_missing_name() -> str:
    """Invalid pyproject.toml content for testing."""
    return """[project]
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

    # Create a real function to get signature from
    def mock_train_func(dataset: str, model_path: str):
        pass

    mock_command.callback = mock_train_func
    mock_app.registered_commands = [mock_command]
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
    caplog,
):
    """Test successful model validation with valid entry points and model card."""
    with mock_valid_entry_points:
        result = runner.invoke(app, ["validate", str(model_project)])

        assert result.exit_code == 0
        assert (
            "✅ Model test_model loaded successfully with entry points:" in caplog.text
        )
        assert "✅ Loaded test_model with hyper parameters" in caplog.text


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
            "invalid_pyproject_content_missing_project",
            "test_model",
        ),
    ],
    indirect=True,
)
def test_validation_pyproject_missing_project_section(
    model_project: Path,
    runner: CliRunner,
    caplog,
):
    """Test validation when pyproject.toml is missing [project] section."""
    result = runner.invoke(app, ["validate", str(model_project)])

    assert result.exit_code == 1
    assert (
        "❌ Validation failed: File does not contain a project header:" in caplog.text
    )


@pytest.mark.parametrize(
    "model_project",
    [
        (
            "valid_model_card_content",
            "invalid_pyproject_content_missing_name",
            "test_model",
        ),
    ],
    indirect=True,
)
def test_validation_pyproject_missing_name(
    model_project: Path,
    runner: CliRunner,
    caplog,
):
    """Test validation when pyproject.toml is missing name under [project] section."""
    result = runner.invoke(app, ["validate", str(model_project)])

    assert result.exit_code == 1
    assert (
        "❌ Validation failed: The project header does not contain a name:"
        in caplog.text
    )


@pytest.mark.parametrize(
    "model_project",
    [
        ("invalid_model_card_content", "valid_pyproject_content", "test_model"),
    ],
    indirect=True,
)
def test_validation_invalid_model_card(
    model_project: Path,
    mock_valid_entry_points,
    runner: CliRunner,
    caplog,
):
    """Test validation with invalid model card content."""
    with mock_valid_entry_points:
        result = runner.invoke(app, ["validate", str(model_project)])

        assert result.exit_code == 1
        assert "❌ Error running validation" in caplog.text


@pytest.mark.parametrize(
    "model_project",
    [
        ("empty_model_card_content", "valid_pyproject_content", "test_model"),
    ],
    indirect=True,
)
def test_validation_empty_model_card(
    model_project: Path,
    mock_valid_entry_points,
    runner: CliRunner,
    caplog,
):
    """Test validation with empty model card file."""
    with mock_valid_entry_points:
        result = runner.invoke(app, ["validate", str(model_project)])

        assert result.exit_code == 1
        assert "❌ Validation failed: 1 validation error for ModelCard" in caplog.text


def test_model_card_from_path_file_not_found():
    """Test ModelCard.from_path with non-existent file."""
    with pytest.raises(FileNotFoundError):
        ModelCard.from_path(Path("nonexistent_file.md"))


def test_model_card_with_extra_fields(tmp_path: Path):
    """Test ModelCard allows extra fields."""
    content = """---
name: "test_model"
hyper_params:
    learning_rate: 0.001
custom_field: "custom_value"
another_field:
    nested: true
---

# Test Model
"""
    model_card_file = tmp_path / "model.md"
    model_card_file.write_text(content)

    model_card = ModelCard.from_path(model_card_file)
    assert model_card.name == "test_model"
    assert hasattr(model_card, "custom_field")
    assert model_card.custom_field == "custom_value"


def test_model_card_missing_name_validation_error(tmp_path: Path):
    """Test ModelCard validation error when name is missing."""
    content = """---
hyper_params:
    learning_rate: 0.001
---

# Test Model without name
"""
    model_card_file = tmp_path / "model.md"
    model_card_file.write_text(content)

    with pytest.raises(ValidationError) as exc_info:
        ModelCard.from_path(model_card_file)

    assert "name" in str(exc_info.value)


def test_model_card_empty_hyper_params(tmp_path: Path):
    """Test ModelCard with empty hyper_params defaults to empty dict."""
    content = """---
name: "test_model"
---

# Test Model
"""
    model_card_file = tmp_path / "model.md"
    model_card_file.write_text(content)

    model_card = ModelCard.from_path(model_card_file)
    assert model_card.name == "test_model"
    assert model_card.hyper_params == {}


def test_model_project_computed_properties(tmp_path: Path):
    """Test ModelProject computed properties."""
    # Create valid project structure
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject_content = """[project]
name = "test_model"
version = "1.0.0"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)
    (project_dir / "README.md").write_text("# Test model")

    project = ModelProject.from_path(project_dir)

    # Test computed properties
    assert project.pyproject_path == project_dir / "pyproject.toml"
    assert project.model_card_path == project_dir / "README.md"
    assert project.project_name == "test_model"


def test_model_project_invalid_project_header_type(tmp_path: Path):
    """Test ModelProject with invalid project header type."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml with project as a string instead of dict
    pyproject_content = """project = "invalid"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    project = ModelProject(project_path=project_dir)

    with pytest.raises(ValueError, match="Project header is not a valid dictionary"):
        _ = project.project_name


def test_model_project_empty_project_name(tmp_path: Path):
    """Test ModelProject with empty project name."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject_content = """[project]
name = ""
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    project = ModelProject(project_path=project_dir)

    with pytest.raises(
        ValueError, match="Project name is not a valid non-empty string"
    ):
        _ = project.project_name


def test_model_project_non_string_project_name(tmp_path: Path):
    """Test ModelProject with non-string project name."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject_content = """[project]
name = 123
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    project = ModelProject(project_path=project_dir)

    with pytest.raises(
        ValueError, match="Project name is not a valid non-empty string"
    ):
        _ = project.project_name


def test_model_project_from_path_nonexistent():
    """Test ModelProject.from_path with non-existent path."""
    with pytest.raises(ValueError, match="Project path does not exist"):
        ModelProject.from_path(Path("nonexistent_project"))


def test_model_project_from_path_not_directory(tmp_path: Path):
    """Test ModelProject.from_path with file instead of directory."""
    file_path = tmp_path / "not_a_directory.txt"
    file_path.write_text("content")

    with pytest.raises(ValueError, match="Project path is not a directory"):
        ModelProject.from_path(file_path)


@pytest.fixture
def mock_non_typer_entry_points():
    """Mock entry points that are not typer applications."""
    mock_ep = Mock()
    mock_ep.dist.name = "test_model"
    mock_ep.group = "console_scripts"

    # Mock a non-typer app (no registered_commands attribute)
    mock_app = Mock()
    mock_app.registered_commands = None
    del mock_app.registered_commands  # Remove the attribute entirely
    mock_ep.load.return_value = mock_app

    return patch("proteingym.base.model.metadata.entry_points", return_value=[mock_ep])


def test_model_project_entry_points_filtering_non_typer(
    tmp_path: Path, mock_non_typer_entry_points
):
    """Test that non-typer entry points are filtered out."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject_content = """[project]
name = "test_model"
version = "1.0.0"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    with mock_non_typer_entry_points:
        project = ModelProject.from_path(project_dir)
        # Should have no entry points since the mock app is not a typer app
        assert project.entry_points == []


def test_model_project_entry_points_no_matching_package(tmp_path: Path):
    """Test entry points discovery with no matching package name."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject_content = """[project]
name = "different_name"
version = "1.0.0"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    # Mock entry points with different package name
    mock_ep = Mock()
    mock_ep.dist.name = "other_package"
    mock_ep.group = "console_scripts"

    with patch("proteingym.base.model.metadata.entry_points", return_value=[mock_ep]):
        project = ModelProject.from_path(project_dir)
        # Should have no entry points since package names don't match
        assert project.entry_points == []


def test_model_project_entry_points_wrong_group(tmp_path: Path):
    """Test entry points discovery with wrong group."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject_content = """[project]
name = "test_model"
version = "1.0.0"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    # Mock entry points with wrong group
    mock_ep = Mock()
    mock_ep.dist.name = "test_model"
    mock_ep.group = "gui_scripts"  # Not console_scripts

    with patch("proteingym.base.model.metadata.entry_points", return_value=[mock_ep]):
        project = ModelProject.from_path(project_dir)
        # Should have no entry points since group doesn't match
        assert project.entry_points == []


def test_entry_point_creation():
    """Test EntryPoint dataclass creation."""
    entry_point = EntryPoint(name="test_command", params=["param1", "param2"])
    assert entry_point.name == "test_command"
    assert entry_point.params == ["param1", "param2"]


def test_entry_point_default_params():
    """Test EntryPoint with default empty params."""
    entry_point = EntryPoint(name="test_command")
    assert entry_point.name == "test_command"
    assert entry_point.params == []


@pytest.fixture
def mock_multiple_commands_entry_points():
    """Mock entry points with multiple commands."""
    mock_ep = Mock()
    mock_ep.dist.name = "test_model"
    mock_ep.group = "console_scripts"

    # Create mock functions for commands
    def mock_train_func(dataset: str, model_path: str):
        pass

    def mock_evaluate_func(model: str, data: str, output: str = "results.json"):
        pass

    # Create mock commands
    mock_train_command = Mock()
    mock_train_command.callback = mock_train_func

    mock_eval_command = Mock()
    mock_eval_command.callback = mock_evaluate_func

    mock_app = Mock()
    mock_app.registered_commands = [mock_train_command, mock_eval_command]
    mock_ep.load.return_value = mock_app

    return patch("proteingym.base.model.metadata.entry_points", return_value=[mock_ep])


def test_model_project_multiple_entry_points(
    tmp_path: Path, mock_multiple_commands_entry_points
):
    """Test ModelProject with multiple entry points."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject_content = """[project]
name = "test_model"
version = "1.0.0"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    with mock_multiple_commands_entry_points:
        project = ModelProject.from_path(project_dir)

        assert len(project.entry_points) == 2

        # Check first entry point
        train_ep = next(
            ep for ep in project.entry_points if ep.name == "mock_train_func"
        )
        assert train_ep.params == ["dataset", "model_path"]

        # Check second entry point
        eval_ep = next(
            ep for ep in project.entry_points if ep.name == "mock_evaluate_func"
        )
        assert eval_ep.params == ["model", "data", "output"]

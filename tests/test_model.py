import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from proteingym.base.__main__ import app
from proteingym.base.model import ModelCard


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


def test_list_models_command(runner: CliRunner, model_card_path: Path) -> None:
    """Test the list-models CLI command."""
    result = runner.invoke(app, ["list-models", str(model_card_path)])

    assert result.exit_code == 0

    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 1

    model_data = output_data[0]
    assert model_data["name"] == "dummy"
    assert "path" in model_data
    assert model_data["hyper_params"]["nogpu"] is False


def test_list_models_directory_with_multiple_cards(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Test list-models with a directory containing multiple model cards."""
    model1 = tmp_path / "model1.md"
    model1.write_text(
        """
---
name: "model_one"
hyper_params:
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
hyper_params:
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
    """Test list-models logs debug message when skipping invalid model card."""
    invalid_card = tmp_path / "invalid.md"
    invalid_card.write_text(
        """
---
hyper_params:
    learning_rate: 0.001
---

# Invalid Model Card
This model card is missing the required 'name' field
""",
        encoding="utf-8",
    )

    with patch("proteingym.base.__main__.logging.getLogger") as mock_get_logger:
        mock_logger = mock_get_logger.return_value
        mock_logger.setLevel.return_value = None

        result = runner.invoke(app, ["list-models", str(invalid_card)])

        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert isinstance(output_data, list)
        assert len(output_data) == 0

        mock_logger.debug.assert_called_once()
        debug_call_args = mock_logger.debug.call_args
        assert f"Skipping {invalid_card}" in str(debug_call_args[0][0])


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

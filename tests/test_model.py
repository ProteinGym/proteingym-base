from pathlib import Path
from typer.testing import CliRunner
import json

import pytest
from pydantic import ValidationError

from proteingym.base.model import ModelCard
from proteingym.base.__main__ import app


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


def test_list_models_command_yaml_format(runner: CliRunner, model_card_path: Path) -> None:
    """Test the list-models CLI command with YAML format."""
    result = runner.invoke(app, ["list-models", str(model_card_path), "--format", "yaml"])

    assert result.exit_code == 0
    assert "name: dummy" in result.stdout
    assert "nogpu: false" in result.stdout
from pathlib import Path

import pytest
from pydantic import ValidationError

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

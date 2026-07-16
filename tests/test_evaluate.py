import json

import pytest

from proteingym.base.dataset import Dataset, Subsets
from proteingym.base.evaluate import evaluate_data, evaluate_splits
from proteingym.base.metrics import ScoreMode


@pytest.mark.parametrize(
    "split,fold,target",
    [
        ("split_name", "0", None),
        (None, "0", "target_name"),
        ("split_name", None, "target_name"),
    ],
)
def test_evaluate_splits_requires_parameters(
    tmp_path,
    metrics_subsets_with_assays: Subsets,
    split,
    fold,
    target,
):
    metric_path = tmp_path / "metrics.json"

    dataset_path = metrics_subsets_with_assays.dump(path=tmp_path)
    pred_path = metrics_subsets_with_assays.dataset.dump(path=tmp_path)
    target_name = metrics_subsets_with_assays.dataset.assay_targets[0].name
    split_name = list(metrics_subsets_with_assays.slices.keys())[0]

    split_value = split_name if split == "split_name" else split
    target_value = target_name if target == "target_name" else target

    with pytest.raises((ValueError, TypeError)):
        evaluate_splits(
            prediction_path=pred_path,
            metric_path=metric_path,
            dataset_path=dataset_path,
            split=split_value,  # type: ignore[arg-type]
            target=target_value,  # type: ignore[arg-type]
            fold=fold,  # type: ignore[arg-type]
        )


def test_evaluate_data_missing_prediction_file_raises(
    tmp_path, metrics_dataset_with_assay: Dataset
):
    dataset_path = metrics_dataset_with_assay.dump(path=tmp_path)
    metric_path = tmp_path / "metrics.json"
    missing_pred = tmp_path / "does_not_exist.pgdata"

    with pytest.raises(FileNotFoundError):
        evaluate_data(
            prediction_path=missing_pred,
            metric_path=metric_path,
            dataset_path=dataset_path,
            target="DMS Score",
            selected_metrics=["spearman"],
        )


def test_evaluate_data_writes_full_dataset_metrics(
    tmp_path,
    metrics_dataset_with_assay: Dataset,
    metrics_predicted_dataset: Dataset,
):
    dataset_path = metrics_dataset_with_assay.dump(path=tmp_path)
    pred_path = metrics_predicted_dataset.dump(path=tmp_path)
    metric_path = tmp_path / "metrics.json"

    result_path = evaluate_data(
        prediction_path=pred_path,
        metric_path=metric_path,
        dataset_path=dataset_path,
        target="DMS Score",
        selected_metrics=["spearman"],
        model_name="test_model",
    )

    assert result_path == metric_path
    result = json.loads(metric_path.read_text())
    assert "spearman" in result["full_dataset"]
    assert result["metadata"]["model"] == "test_model"
    assert result["metadata"]["target"] == "DMS Score"


def test_evaluate_splits_writes_metrics_and_metadata(
    tmp_path,
    metrics_subsets_with_assays: Subsets,
    metrics_predicted_dataset: Dataset,
):
    dataset_path = metrics_subsets_with_assays.dump(path=tmp_path)
    pred_path = metrics_predicted_dataset.dump(path=tmp_path)
    metric_path = tmp_path / "metrics.json"

    result_path = evaluate_splits(
        prediction_path=pred_path,
        metric_path=metric_path,
        dataset_path=dataset_path,
        split="random",
        target="DMS Score",
        fold="0",
        selected_metrics=["spearman"],
        model_name="test_model",
        score_modes=[ScoreMode.TEST],
    )

    assert result_path == metric_path
    result = json.loads(metric_path.read_text())
    assert "spearman" in result["test"]
    assert result["metadata"]["model"] == "test_model"
    assert result["metadata"]["split"] == "random"
    assert result["metadata"]["target"] == "DMS Score"
    assert result["metadata"]["test_fold"] == 0

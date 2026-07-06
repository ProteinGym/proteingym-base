import json

import pytest

from proteingym.base.dataset import Dataset, Subsets
from proteingym.base.evaluate import evaluate


class TestEvaluateValidation:
    """Test validation in the evaluate function."""

    @pytest.mark.parametrize(
        "split,fold,target",
        [
            ("split_name", "0", None),
            (None, "0", "target_name"),
            ("split_name", None, "target_name"),
        ],
    )
    def test_evaluate_requires_parameters_for_subsets(
        self,
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

        with pytest.raises(
            ValueError, match="--split, --fold, and --target are required"
        ):
            evaluate(
                prediction_path=pred_path,
                metric_path=metric_path,
                dataset_path=dataset_path,
                split=split_value,
                fold=fold,
                target=target_value,
            )

    def test_evaluate_missing_prediction_file_writes_error(self, tmp_path):
        metric_path = tmp_path / "metrics.json"
        missing_pred = tmp_path / "does_not_exist.pgdata"

        result_path = evaluate(
            prediction_path=missing_pred,
            metric_path=metric_path,
            dataset_path=tmp_path / "dataset.pgdata",
            selected_metrics=["spearman"],
            target="DMS Score",
        )

        assert result_path == metric_path
        result = json.loads(metric_path.read_text())
        assert result["status"] == "failed"
        assert result["spearman"] is None

    def test_evaluate_requires_dataset_path(
        self, tmp_path, metrics_predicted_dataset: Dataset
    ):
        pred_path = metrics_predicted_dataset.dump(path=tmp_path)
        metric_path = tmp_path / "metrics.json"

        with pytest.raises(ValueError, match="'dataset_path' parameter is required"):
            evaluate(
                prediction_path=pred_path,
                metric_path=metric_path,
                dataset_path=None,
            )

    def test_evaluate_dataset_requires_target(
        self,
        tmp_path,
        metrics_dataset_with_assay: Dataset,
        metrics_predicted_dataset: Dataset,
    ):
        dataset_path = metrics_dataset_with_assay.dump(path=tmp_path)
        pred_path = metrics_predicted_dataset.dump(path=tmp_path)
        metric_path = tmp_path / "metrics.json"

        with pytest.raises(ValueError, match="'target' parameter is required"):
            evaluate(
                prediction_path=pred_path,
                metric_path=metric_path,
                dataset_path=dataset_path,
                target=None,
            )

    def test_evaluate_subsets_writes_metrics_and_metadata(
        self,
        tmp_path,
        metrics_subsets_with_assays: Subsets,
        metrics_predicted_dataset: Dataset,
    ):
        dataset_path = metrics_subsets_with_assays.dump(path=tmp_path)
        pred_path = metrics_predicted_dataset.dump(path=tmp_path)
        metric_path = tmp_path / "metrics.json"

        result_path = evaluate(
            prediction_path=pred_path,
            metric_path=metric_path,
            dataset_path=dataset_path,
            selected_metrics=["spearman"],
            model_name="test_model",
            split="random",
            target="DMS Score",
            fold="0",
            score_modes=["test"],
        )

        assert result_path == metric_path
        result = json.loads(metric_path.read_text())
        assert "spearman" in result["test"]
        assert result["metadata"]["model"] == "test_model"
        assert result["metadata"]["split"] == "random"
        assert result["metadata"]["target"] == "DMS Score"
        assert result["metadata"]["test_fold"] == 0

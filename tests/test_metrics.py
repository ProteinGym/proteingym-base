import json
import logging

import polars as pl
import pytest
from Bio.Seq import Seq

from proteingym.base.assay import SEQUENCE
from proteingym.base.dataset import (
    Assay,
    AssaySlice,
    Dataset,
    DatasetSlice,
    Field,
    Subsets,
)
from proteingym.base.metrics import (
    _get_top_k_from_slice,
    calculate_metrics_by_mode,
    calculate_selected_metrics,
    evaluate,
    metric_recovery,
    metric_spearman,
    prepare_and_validate_scoring_df,
)
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType


@pytest.fixture
def metrics_dataset_with_assay() -> Dataset:
    """A dataset containing a single assay with 10 records."""
    sequences = [
        Sequence(
            name=f"seq{i}",
            value=Seq(seq_value),
            type=SequenceType.ENGINEERED_SEQUENCE,
            alphabet=SequenceAlphabet.AA,
        )
        for i, seq_value in enumerate(
            [
                "ACDEFG",
                "ACDEFH",
                "ACDEFI",
                "ACDEFK",
                "ACDEFL",
                "ACDEFM",
                "ACDEFN",
                "ACDEFP",
                "ACDEFQ",
                "ACDEFR",
            ],
            start=1,
        )
    ]

    assay = Assay(
        name="assay1",
        records=[(sequences[i], float(i + 1), float(i + 1) + 0.5) for i in range(10)],
        fields=[
            Field(name="sequence"),
            Field(name="DMS Score"),
            Field(name="stability"),
        ],
    )
    return Dataset(
        name="dataset_with_single_assay",
        description="A dataset containing a single assay.",
        assay_variables=[Field(name="var1", description="A test variable")],
        assay_targets=[
            Field(name="DMS Score", description="The DMS score"),
            Field(name="stability", description="The resistance to temperature"),
        ],
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )


@pytest.fixture
def metrics_predicted_dataset(metrics_dataset_with_assay: Dataset) -> Dataset:
    """A predictions dataset built from metrics_dataset_with_assay."""
    predictions_df = pl.DataFrame(
        {
            "sequence": [
                "ACDEFG",
                "ACDEFH",
                "ACDEFI",
                "ACDEFK",
                "ACDEFL",
                "ACDEFM",
                "ACDEFN",
                "ACDEFP",
                "ACDEFQ",
                "ACDEFR",
            ],
            "DMS Score": [1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1],
        }
    )
    return metrics_dataset_with_assay.predictions_delta(
        predictions_df, target="DMS Score"
    )


@pytest.fixture
def metrics_subsets_with_assays(metrics_dataset_with_assay: Dataset) -> Subsets:
    """A Subsets object with a 5-fold 'random' split (2 records per fold)."""
    folds = []
    for fold_idx in range(5):
        records_mask = [False] * 10
        records_mask[fold_idx * 2] = True
        records_mask[fold_idx * 2 + 1] = True

        fold_slice = DatasetSlice(
            assays=[AssaySlice(records=records_mask)],
            metadata={"fold": float(fold_idx)},
        )
        folds.append(fold_slice)

    return Subsets(dataset=metrics_dataset_with_assay, slices={"random": folds})


@pytest.fixture
def recovery_dataset() -> Dataset:
    """A dataset with known values for testing recovery."""
    sequences = [
        Sequence(
            name=f"seq{i}",
            value=Seq(f"SEQ{i:03d}"),
            type=SequenceType.ENGINEERED_SEQUENCE,
            alphabet=SequenceAlphabet.AA,
        )
        for i in range(10)
    ]

    assay = Assay(
        name="assay1",
        records=[(sequences[i], (i + 1) / 10.0) for i in range(10)],
        fields=[
            Field(name="sequence"),
            Field(name="fitness"),
        ],
    )

    return Dataset(
        name="recovery_test",
        description="Dataset for recovery testing",
        assay_variables=[],
        assay_targets=[Field(name="fitness", description="Fitness score")],
        assays=[assay],
        sequences=sequences,
        structures=[],
        msas=[],
    )


@pytest.fixture
def recovery_subsets(recovery_dataset: Dataset) -> Subsets:
    """Subsets with top_k metadata covering all records in a single slice."""
    all_records_mask = [True] * 10
    return Subsets(
        dataset=recovery_dataset,
        slices={
            "test": [
                DatasetSlice(
                    assays=[AssaySlice(records=all_records_mask)],
                    metadata={"top_k": 3},
                )
            ]
        },
    )


def _fitness_predictions(recovery_dataset: Dataset, values: list[float]) -> Dataset:
    """Helper to build a fitness predictions dataset."""
    predictions_df = pl.DataFrame(
        {
            "sequence": [f"SEQ{i:03d}" for i in range(10)],
            "fitness": values,
        }
    )
    return recovery_dataset.predictions_delta(predictions_df, target="fitness")


class TestMetricSpearman:
    """Test metric_spearman function."""

    def test_perfect_correlation(self, metrics_dataset_with_assay):
        perfect_predictions_df = pl.DataFrame(
            {
                "sequence": [
                    "ACDEFG",
                    "ACDEFH",
                    "ACDEFI",
                    "ACDEFK",
                    "ACDEFL",
                    "ACDEFM",
                    "ACDEFN",
                    "ACDEFP",
                    "ACDEFQ",
                    "ACDEFR",
                ],
                "DMS Score": [10.0 * (i + 1) for i in range(10)],
            }
        )

        perfect_preds = metrics_dataset_with_assay.predictions_delta(
            perfect_predictions_df, target="DMS Score"
        )

        corr = metric_spearman(
            ground_truth=metrics_dataset_with_assay,
            predicted=perfect_preds,
            target="DMS Score",
        )

        assert corr == pytest.approx(1.0)


class TestGetTopKFromSlice:
    """Test _get_top_k_from_slice helper function."""

    @pytest.fixture
    def simple_dataset(self) -> Dataset:
        return Dataset(
            name="test",
            assay_targets=[Field(name="target")],
            assay_variables=[],
            assays=[],
        )

    def test_returns_none_for_dataset(self, simple_dataset):
        assert (
            _get_top_k_from_slice(ground_truth=simple_dataset, split="test", fold=0)
            is None
        )

    def test_returns_none_without_split(self, simple_dataset):
        subsets = Subsets(
            dataset=simple_dataset,
            slices={"test": [DatasetSlice(metadata={"top_k": 10})]},
        )
        assert _get_top_k_from_slice(ground_truth=subsets, split=None, fold=0) is None

    def test_returns_none_without_fold(self, simple_dataset):
        subsets = Subsets(
            dataset=simple_dataset,
            slices={"test": [DatasetSlice(metadata={"top_k": 10})]},
        )
        assert (
            _get_top_k_from_slice(ground_truth=subsets, split="test", fold=None) is None
        )

    def test_returns_none_for_list_fold(self, simple_dataset):
        subsets = Subsets(
            dataset=simple_dataset,
            slices={"test": [DatasetSlice(metadata={"top_k": 10})]},
        )
        assert (
            _get_top_k_from_slice(ground_truth=subsets, split="test", fold=[0, 1])
            is None
        )

    def test_returns_none_without_metadata(self, simple_dataset):
        subsets = Subsets(
            dataset=simple_dataset, slices={"test": [DatasetSlice(metadata=None)]}
        )
        assert _get_top_k_from_slice(ground_truth=subsets, split="test", fold=0) is None

    def test_returns_none_without_top_k_in_metadata(self, simple_dataset):
        subsets = Subsets(
            dataset=simple_dataset,
            slices={"test": [DatasetSlice(metadata={"other_key": "value"})]},
        )
        assert _get_top_k_from_slice(ground_truth=subsets, split="test", fold=0) is None

    def test_extracts_top_k_successfully(self, simple_dataset):
        subsets = Subsets(
            dataset=simple_dataset,
            slices={"test": [DatasetSlice(metadata={"top_k": 10})]},
        )
        assert _get_top_k_from_slice(ground_truth=subsets, split="test", fold=0) == 10

    def test_converts_float_top_k_to_int(self, simple_dataset):
        subsets = Subsets(
            dataset=simple_dataset,
            slices={"test": [DatasetSlice(metadata={"top_k": 10.0})]},
        )
        result = _get_top_k_from_slice(ground_truth=subsets, split="test", fold=0)
        assert result == 10
        assert isinstance(result, int)


class TestMetricRecovery:
    """Test metric_recovery function."""

    def test_perfect_recovery(self, recovery_subsets):
        predictions = _fitness_predictions(
            recovery_subsets.dataset, [(i + 1) / 10.0 for i in range(10)]
        )
        recovery = metric_recovery(
            ground_truth=recovery_subsets,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=0,
        )
        assert recovery == pytest.approx(1.0)

    def test_zero_recovery(self, recovery_subsets):
        predictions = _fitness_predictions(
            recovery_subsets.dataset, [(10 - i) / 10.0 for i in range(10)]
        )
        recovery = metric_recovery(
            ground_truth=recovery_subsets,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=0,
        )
        assert recovery == pytest.approx(0.0)

    def test_partial_recovery(self, recovery_subsets):
        predictions = _fitness_predictions(
            recovery_subsets.dataset,
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.95, 0.75, 0.9, 1.0],
        )
        recovery = metric_recovery(
            ground_truth=recovery_subsets,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=0,
        )
        assert recovery == pytest.approx(2.0 / 3.0)

    def test_recovery_with_dataset_returns_none(self, recovery_dataset):
        predictions = _fitness_predictions(
            recovery_dataset, [(i + 1) / 10.0 for i in range(10)]
        )
        recovery = metric_recovery(
            ground_truth=recovery_dataset,
            predicted=predictions,
            target="fitness",
        )
        assert recovery is None

    def test_recovery_without_metadata_returns_none(self, recovery_dataset):
        subsets_no_metadata = Subsets(
            dataset=recovery_dataset, slices={"test": [DatasetSlice(metadata=None)]}
        )
        predictions = _fitness_predictions(
            recovery_dataset, [(i + 1) / 10.0 for i in range(10)]
        )
        recovery = metric_recovery(
            ground_truth=subsets_no_metadata,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=0,
        )
        assert recovery is None

    def test_recovery_zero_top_k_returns_none(self, recovery_dataset):
        subsets = Subsets(
            dataset=recovery_dataset,
            slices={
                "test": [
                    DatasetSlice(
                        assays=[AssaySlice(records=[True] * 10)],
                        metadata={"top_k": 0},
                    )
                ]
            },
        )
        predictions = _fitness_predictions(
            recovery_dataset, [(i + 1) / 10.0 for i in range(10)]
        )
        recovery = metric_recovery(
            ground_truth=subsets,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=0,
        )
        assert recovery is None

    def test_recovery_in_calculate_selected_metrics(self, recovery_subsets):
        predictions = _fitness_predictions(
            recovery_subsets.dataset, [(i + 1) / 10.0 for i in range(10)]
        )
        results = calculate_selected_metrics(
            selected_metrics=["recovery", "spearman"],
            ground_truth=recovery_subsets,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=0,
        )
        assert "recovery" in results and "spearman" in results
        assert results["recovery"] == pytest.approx(1.0)
        assert results["spearman"] == pytest.approx(1.0)

    def test_recovery_none_for_training_folds(self, recovery_dataset):
        half_records_mask = [i < 5 for i in range(10)]
        subsets_with_mixed_metadata = Subsets(
            dataset=recovery_dataset,
            slices={
                "test": [
                    DatasetSlice(
                        assays=[AssaySlice(records=half_records_mask)],
                        metadata={"top_k": 2},
                    ),
                    DatasetSlice(
                        assays=[AssaySlice(records=half_records_mask)], metadata=None
                    ),
                ]
            },
        )
        predictions = _fitness_predictions(
            recovery_dataset, [(i + 1) / 10.0 for i in range(10)]
        )

        test_recovery = metric_recovery(
            ground_truth=subsets_with_mixed_metadata,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=0,
        )
        assert test_recovery == pytest.approx(1.0)

        train_recovery = metric_recovery(
            ground_truth=subsets_with_mixed_metadata,
            predicted=predictions,
            target="fitness",
            split="test",
            fold=1,
        )
        assert train_recovery is None

    def test_recovery_in_calculate_metrics_by_mode(self, recovery_dataset):
        all_records_mask = [True] * 10
        subsets = Subsets(
            dataset=recovery_dataset,
            slices={
                "cv": [
                    DatasetSlice(
                        assays=[AssaySlice(records=all_records_mask)], metadata=None
                    ),
                    DatasetSlice(
                        assays=[AssaySlice(records=all_records_mask)], metadata=None
                    ),
                    DatasetSlice(
                        assays=[AssaySlice(records=all_records_mask)],
                        metadata={"top_k": 3},
                    ),
                ]
            },
        )
        predictions = _fitness_predictions(
            recovery_dataset, [(i + 1) / 10.0 for i in range(10)]
        )

        results = calculate_metrics_by_mode(
            selected_metrics=["recovery", "spearman"],
            ground_truth=subsets,
            predicted=predictions,
            target="fitness",
            split="cv",
            test_fold=2,
        )

        expected_structure = {
            "test_has_recovery": results["test"]["recovery"] == pytest.approx(1.0),
            "test_has_spearman": results["test"]["spearman"] == pytest.approx(1.0),
            "train_recovery_is_none": results["train_available"]["recovery"] is None,
            "train_has_spearman": results["train_available"]["spearman"]
            == pytest.approx(1.0),
            "fold_0_recovery_is_none": results["per_fold"]["fold_0"]["recovery"]
            is None,
            "fold_1_recovery_is_none": results["per_fold"]["fold_1"]["recovery"]
            is None,
            "fold_2_has_recovery": results["per_fold"]["fold_2"]["recovery"]
            == pytest.approx(1.0),
        }

        assert all(expected_structure.values()), (
            f"Failed checks: {[k for k, v in expected_structure.items() if not v]}"
        )

    def test_recovery_none_serializes_to_json_null(self, recovery_dataset):
        all_records_mask = [True] * 10
        subsets = Subsets(
            dataset=recovery_dataset,
            slices={
                "cv": [
                    DatasetSlice(
                        assays=[AssaySlice(records=all_records_mask)], metadata=None
                    ),
                    DatasetSlice(
                        assays=[AssaySlice(records=all_records_mask)],
                        metadata={"top_k": 3},
                    ),
                ]
            },
        )
        predictions = _fitness_predictions(
            recovery_dataset, [(i + 1) / 10.0 for i in range(10)]
        )

        results = calculate_metrics_by_mode(
            selected_metrics=["recovery", "spearman"],
            ground_truth=subsets,
            predicted=predictions,
            target="fitness",
            split="cv",
            test_fold=1,
        )

        json_str = json.dumps(results)
        parsed = json.loads(json_str)

        expected_json_structure = {
            "test_recovery_is_float": isinstance(parsed["test"]["recovery"], float),
            "train_recovery_is_null": parsed["train_available"]["recovery"] is None,
            "fold_0_recovery_is_null": parsed["per_fold"]["fold_0"]["recovery"] is None,
            "fold_1_recovery_is_float": isinstance(
                parsed["per_fold"]["fold_1"]["recovery"], float
            ),
            "json_contains_null_string": '"recovery": null' in json_str,
        }

        assert all(expected_json_structure.values()), (
            f"Failed checks: {[k for k, v in expected_json_structure.items() if not v]}"
        )

    def test_top_k_larger_than_samples_raises_error(self, recovery_dataset):
        predictions_df = pl.DataFrame(
            {
                "sequence": ["SEQ000", "SEQ001"],
                "fitness": [0.1, 0.2],
            }
        )
        predicted = recovery_dataset.predictions_delta(predictions_df, target="fitness")

        records_mask = [i < 2 for i in range(10)]
        fold_slice = DatasetSlice(
            assays=[AssaySlice(records=records_mask)],
            metadata={"top_k": 10},
        )
        subsets = Subsets(dataset=recovery_dataset, slices={"test": [fold_slice]})

        with pytest.raises(
            ValueError,
            match=r"top_k \(10\) is larger than the number of samples \(2\)\.",
        ):
            metric_recovery(
                ground_truth=subsets,
                predicted=predicted,
                target="fitness",
                split="test",
                fold=0,
            )


class TestPrepareAndValidateScoringDf:
    """Test prepare_and_validate_scoring_df function."""

    def test_with_dataset(self, metrics_dataset_with_assay, metrics_predicted_dataset):
        df = prepare_and_validate_scoring_df(
            ground_truth=metrics_dataset_with_assay,
            predicted=metrics_predicted_dataset,
            target="DMS Score",
        )

        expected_properties = {
            "is_dataframe": isinstance(df, pl.DataFrame),
            "has_sequence": SEQUENCE in df.columns,
            "has_target": "DMS Score" in df.columns,
            "has_predictions": "DMS Score_pred" in df.columns,
            "correct_length": len(df) == 10,
        }

        assert all(expected_properties.values()), (
            f"Failed checks: {[k for k, v in expected_properties.items() if not v]}"
        )

    def test_missing_predictions_raises_error(self, metrics_dataset_with_assay):
        incomplete_predictions_df = pl.DataFrame(
            {
                "sequence": ["ACDEFG"],
                "DMS Score": [1.1],
            }
        )
        incomplete_preds = metrics_dataset_with_assay.predictions_delta(
            incomplete_predictions_df, target="DMS Score"
        )

        with pytest.raises(ValueError, match="Missing 9 prediction"):
            prepare_and_validate_scoring_df(
                ground_truth=metrics_dataset_with_assay,
                predicted=incomplete_preds,
                target="DMS Score",
            )

    def test_mismatched_variables_raises_error(self, metrics_dataset_with_assay):
        mismatched_predicted = metrics_dataset_with_assay.model_copy(
            update={"assay_variables": [Field(name="different_var")]}
        )

        with pytest.raises(ValueError, match="must have identical assay_variables"):
            prepare_and_validate_scoring_df(
                ground_truth=metrics_dataset_with_assay,
                predicted=mismatched_predicted,
                target="DMS Score",
            )

    def test_invalid_ground_truth_type_raises_error(self, metrics_predicted_dataset):
        with pytest.raises(TypeError, match="must be a Dataset or a Subsets object"):
            prepare_and_validate_scoring_df(
                ground_truth="invalid",  # type: ignore
                predicted=metrics_predicted_dataset,
                target="fitness",
            )

    def test_subsets_without_split_raises_error(
        self, metrics_subsets_with_assays, metrics_predicted_dataset
    ):
        with pytest.raises(
            ValueError, match="Both 'split' and 'fold' must be provided"
        ):
            prepare_and_validate_scoring_df(
                ground_truth=metrics_subsets_with_assays,
                predicted=metrics_predicted_dataset,
                target="DMS Score",
            )


class TestCalculateSelectedMetrics:
    """Test calculate_selected_metrics function."""

    def test_unknown_metric_warning(
        self, metrics_dataset_with_assay, metrics_predicted_dataset, caplog
    ):
        with caplog.at_level(logging.WARNING, logger="proteingym.base"):
            results = calculate_selected_metrics(
                selected_metrics=["unknown_metric"],
                ground_truth=metrics_dataset_with_assay,
                predicted=metrics_predicted_dataset,
                target="DMS Score",
            )

        assert "Metric 'unknown_metric' not found" in caplog.text
        assert "unknown_metric" not in results


class TestMetricsIntegration:
    """Integration tests using real dataset fixtures."""

    def test_with_subsets(self, metrics_subsets_with_assays):
        dataset = metrics_subsets_with_assays.dataset
        target_name = dataset.assay_targets[0].name

        predictions = Dataset(
            name="test_predictions",
            assay_targets=dataset.assay_targets,
            assay_variables=dataset.assay_variables,
            assays=dataset.assays,
        )

        split_name = list(metrics_subsets_with_assays.slices.keys())[0]

        results = calculate_selected_metrics(
            selected_metrics=["spearman"],
            ground_truth=metrics_subsets_with_assays,
            predicted=predictions,
            target=target_name,
            split=split_name,
            fold=0,
        )

        assert "spearman" in results
        assert results["spearman"] == pytest.approx(1.0)

    def test_multi_mode_scoring(self, metrics_subsets_with_assays):
        dataset = metrics_subsets_with_assays.dataset
        target_name = dataset.assay_targets[0].name

        predictions = Dataset(
            name="test_predictions",
            assay_targets=dataset.assay_targets,
            assay_variables=dataset.assay_variables,
            assays=dataset.assays,
        )

        split_name = list(metrics_subsets_with_assays.slices.keys())[0]
        test_fold = 0

        results = calculate_metrics_by_mode(
            selected_metrics=["spearman"],
            ground_truth=metrics_subsets_with_assays,
            predicted=predictions,
            target=target_name,
            split=split_name,
            test_fold=test_fold,
            score_modes=["test", "train_available", "per_fold"],
        )

        expected_results = {
            "has_correct_keys": set(results.keys())
            == {"test", "train_available", "per_fold", "metadata"},
            "test_spearman_correct": results["test"]["spearman"] == pytest.approx(1.0),
            "train_available_spearman_correct": results["train_available"]["spearman"]
            == pytest.approx(1.0),
            "per_fold_spearman_correct": all(
                fold_metrics["spearman"] == pytest.approx(1.0)
                for fold_metrics in results["per_fold"].values()
            ),
            "metadata_test_folds_correct": results["metadata"]["test_folds"]
            == [test_fold],
            "metadata_train_folds_correct": test_fold
            not in results["metadata"]["train_available_folds"],
            "metadata_total_folds_correct": results["metadata"]["total_folds"]
            == len(results["per_fold"]),
        }

        assert all(expected_results.values()), (
            f"Failed checks: {[k for k, v in expected_results.items() if not v]}"
        )

    def test_full_dataset_mode(self, metrics_subsets_with_assays):
        dataset = metrics_subsets_with_assays.dataset
        target_name = dataset.assay_targets[0].name

        predictions = Dataset(
            name="test_predictions",
            assay_targets=dataset.assay_targets,
            assay_variables=dataset.assay_variables,
            assays=dataset.assays,
        )

        split_name = list(metrics_subsets_with_assays.slices.keys())[0]

        results = calculate_metrics_by_mode(
            selected_metrics=["spearman"],
            ground_truth=metrics_subsets_with_assays,
            predicted=predictions,
            target=target_name,
            split=split_name,
            test_fold=0,
            score_modes=["full_dataset"],
        )

        assert set(results.keys()) == {"full_dataset", "metadata"}
        assert results["full_dataset"]["spearman"] == pytest.approx(1.0)


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
        self, tmp_path, metrics_subsets_with_assays, split, fold, target
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

    def test_evaluate_requires_dataset_path(self, tmp_path, metrics_predicted_dataset):
        pred_path = metrics_predicted_dataset.dump(path=tmp_path)
        metric_path = tmp_path / "metrics.json"

        with pytest.raises(ValueError, match="'dataset_path' parameter is required"):
            evaluate(
                prediction_path=pred_path,
                metric_path=metric_path,
                dataset_path=None,
            )

    def test_evaluate_dataset_requires_target(
        self, tmp_path, metrics_dataset_with_assay, metrics_predicted_dataset
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
        self, tmp_path, metrics_subsets_with_assays, metrics_predicted_dataset
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

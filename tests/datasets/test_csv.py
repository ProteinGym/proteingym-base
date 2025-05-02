import pytest
import random
from pg2_dataset.datasets.csv import CSVDataset


@pytest.fixture
def dummy_data():
    return f"""sequence,a,b,c
    {"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3
    {"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3
    {"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3
    {"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3
    {"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3
    """


class TestCSVDataset:
    @pytest.fixture
    def csv_file_path(self, dummy_data, tmpdir):
        file_path = tmpdir / "dummy.csv"

        with open(file_path, "w") as file:
            file.write(dummy_data)

        return str(file_path)

    def test_split(self, csv_file_path):
        dataset = CSVDataset(
            file_path=csv_file_path,
            input_keys=["sequence"],
            label="c",
            train_size=3,
            test_size=2,
        )

        assert dataset.train is not None, "dataset.train is None."
        assert len(dataset.train) == 3, (
            "dataset.train does not have the correct number of records."
        )

        assert dataset.test is not None, "dataset.test is None."
        assert len(dataset.test) == 2, (
            "dataset.test does not have the correct number of records."
        )

    def test_input_keys(self, csv_file_path):
        dataset = CSVDataset(
            file_path=csv_file_path,
            input_keys=["sequence"],
            train_size=3,
            test_size=2,
        )

        for record in dataset.train:
            assert set(record._input_keys) == {"sequence"}, (
                "input_keys are not correctly set in dataset.train."
            )

        for record in dataset.test:
            assert set(record._input_keys) == {"sequence"}, (
                "input_keys are not correctly set in dataset.test."
            )

    def test_bad_input_keys(self, csv_file_path):
        with pytest.raises(ValueError):
            dataset = CSVDataset(
                file_path=csv_file_path,
                input_keys=["bad_sequence"],
                train_size=3,
                test_size=2,
            )

            dataset.train

    def test_label(self, csv_file_path):
        dataset = CSVDataset(
            file_path=csv_file_path,
            input_keys=["sequence"],
            label="a",
            train_size=3,
            test_size=2,
        )

        for record in dataset.train:
            assert record._label == "a", "label is not correctly set in dataset.train."

        for record in dataset.test:
            assert record._label == "a", "label is not correctly set in dataset.test."

    def test_bad_label(self, csv_file_path):
        with pytest.raises(ValueError):
            dataset = CSVDataset(
                file_path=csv_file_path,
                input_keys=["sequence"],
                label=["a"],
                train_size=3,
                test_size=2,
            )

            dataset.train

        with pytest.raises(ValueError):
            dataset = CSVDataset(
                file_path=csv_file_path,
                input_keys=["sequence"],
                label=["a", "b"],
                train_size=3,
                test_size=2,
            )

            dataset.train

        with pytest.raises(ValueError):
            dataset = CSVDataset(
                file_path=csv_file_path,
                input_keys=["sequence"],
                label=["d"],
                train_size=3,
                test_size=2,
            )

            dataset.train

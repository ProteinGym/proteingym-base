import pytest
import random
import polars as pl
from pg2_dataset.datasets.csv import CSVDataset


@pytest.fixture
def good_data():
    return f"""sequence,a,b,c
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.1
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.2
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.3
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.4
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.5
"""


@pytest.fixture
def null_data():
    return f"""sequence,a,b,c
,1,2,3.1
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,3.2
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,,3.3
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,
,1,2,3.5
"""


class TestCSVDataset:
    @pytest.fixture
    def good_csv_file_path(self, good_data, tmpdir):
        file_path = tmpdir / "good.csv"

        with open(file_path, "w") as file:
            file.write(good_data)

        return str(file_path)

    @pytest.fixture
    def null_csv_file_path(self, null_data, tmpdir):
        file_path = tmpdir / "null.csv"

        with open(file_path, "w") as file:
            file.write(null_data)

        return str(file_path)

    def test_features_should_exist_in_data_frame(self, good_csv_file_path):
        dataset = CSVDataset(
            file_path=good_csv_file_path,
            features=["sequence"],
            targets=["c"],
        )

        for record in dataset.data_frame:
            assert set(record._features) == {"sequence"}, "features are not correctly set in dataset.train."

    def test_bad_features_should_raise_error(self, good_csv_file_path):
        with pytest.raises(ValueError):
            CSVDataset(
                file_path=good_csv_file_path,
                features=["bad_sequence"],
                targets=["c"],
            )

    def test_targets_should_exist_in_data_frame(self, good_csv_file_path):
        dataset = CSVDataset(
            file_path=good_csv_file_path,
            features=["sequence"],
            targets=["c"],
        )

        for record in dataset.data_frame:
            assert set(record._targets) == {"c"}, "features are not correctly set in dataset.train."

    def test_bad_targets_should_raise_error(self, good_csv_file_path):
        with pytest.raises(ValueError):
            CSVDataset(
                file_path=good_csv_file_path,
                features=["sequence"],
                targets=["d"],
            )

    def test_good_schema_should_be_parsed_correctly(self, good_csv_file_path):
        dataset = CSVDataset(
            file_path=good_csv_file_path,
            features=["sequence"],
            targets=["c"],
            columns=["sequence", "a", "b", "c"],
            schemas=[pl.String, pl.Int64, pl.Int64, pl.Float64],
        )

        assert dataset.data_frame is not None, "dataset.data_frame is None."
        assert len(dataset.data_frame) == 5, "dataset.data_frame does not have the correct number of records."

        for record in dataset.data_frame:
            assert isinstance(record.sequence, str), f"{record.sequence} should be a string"
            assert isinstance(record.a, int), f"{record.a} should be an integer"
            assert isinstance(record.b, int), f"{record.b} should be an integer"
            assert isinstance(record.c, float), f"{record.c} should be a float"

    def test_bad_schema_should_raise_error(self, good_csv_file_path):
        with pytest.raises(pl.exceptions.ComputeError):
            CSVDataset(
                file_path=good_csv_file_path,
                features=["sequence"],
                targets=["c"],
                columns=["sequence", "a", "b", "c"],
                schemas=[pl.String, pl.Int64, pl.Int64, pl.Int64],
            )

    def test_null_values_should_be_parsed_as_null(self, null_csv_file_path):
        dataset = CSVDataset(
            file_path=null_csv_file_path,
            features=["sequence"],
            targets=["c"],
            columns=["sequence", "a", "b", "c"],
            schemas=[pl.String, pl.Int64, pl.Int64, pl.Float64],
        )

        assert dataset._data_frame.select(pl.all().is_null().sum()).to_dicts()[0] == {
            "a": 2,
            "b": 1,
            "c": 1,
            "sequence": 2,
        }

    def test_get_data_frame_by_target_correctly(self, null_csv_file_path):
        dataset = CSVDataset(
            file_path=null_csv_file_path,
            features=["sequence"],
            targets=["a", "c"],
        )

        data_frame_by_target = dataset.data_frame_by_target("c")

        assert len(data_frame_by_target) == 4, "only 4 valid records by the target 'c'"
        assert set([record.c for record in data_frame_by_target]) == set([3.1, 3.2, 3.3, 3.5])

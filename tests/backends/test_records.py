import random

import polars as pl
import pytest
from pydantic import ValidationError

from pg2_dataset.backends.records import RecordsDataset


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
{""},1,2,3.5
"""


@pytest.fixture
def any_data():
    return f"""a_sequence,a,b,c,round
,1,2,3.1
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,3.2,1
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,,3.3,2
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,,2
{""},1,2,3.5,1
"""


class TestRecordsDataset:
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

    @pytest.fixture
    def any_csv_file_path(self, any_data, tmpdir):
        file_path = tmpdir / "any.csv"

        with open(file_path, "w") as file:
            file.write(any_data)

        return str(file_path)

    def test_features_should_be_renamed_correctly(self, any_csv_file_path):
        dataset = RecordsDataset(
            include_records=True,
            records_file_path=any_csv_file_path,
            sequence_feature="a_sequence",
            engineering_round_feature="round",
            columns=["a_sequence", "c", "round"],
            schemas=[pl.String, pl.Float64, pl.Int64],
        )

        assert "sequence" in dataset.data_frame().columns.to_list()
        assert "a_sequence" not in dataset.data_frame().columns.to_list()

        assert "engineering_round" in dataset.data_frame().columns.to_list()
        assert "round" not in dataset.data_frame().columns.to_list()

    def test_columns_should_exist_in_data_frame(self, good_csv_file_path):
        with pytest.raises(pl.exceptions.ColumnNotFoundError):
            ds = RecordsDataset(
                include_records=True,
                records_file_path=good_csv_file_path,
                sequence_feature="sequence",
                columns=["sequence", "c", "e"],
                schemas=[pl.String, pl.Float64, pl.Float64],
            )
            print(ds)

    def test_good_schema_should_be_parsed_correctly(self, good_csv_file_path):
        dataset = RecordsDataset(
            include_records=True,
            records_file_path=good_csv_file_path,
            sequence_feature="sequence",
            columns=["sequence", "c"],
            schemas=[pl.String, pl.Float64],
        )

        assert dataset.data_frame() is not None, "dataset.data_frame is None."
        assert len(dataset.data_frame()) == 5

        for record in dataset.data_frame().to_dict("records"):
            assert isinstance(record["sequence"], str)
            assert isinstance(record["c"], float)

    def test_bad_schema_should_raise_error(self, good_csv_file_path):
        with pytest.raises(pl.exceptions.ComputeError):
            ds = RecordsDataset(
                include_records=True,
                records_file_path=good_csv_file_path,
                sequence_feature="sequence",
                columns=["sequence", "c"],
                schemas=[pl.String, pl.Int64],
            )
            print(ds)

    def test_null_values_should_be_parsed_as_null(self, null_csv_file_path):
        dataset = RecordsDataset(
            include_records=True,
            records_file_path=null_csv_file_path,
            sequence_feature="sequence",
            columns=["sequence", "a", "b", "c"],
            schemas=[pl.String, pl.Float64, pl.Float64, pl.Float64],
        )

        assert dataset.raw_data_frame.select(pl.all().is_null().sum()).to_dicts()[
            0
        ] == {
            "a": 2,
            "b": 1,
            "c": 1,
            "sequence": 2,
            "engineering_round": 0,
        }

    def test_get_records_correctly(self, null_csv_file_path):
        dataset = RecordsDataset(
            include_records=True,
            records_file_path=null_csv_file_path,
            sequence_feature="sequence",
            columns=["sequence", "a", "b", "c"],
            schemas=[pl.String, pl.Float64, pl.Float64, pl.Float64],
        )

        assert len(dataset.records) == 3
        for record in dataset.records:
            assert record.sequence is not None
            assert record.engineering_round is not None

    def test_get_data_frame_correctly(self, null_csv_file_path):
        dataset = RecordsDataset(
            include_records=True,
            records_file_path=null_csv_file_path,
            sequence_feature="sequence",
            columns=["sequence", "a", "b", "c"],
            schemas=[pl.String, pl.Float64, pl.Float64, pl.Float64],
        )

        data_frame = dataset.data_frame()

        assert len(data_frame) == 3
        assert len(data_frame.columns) == 5, (
            "there are 4 selected columns and 1 engineering round column"
        )

    def test_get_data_frame_by_target_correctly(self, null_csv_file_path):
        dataset = RecordsDataset(
            include_records=True,
            records_file_path=null_csv_file_path,
            sequence_feature="sequence",
            columns=["sequence", "a", "b", "c"],
            schemas=[pl.String, pl.Float64, pl.Float64, pl.Float64],
        )

        data_frame_by_target = dataset.data_frame_by_target("c")

        assert len(data_frame_by_target) == 2
        assert len(data_frame_by_target.columns) == 5, (
            "there are 4 selected columns and 1 engineering round column"
        )

    # since we do allow ints now i think we don't need to test for allowed
    # types anymore? Since we got str/float/int?
    #
    #
    # def test_extra_columns_should_be_within_allowed_types(self, good_csv_file_path):
    #     with pytest.raises(ValidationError):
    #         ds = RecordsDataset(
    #             include_records=True,
    #             records_file_path=good_csv_file_path,
    #             sequence_feature="sequence",
    #             columns=["sequence", "a", "b", "c"],
    #             schemas=[pl.String, pl.Int64, pl.Int64, pl.Float64],
    #         )
    #         print(ds)

    def test_schemas_should_not_exist_without_columns(self, good_csv_file_path):
        with pytest.raises(ValidationError):
            ds = RecordsDataset(
                include_records=True,
                records_file_path=good_csv_file_path,
                sequence_feature="sequence",
                schemas=[pl.String, pl.Int64, pl.Int64, pl.Float64],
            )
            print(ds)

import random

import polars as pl
import pytest
from pydantic import ValidationError

from pg2_dataset.backends import Assays
from pg2_dataset.backends.assays import ENGINEERING_ROUND, SEQUENCE
from pg2_dataset.primitives.meta import AssaysMeta, SingleAssayMeta
from pg2_dataset.splits.random_split_strategy import RandomSplitStrategy


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
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.5
"""


@pytest.fixture
def any_data():
    return f"""a_sequence,a,b,c,round
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.1,1
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,3.2,1
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,,3.3,2
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,,2
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.5,1
"""


@pytest.fixture
def split_data():
    return f"""a_sequence,a,b,c,round,a_split
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.1,1,train
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,3.2,1,valid
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,,3.3,2,test
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},,2,,2,train
{"".join(random.choices("ACDEFGHIJKLMNOPQRSTVYW", k=10))},1,2,3.5,1,test
"""


class TestAssays:
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

    @pytest.fixture
    def split_csv_file_path(self, split_data, tmpdir):
        file_path = tmpdir / "split.csv"

        with open(file_path, "w") as file:
            file.write(split_data)

        return str(file_path)

    def test_features_should_be_renamed_correctly(self, any_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=any_csv_file_path,
                sequence_feature="a_sequence",
                engineering_round_feature="round",
                assays={"a": SingleAssayMeta()},
            ),
        )

        assert SEQUENCE in dataset.data_frame.columns.to_list()
        assert "a_sequence" not in dataset.data_frame.columns.to_list()

        assert ENGINEERING_ROUND in dataset.data_frame.columns.to_list()
        assert "round" not in dataset.data_frame.columns.to_list()

    def test_sequence_feature_should_exist(self, good_csv_file_path):
        with pytest.raises(ValidationError):
            dataset = Assays(
                meta=AssaysMeta(
                    file_path=good_csv_file_path,
                    sequence_feature="",
                    assays={"a": SingleAssayMeta()},
                ),
            )
            print(dataset)

    def test_engineering_round_feature_should_exist(self, good_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=good_csv_file_path, assays={"a": SingleAssayMeta()}
            ),
        )

        assert ENGINEERING_ROUND in dataset.data_frame.columns.to_list()
        for record in dataset.records:
            assert record.engineering_round == 1

    def test_columns_should_exist_in_data_frame(self, good_csv_file_path):
        with pytest.raises(pl.exceptions.ColumnNotFoundError):
            dataset = Assays(
                meta=AssaysMeta(
                    file_path=good_csv_file_path,
                    sequence_feature="sequence",
                    assays={"c": SingleAssayMeta(), "e": SingleAssayMeta()},
                ),
            )
            print(dataset)

    def test_good_schema_should_be_parsed_correctly(self, good_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=good_csv_file_path, assays={"c": SingleAssayMeta()}
            ),
        )

        assert dataset.data_frame is not None, "dataset.data_frame is None."
        assert len(dataset.data_frame) == 5

        for record in dataset.data_frame.to_dict("records"):
            assert isinstance(record["sequence"], str)
            assert isinstance(record["c"], float)

    def test_null_values_should_be_parsed_as_null(self, null_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=null_csv_file_path,
                assays={
                    "a": SingleAssayMeta(),
                    "b": SingleAssayMeta(),
                    "c": SingleAssayMeta(),
                },
            ),
        )

        assert dataset._internal_data_frame.select(pl.all().is_null().sum()).to_dicts()[
            0
        ] == {
            "a": 2,
            "b": 1,
            "c": 1,
            SEQUENCE: 1,
            ENGINEERING_ROUND: 0,
        }

    def test_get_records_correctly(self, null_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=null_csv_file_path,
                assays={
                    "a": SingleAssayMeta(),
                    "b": SingleAssayMeta(),
                    "c": SingleAssayMeta(),
                },
            ),
        )

        assert len(dataset.records) == 4
        for record in dataset.records:
            assert record.sequence is not None
            assert record.engineering_round is not None

    def test_get_data_frame_correctly(self, null_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=null_csv_file_path,
                assays={
                    "a": SingleAssayMeta(),
                    "b": SingleAssayMeta(),
                    "c": SingleAssayMeta(),
                },
            ),
        )

        assert len(dataset.data_frame) == 4
        assert len(dataset.data_frame.columns) == 5, (
            "there are 4 selected columns and 1 engineering round column"
        )

    def test_get_data_frame_by_target_correctly(self, null_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=null_csv_file_path,
                assays={
                    "a": SingleAssayMeta(),
                    "b": SingleAssayMeta(),
                    "c": SingleAssayMeta(),
                },
            ),
        )

        data_frame_by_target = dataset.data_frame_by_target("c")

        assert len(data_frame_by_target) == 3
        assert len(data_frame_by_target.columns) == 5, (
            "there are 4 selected columns and 1 engineering round column"
        )

    def test_split_data_frame_by_default_correctly(self, split_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=split_csv_file_path,
                sequence_feature="a_sequence",
                split_feature="a_split",
                assays={"a": SingleAssayMeta(), "b": SingleAssayMeta(features=["c"])},
            ),
        )

        assert "split" in dataset.data_frame.columns.to_list()
        assert "a_split" not in dataset.data_frame.columns.to_list()

        assert len(dataset.train()) == 2
        assert len(dataset.valid()) == 1
        assert len(dataset.test()) == 2

        x, y = dataset.train(targets=("a", "b"))
        assert x.columns.to_list() == [SEQUENCE, "c"]
        assert y.columns.to_list() == ["a", "b"]

    def test_add_split_by__random_strategy(self, split_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=split_csv_file_path,
                sequence_feature="a_sequence",
                split_feature="a_split",
                assays={"a": SingleAssayMeta(), "b": SingleAssayMeta(features=["c"])},
            ),
        )
        dataset.add_split(
            RandomSplitStrategy(train_ratio=0.6, valid_ratio=0.2),
        )
        assert len(dataset.train()) == 3
        assert len(dataset.valid()) == 1
        assert len(dataset.test()) == 1

    def test_iter_by_rounds(self, split_csv_file_path):
        dataset = Assays(
            meta=AssaysMeta(
                file_path=split_csv_file_path,
                sequence_feature="a_sequence",
                engineering_round_feature="round",
                assays={
                    "a": SingleAssayMeta(),
                    "b": SingleAssayMeta(),
                    "c": SingleAssayMeta(),
                },
            ),
        )

        for round_idx, batch in enumerate(dataset.iter_by_rounds()):
            if round_idx == 0:
                assert len(batch) == 3

            if round_idx == 1:
                assert len(batch) == 2

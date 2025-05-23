from pg2_dataset.primitives.meta import AssayMeta, RecordsMeta


class TestRecordsMeta:
    def test_columns_property(self):
        meta = RecordsMeta(
            sequence_feature="sequence",
            engineering_round_feature="foo",
        )
        assert meta.columns == ["foo", "sequence"]

    def test_columns_property_with_assays(self):
        meta = RecordsMeta(
            sequence_feature="seq",
            assays={"activity": AssayMeta(), "expression": AssayMeta()},
        )
        assert meta.columns == ["activity", "expression", "seq"]

    def test_columns_property_with_assays_and_features(self):
        meta = RecordsMeta(
            sequence_feature="seq",
            assays={
                "activity": AssayMeta(features=["foo", "bar"]),
                "expression": AssayMeta(features=["baz"]),
            },
        )
        assert meta.columns == ["activity", "bar", "baz", "expression", "foo", "seq"]

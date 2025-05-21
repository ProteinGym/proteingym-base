import tempfile

from pg2_dataset.backends.records import RecordsDataset


class TestIO:
    def test_records_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset = RecordsDataset(toml_file="example_data/dataset.toml")
            dataset.to_zip(f"{tmpdir}/dataset.zip")

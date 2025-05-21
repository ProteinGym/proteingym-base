import tempfile

from pg2_dataset.backends.records import RecordsDataset


def mock_toml_file_contents():
    return """
[artifacts]
records = "https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv"
structure = "example_data/v1/A0A1I9GEU1_NEIME_Kennouche_2019/structure.cif"
msa = "data/msa.npy"


[records]
sequence_feature = "mutated_sequence"
columns = [
    "mutated_sequence",
    "mutant",
    "DMS_score",
    "DMS_score_bin",
    "engineering_round"
]


[metadata]
name = "project name"
description = "project description"
doi = "DOI: 10.1000/xyz123"
source = "DOI: 10.1000/xyz123"
xref = ""
"""


class TestIO:
    def test_records_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path_to_toml = f"{tmpdir}/dataset.toml"
            with open(path_to_toml, "w") as f:
                f.write(mock_toml_file_contents())
            dataset = RecordsDataset(toml_file=path_to_toml)
            dataset.to_zip(f"{tmpdir}/dataset.zip")

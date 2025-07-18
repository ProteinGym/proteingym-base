import pytest
from pg2_dataset.models.sequence import Sequence
from pg2_dataset.models.manifest import DatasetManifest
from pg2_dataset.models.dataset import Dataset
from pathlib import Path

def test_assert_non_empty_sequence_list_raises():
    from pg2_dataset.models.dataset import assert_non_empty_sequence_list
    with pytest.raises(ValueError):
        assert_non_empty_sequence_list([])


@pytest.mark.parametrize(
    "name, description, version, sequences", 
    [
        ("test_dataset", "A test dataset which contains sequences.", "1.0", []),
    ]
)
@pytest.mark.xfail(raises=ValueError, reason="At least one sequence is required.")
def test_dataset_empty_sequences(name, description, version, sequences):
    ds = Dataset(name=name, description=description, version=version, sequences=sequences)
    assert ds.name == name
    assert ds.description == description
    assert ds.version == version
    assert isinstance(ds.sequences, list)


@pytest.mark.parametrize(
    "name, description, version, sequences", 
    [
        ("test_dataset", "A test dataset which contains sequences.", "1.0", [{
                    "name": "seq1",
                    "value": "ACGT",
                    "description": "seq 1 desc",
                    "type": "wild_type",
                    "alphabet": "DNA",
                }]),
    ]
)
def test_dataset(name, description, version, sequences):
    ds = Dataset(name=name, description=description, version=version, sequences=sequences)
    assert ds.name == name
    assert ds.description == description
    assert ds.version == version
    assert isinstance(ds.sequences, list)
    assert all(isinstance(seq, Sequence) for seq in ds.sequences)


@pytest.mark.parametrize(
    "manifest",
    [
        {
            "name": "test_dataset",
            "description": "A test dataset which contains sequences.",
            "version": "1.0",
            "sequences": [
                {
                    "sequence_type": "wild_type",
                    "sequence_alphabet": "DNA",
                    "sources": {
                        "local": ["tests/test_data/datasets/dataset1/sequences/"],
                        "s3": []
                    }
                }
            ],
        }
    ]
)
def test_dataset_from_manifest(manifest):
    print(manifest)
    ds_manifest = DatasetManifest(**manifest)
    ds = Dataset.from_manifest(ds_manifest)
    assert ds.name == manifest["name"]
    assert ds.description == manifest["description"]
    assert ds.version == manifest["version"]
    assert isinstance(ds.sequences, list)
    assert all(isinstance(seq, Sequence) for seq in ds.sequences)
    assert isinstance(ds.creator, str)
    assert ds.creator == ""  # Default value for creator
    assert isinstance(ds.metadata, dict)
    assert ds.metadata == {}  # Default value for metadata


@pytest.mark.parametrize(
    "manifest_path",
    [
        "tests/test_data/datasets/dataset1/neime_manifest.toml",
    ]
)
def test_dataset_from_manifest_toml(manifest_path):
    ds = Dataset.from_manifest_toml(manifest_path)
    assert isinstance(ds, Dataset)
    assert len(ds.name) >= 4
    assert len(ds.description) >= 20
    assert isinstance(ds.sequences, list)
    assert len(ds.sequences) > 0
    assert all(isinstance(seq, Sequence) for seq in ds.sequences)


@pytest.mark.parametrize(
    "zip_path",
    [
        "tests/test_data/datasets/zip/neime.zip",
    ]
)
def test_dataset_from_zip(zip_path):
    ds = Dataset.from_zip(zip_path)
    assert isinstance(ds, Dataset)
    assert len(ds.name) >= 4
    assert len(ds.description) >= 20
    assert isinstance(ds.sequences, list)
    assert len(ds.sequences) > 0
    assert all(isinstance(seq, Sequence) for seq in ds.sequences)

@pytest.mark.parametrize(
    "name, description, version, sequences", 
    [
        ("test_dataset", "A test dataset which contains sequences.", "1.0", [{
                    "name": "seq1",
                    "value": "ACGT",
                    "description": "seq 1 desc",
                    "type": "wild_type",
                    "alphabet": "DNA",
                }]),
    ]
)
def test_dataset_dump(name, description, version, sequences):
    ds = Dataset(name=name, description=description, version=version, sequences=sequences)
    ds.dump("test_dir/")
    assert Path(f"test_dir/{name}.toml").exists()
    assert Path(f"test_dir/sequences/seq1.fasta").exists()

import pytest
from pydantic import ValidationError

from pg2_dataset.models.manifest import Manifest, SequenceManifest, Sources

TEST_MANIFEST_FILE = "tests/test_data/manifests/test_manifest.toml"


@pytest.mark.parametrize(
    "local,s3",
    [
        (["/some/path"], []),
        (["/some/path"], ["s3://bucket"]),
        ([], ["s3://bucket"]),
    ],
)
def test_source_dirs(local, s3):
    sources = Sources(local=local, s3=s3)
    if local or s3:
        assert sources.local == local
        assert sources.s3 == s3
    else:
        with pytest.raises(ValidationError) as e:
            Sources(local=local, s3=s3)
        assert "At least one of 'local' or 's3' must be provided in sources" in str(
            e.value
        )


@pytest.mark.parametrize("local,s3", [([], [])])
@pytest.mark.xfail(raises=ValidationError)
def test_source_dirs_empty(local, s3):
    Sources(local=local, s3=s3)


@pytest.mark.parametrize(
    "sequence_type, sequence_alphabet, local, s3",
    [
        (
            "wild_type",
            "DNA",
            ["path/"],
            [],
        ),
        (
            "wild_type",
            "DNA",
            ["path/"],
            [],
        ),
    ],
)
def test_sequence_manifest(sequence_type, sequence_alphabet, local, s3):
    sources = Sources(local=local, s3=s3)

    manifest = SequenceManifest(
        sequence_type=sequence_type,
        sequence_alphabet=sequence_alphabet,
        sources=sources,
    )
    assert manifest.sequence_type == sequence_type
    assert manifest.sequence_alphabet == sequence_alphabet


@pytest.mark.parametrize(
    "sequence_type, sequence_alphabet, local, s3",
    [
        ("wild_type", None, ["path/"], []),
        (None, "DNA", ["path/"], []),
    ],
)
@pytest.mark.xfail(raises=ValidationError)
def test_sequence_manifest_missing_data(sequence_type, sequence_alphabet, local, s3):
    manifest = SequenceManifest(
        sequence_type=sequence_type,
        sequence_alphabet=sequence_alphabet,
        sources=Sources(dirs=Sources(local=local, s3=s3)),
    )
    assert len(manifest.sequence_type) > 0
    assert len(manifest.sequence_alphabet) > 0


@pytest.mark.parametrize(
    "name, version, description, creator, metadata, sequences",
    [
        (
            "TestName",
            "1.0",
            "A test dataset for validation",
            "John Doe",
            {"key": "value"},
            (
                "wild_type",
                "DNA",
                ["path/"],
                [],
            ),
        ),
    ],
)
def test_dataset_manifest(name, version, description, creator, metadata, sequences):
    sources = Sources(local=sequences[2], s3=sequences[3])
    sequence_manifest = SequenceManifest(
        sequence_type=sequences[0], sequence_alphabet=sequences[1], sources=sources
    )
    manifest = Manifest(
        name=name,
        version=version,
        description=description,
        creator=creator,
        metadata=metadata,
        sequences=[sequence_manifest],
    )
    assert len(manifest.name) >= 4
    assert len(manifest.description) >= 20


@pytest.mark.parametrize(
    "name, version, description, creator, metadata, sequences",
    [
        (
            "T",
            "1.0",
            "A test dataset for validation",
            "John Doe",
            {"key": "value"},
            (
                "wild_type",
                "DNA",
                ["path/"],
                [],
            ),
        ),
        (
            "Test",
            "1.0",
            "Short",
            "John Doe",
            {"key": "value"},
            (
                "wild_type",
                "DNA",
                ["path/"],
                [],
            ),
        ),
    ],
)
@pytest.mark.xfail(raises=ValidationError)
def test_dataset_manifest_invalid(
    name, version, description, creator, metadata, sequences
):
    sources = Sources(local=sequences[2], s3=sequences[3])
    sequence_manifest = SequenceManifest(
        sequence_type=sequences[0], sequence_alphabet=sequences[1], sources=sources
    )
    manifest = Manifest(
        name=name,
        version=version,
        description=description,
        creator=creator,
        metadata=metadata,
        sequences=[sequence_manifest],
    )
    assert len(manifest.name) >= 4
    assert len(manifest.description) >= 20


def test_dataset_manifest_from_toml():
    toml_path = TEST_MANIFEST_FILE
    manifest = Manifest.from_toml(toml_path)
    assert len(manifest.name) >= 4
    assert len(manifest.description) >= 20

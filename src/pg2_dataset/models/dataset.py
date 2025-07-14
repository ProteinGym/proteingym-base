from pathlib import Path
from typing import Annotated, Dict, List

from pydantic import BaseModel

from pg2_dataset.models.constants import DirType
from pg2_dataset.models.getter import DataDir
from pg2_dataset.models.manifest import DatasetManifest
from pg2_dataset.repositories.sequence import Sequence, SequenceFactory
from pg2_dataset.settings import datasets_dir


def assert_non_empty_sequence_list(v: List[Sequence]) -> List[Sequence]:
    if len(v) == 0:
        raise ValueError("At least one sequence is required.")
    return v


class Dataset(BaseModel):
    name: str
    description: str
    version: str
    sequences: Annotated[
        List[Sequence],
        lambda v: assert_non_empty_sequence_list(v),
    ]
    creator: str = None
    metadata: Dict[str, str] = None
    manifest: DatasetManifest = None

    @classmethod
    def from_manifest(cls, manifest: DatasetManifest) -> "Dataset":
        sequences = []
        for sequence_manifest in manifest.sequences:
            sequence_factory = SequenceFactory.from_manifest(manifest=sequence_manifest)
            sequences = sequences + sequence_factory.generate_sequences()

        return cls(
            name=manifest.name,
            description=manifest.description,
            version=manifest.version,
            creator=manifest.creator,
            metadata=manifest.metadata,
            sequences=sequences,
            manifest=manifest,
        )

    def dump(self, path: Path = None):
        if path is None:
            path = datasets_dir / self.name
        path.mkdir(parents=True, exist_ok=True)

        # Write sequences
        sequence_dir = DataDir(
            path=path / "sequences",
            dir_type=DirType.LOCAL,
        ).dump()
        for sequence in self.sequences:
            sequence.dump(sequence_dir)

        # Write manifest
        manifest_path = path / "manifest.toml"
        self.manifest.dump(manifest_path)

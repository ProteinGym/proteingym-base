from pathlib import Path
from typing import Annotated, Dict, List

from pydantic import AfterValidator, BaseModel

from pg2_dataset.constants import DirType
from pg2_dataset.models.getter import DataDir
from pg2_dataset.models.manifest import DatasetManifest, SequenceManifest, Sources
from pg2_dataset.repositories.sequence import Sequence, SequenceFactory
from pg2_dataset.settings import datasets_dir
from pg2_dataset.utils import zip_context


def assert_non_empty_sequence_list(v: List[Sequence]) -> List[Sequence]:
    if len(v) == 0:
        raise ValueError("At least one sequence is required.")
    return v


def length_validator(v, length: int):
    if len(v) < length:
        raise ValueError(f"Must be at least {length} characters long.")
    return v


class Dataset(BaseModel):
    name: Annotated[str, AfterValidator(lambda v: length_validator(v, 4))]
    description: Annotated[str, AfterValidator(lambda v: length_validator(v, 20))]
    version: str
    sequences: Annotated[
        List[Sequence],
        AfterValidator(lambda v: assert_non_empty_sequence_list(v)),
    ]
    creator: str = ""
    metadata: Dict[str, str] = {}
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

    @classmethod
    def from_manifest_toml(cls, path: str | Path) -> "Dataset":
        dataset_manifest = DatasetManifest.from_toml(path)
        return cls.from_manifest(dataset_manifest)

    @classmethod
    def from_zip(cls, path: str | Path) -> "Dataset":
        with zip_context(path) as zip_contents:
            manifest_files = [name for name in zip_contents if name.suffix == ".toml"]
            if len(manifest_files) > 1:
                raise ValueError(
                    f"Multiple manifest .toml files found in the \
                        ZIP archive: {manifest_files}"
                )
            elif not manifest_files:
                raise FileNotFoundError(
                    f"No manifest .toml found in the ZIP archive at {path}"
                )
            else:
                manifest_file = manifest_files[0]

            dataset_manifest = DatasetManifest.from_toml(manifest_file)
            return cls.from_manifest(dataset_manifest)

    def dump(self, path: str | Path = None):
        if path is None:
            path = datasets_dir / self.name
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        sequences_dir = path / "sequences"
        sequences_dir.mkdir(parents=True, exist_ok=True)
        # Write sequences
        sequence_dir = DataDir(
            path=sequences_dir,
            dir_type=DirType.LOCAL,
        )
        for sequence in self.sequences:
            sequence.dump(sequence_dir.path)

        # Write manifest
        if self.manifest is None:
            self.manifest = DatasetManifest(
                name=self.name,
                description=self.description,
                version=self.version,
                creator=self.creator,
                metadata=self.metadata,
                sequences=[
                    SequenceManifest(
                        sequence_type=self.sequences[0].type.value,
                        sequence_alphabet=self.sequences[0].alphabet.value,
                        sources=Sources(local=[str(sequence_dir.path)]),
                    )
                ],
            )
        self.manifest.dump(path)

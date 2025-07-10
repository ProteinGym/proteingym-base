from pydantic import BaseModel, Field, AfterValidator

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Annotated

import toml

from pg2_dataset.models.manifest import DatasetManifest
from pg2_dataset.repositories.sequence import Sequence, SequenceFactory
from pg2_dataset.models.getter import DataGetter, DataDir

class Dataset(BaseModel):
    name: str
    description: str
    version: str
    sequences: Annotated[List[Sequence], AfterValidator(lambda seqs: seqs if all(isinstance(seq, Sequence) for seq in seqs) else ValueError("All items must be of type Sequence."))]
    creator: str = None
    metadata: Dict[str, str] = None

    @classmethod
    def from_manifest(cls, manifest: DatasetManifest) -> 'Dataset':
        sequence_factory = SequenceFactory.create_from_list_of_dict(data=manifest.sequences)
        return cls(
            name = manifest.name,
            description = manifest.description,
            version = manifest.version,
            creator = manifest.creator,
            metadata = manifest.metadata,
            sequences = sequence_factory.generate_sequences()
        )
    
from pathlib import Path
from typing import Dict, List

import toml
from pydantic import BaseModel, Field


# Create manifest for sequence, currently supports only local and S3 directories.
# It can be extended to support xrefs.
class Sources(BaseModel):
    local: List[str] = Field(default_factory=list)
    s3: List[str] = Field(default_factory=list)

    def model_post_init(self, __context):
        if not self.local and not self.s3:
            raise ValueError(
                "At least one of 'local' or 's3' must be provided in sources"
            )


class SequenceManifest(BaseModel):
    """This is the manifest for Sequences. They can be loaded from multiple directories.
    This object is used to validate the sequence manifest."""

    sequence_type: str = Field(required=True)
    sequence_alphabet: str = Field(required=True)
    sources: Sources = Field(required=True)


class Manifest(BaseModel):
    name: str
    version: str = Field(description="Version of the dataset", required=True)
    description: str
    creator: str = Field(description="John Doe <john.doe@iff.com>")
    metadata: Dict[str, str] = Field(default_factory=dict)
    sequences: List[SequenceManifest] = Field(
        description="List of sequences dicts", required=True
    )

    @classmethod
    def from_toml(cls, path: str) -> "Manifest":
        data = toml.load(path)
        return cls(**data)

    def dump(self, path: Path, name: str = None) -> None:
        assert path.is_dir(), f"Provided path {path} is not a directory."
        if name:
            path = Path(path) / name
        else:
            path = path / f"{self.name}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            toml.dump(self.model_dump(), f)

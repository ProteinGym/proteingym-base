from pathlib import Path
from typing import Dict, List

import toml
from pydantic import BaseModel, Field


class DatasetManifest(BaseModel):
    name: str = Field(description="Name of the dataset", required=True)
    version: str = Field(description="Version of the dataset", required=True)
    description: str = Field(description="Description of the dataset", required=True)
    creator: str = Field(description="John Doe <john.doe@iff.com>")
    metadata: Dict[str, str] = Field(default_factory=dict)
    sequences: List[Dict] = Field(description="List of sequences dicts", required=True)

    @classmethod
    def from_toml(cls, path: str) -> "DatasetManifest":
        data = toml.load(path)
        return cls(**data)

    def dump(self, path: Path) -> None:
        assert path.is_dir(), f"Provided path {path} is not a directory."
        path = path / f"{self.name}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            toml.dump(self.model_dump(), f)

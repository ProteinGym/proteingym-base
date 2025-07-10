from pg2_dataset.models.dataset import Dataset
from pg2_dataset.models.manifest import DatasetManifest
from pg2_dataset.repositories.sequence import SequenceFactory
from typing import Dict
import toml

class ManifestRepository:
    @staticmethod
    def create_manifest_from_toml(path: str) -> DatasetManifest:
        data = toml.load(path)
        manifest = DatasetManifest(**data)
        return manifest


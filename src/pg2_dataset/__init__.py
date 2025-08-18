"""The protein gym 2 dataset.

A standardized format for storing and sharing datasets in the Protein Gym 2
ecosystem.

Attributes :
    Dataset :
        The main class for managing datasets.
    Manifest :
        Represents the metadata and resources of a dataset.  Entrypoint for
        loading and validating dataset from metadata.
"""

from .dataset import Dataset
from .manifest import Manifest

__all__ = [
    "Dataset",
    "Manifest",
]

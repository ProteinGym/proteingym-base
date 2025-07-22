import logging
from typing import List

from pydantic import BaseModel, Field

from pg2_dataset.models.getter import DataGetter
from pg2_dataset.models.sequence import Sequence, SequenceManifestSection

logger = logging.getLogger(__name__)


class SequenceFactory(BaseModel):
    sequence_type: str = Field(required=True)
    sequence_alphabet: str = Field(required=True)
    data_getters: DataGetter = None
    manifest_section: SequenceManifestSection = None

    @classmethod
    def from_manifest_section(
        cls,
        manifest: SequenceManifestSection,
    ) -> "SequenceFactory":
        sequence_type = manifest.sequence_type
        sequence_alphabet = manifest.sequence_alphabet
        sequence_sources = manifest.sources
        data_getter = DataGetter.from_sources(sequence_sources)

        return cls(
            sequence_type=sequence_type,
            sequence_alphabet=sequence_alphabet,
            data_getters=data_getter,
            manifest_section=manifest,
        )

    def generate_sequences(self) -> List[Sequence]:
        """
        Generate sequences from a list of dictionaries.
        """
        data_getter = self.data_getters
        sequences = []
        data = data_getter.get_data() if data_getter else None
        for record in data:
            sequences.append(
                Sequence(
                    name=record.name,
                    value=record.seq,
                    description=record.description,
                    type=self.sequence_type,
                    alphabet=self.sequence_alphabet,
                )
            )
        return sequences

import logging
from typing import List

from pg2_dataset.models.getter import DataGetter
from pg2_dataset.models.sequence import Sequence, SequenceManifestSection

logger = logging.getLogger(__name__)


class SequenceFactory:
    """Factory for generating `Sequence` objects from manifest sections.

    It provides the methods to generate `Sequence` instances from sequence
    manifest section. It provides method for generating `Sequences`.
    """

    def __init__(
        self,
        sequence_type: str,
        sequence_alphabet: str,
        data_getters: DataGetter = None,
        manifest_section: SequenceManifestSection = None,
    ):
        """Initialize `SequenceFactory`.

        Args:
        sequence_type (str): Type of sequence (e.g. wild_type, engineered_sequence).
        sequence_alphabet (str): The alphabet of the sequence (e.g. DNA, RNA, AA).
        data_getters (DataGetter): The data getter for retrieving sequence data.
        manifest_section (SequenceManifestSection): The manifest section
        describing the sequence.
        """
        self.sequence_type = sequence_type
        self.sequence_alphabet = sequence_alphabet
        self.data_getters = data_getters
        self.manifest_section = manifest_section

    @classmethod
    def from_manifest_section(
        cls,
        manifest_section: SequenceManifestSection,
    ) -> "SequenceFactory":
        """Creates a `SequenceFactory` from a `SequenceManifestSection`.

        Args:
            manifest_section (SequenceManifestSection): The manifest section containing
            sequence metadata and sources.

        Returns:
            SequenceFactory: An instance of SequenceFactory from the manifest section.
        """
        sequence_type = manifest_section.sequence_type
        sequence_alphabet = manifest_section.sequence_alphabet
        sequence_sources = manifest_section.sources
        data_getter = DataGetter.from_sources(sequence_sources)

        return cls(
            sequence_type=sequence_type,
            sequence_alphabet=sequence_alphabet,
            data_getters=data_getter,
            manifest_section=manifest_section,
        )

    def generate_sequences(self) -> List[Sequence]:
        """Generate a list of `Sequence` objects from the associated data sources.

        Returns:
            List[Sequence]: A list of generated Sequence objects.
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

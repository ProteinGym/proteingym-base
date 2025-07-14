import logging
from typing import Dict, List

from pydantic import BaseModel, Field

from pg2_dataset.models.getter import DataGetter
from pg2_dataset.models.sequence import Sequence

logger = logging.getLogger(__name__)


class SequenceFactory(BaseModel):
    data_getters: List[DataGetter] = None
    sequence_type: str = Field(required=True)
    sequence_alphabet: str = Field(required=True)

    @classmethod
    def create_from_list_of_dict(
        cls,
        data: List[Dict],
    ) -> "SequenceFactory":
        sequence_types = []
        sequence_alphabets = []
        data_getters = []
        for item in data:
            sequence_type = item.get("sequence_type")
            sequence_alphabet = item.get("sequence_alphabet")
            sequence_sources = item.get("sources")
            data_getter = (
                DataGetter.from_sources(sequence_sources) if sequence_sources else []
            )

            sequence_types.append(sequence_type)
            sequence_alphabets.append(sequence_alphabet)
            data_getters.append(data_getter)

        return SequenceFactory(
            data_getters=data_getters,
            sequence_type=sequence_types[0],
            sequence_alphabet=sequence_alphabets[0],
        )

    def generate_sequences(self) -> List[Sequence]:
        """
        Generate sequences from a list of dictionaries.
        """
        sequences = []
        for data_getter in self.data_getters:
            data = data_getter.get_data() if data_getter else None
            print(f"Data retrieved: {data}")
            for record in data:
                sequences.append(
                    Sequence(
                        name=record.name,
                        value=record.seq,
                        description=record.description,
                        sequence_type=self.sequence_type,
                        sequence_alphabet=self.sequence_alphabet,
                    )
                )
        return sequences

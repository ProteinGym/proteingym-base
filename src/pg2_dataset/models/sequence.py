from pydantic import BaseModel, Field
from typing import Any
import logging
logger = logging.getLogger(__name__)

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType



class Sequence(BaseModel):
    name: str
    value: Any
    description: str = Field(required=True)
    sequence_type: SequenceType = Field(required=True)
    sequence_alphabet: SequenceAlphabet = Field(required=True)

from typing_extensions import Self
from pydantic import BaseModel, model_validator


class MeasurementWithUncertainty(BaseModel):
    value: float
    uncertainty: float  # validate for positive

    @model_validator(mode="after")
    def uncertainty_check(self) -> Self:
        if self.uncertainty < 0.0:
            raise ValueError("uncertainty must be non negative.")
        return self


class Record(BaseModel, extra="allow"):
    engineering_round: int = 1
    sequence: str

    @model_validator(mode="after")
    def check_extra_fields(self) -> Self:
        allowed_types = (float, str, MeasurementWithUncertainty)
        for f in self.model_extra:
            if self.model_extra[f] is not None and not isinstance(self.model_extra[f], allowed_types):
                raise ValueError(f"Invalid data type for field {f}. Expected one of {allowed_types}. Got {type(self.model_extra[f])}.")
        return self

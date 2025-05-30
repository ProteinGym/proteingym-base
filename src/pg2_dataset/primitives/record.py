from typing import Self

from pydantic import BaseModel, PositiveFloat, model_validator


class MeasurementWithUncertainty(BaseModel):
    value: float
    uncertainty: PositiveFloat


class Record(BaseModel, extra="allow"):
    engineering_round: int = 1
    sequence: str

    @model_validator(mode="after")
    def check_extra_fields(self) -> Self:
        allowed_types = (int, float, str, MeasurementWithUncertainty)
        for f in self.model_extra:
            if self.model_extra[f] is not None and not isinstance(
                self.model_extra[f], allowed_types
            ):
                raise ValueError(
                    f"Invalid data type for field {f}. Expected one of {allowed_types}."
                    f" Got {type(self.model_extra[f])}."
                )
        return self
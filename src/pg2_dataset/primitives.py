from typing_extensions import Self
from typing import Annotated
from pydantic import BaseModel, model_validator, AfterValidator


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
    targets: list[str]

    @model_validator(mode="after")
    def check_extra_fields(self) -> Self:
        allowed_types = (float, str, MeasurementWithUncertainty)
        for f in self.model_extra:
            if self.model_extra[f] is not None and not isinstance(self.model_extra[f], allowed_types):
                raise ValueError(f"Invalid data type for field {f}. Expected one of {allowed_types}. Got {type(self.model_extra[f])}.")
        return self


class AssayMeta(BaseModel, extra="allow"):
    target: str
    # features: dict[str,type] #str is the key? would type be python <class 'something'> kind of format?
    description: str


def uri_check(uri):
    if ":" not in uri:
        raise ValueError("Invalid URI")
    return uri


class DatasetMeta(BaseModel):
    doi: Annotated[str, AfterValidator(uri_check)]
    source: Annotated[str, AfterValidator(uri_check)]
    # xref: CrossReference #how to define that?

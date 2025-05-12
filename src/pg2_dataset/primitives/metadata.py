from typing import Annotated

from pydantic import AfterValidator, BaseModel

from pg2_dataset.utils.strings import uri_check


class AssayMeta(BaseModel, extra="allow"):
    target: str
    # features: dict[str,type] #str is the key? would type be python
    # <class 'something'> kind of format?
    description: str


class DatasetMeta(BaseModel):
    doi: Annotated[str, AfterValidator(uri_check)]
    source: Annotated[str, AfterValidator(uri_check)]
    # xref: CrossReference #how to define that?

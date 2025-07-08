from pydantic import BaseModel, Field


class DatasetManifest(BaseModel):
    name: str = Field(
        description="Name of the dataset",
        required=True
    )
    version: str = Field(
        description="Version of the dataset",
        required=True
    )
    description: str = Field(
        description="Description of the dataset",
        required=True
    )
    creator: str = Field(
        description="John Doe <john.doe@iff.com>"
    )
    metadata: dict = Field(
    )
    sequences: list = Field(
        description="List of sequences dicts",
        required=True
    )
    
    @classmethod
    def from_toml(cls, path: str) -> 'DatasetManifest':
        import toml
        data = toml.load(path)
        return cls(**data)
    


from pydantic import BaseModel, model_validator

from pg2_dataset.io import exists


class Base(BaseModel):
    is_valid: bool | None = None

    @model_validator(mode="after")
    def set_is_valid(self):
        """Check if the dataset is valid by verifying the existence of the file path."""
        self.is_valid = exists(self.meta.file_path)

        return self

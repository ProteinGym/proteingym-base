from typing import Any

from pydantic import BaseModel, Field, create_model


class MMcifEntry(BaseModel):
    key: str
    value: str = ""


class MMcifTabular(BaseModel):
    headers: list[str]
    rows: list[list[str]]

    @staticmethod
    def _infer_type(value: str) -> Any:
        """Infer the data type of a value and convert it."""
        try:
            if "." in value:
                # TODO: This will break on urls etc
                return float(value)
            elif value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                return int(value)
        except ValueError:
            pass

        # Handle special cases
        if value == "?" or value == ".":
            return None

        # Default to string
        return value

    def _infer_column_type(self, column_values: list[str]) -> list[Any]:
        """Infer and convert types for an entire column."""
        return [self._infer_type(val) for val in column_values]

    def __getattr__(self, name: str) -> list[Any]:
        """Allow access to columns by header name (case-insensitive) with type
        inference"""
        name_lower = name.lower()

        header_indices = [
            i for i, h in enumerate(self.headers) if h.lower() == name_lower
        ]

        if not header_indices:
            # Also try with common variations (e.g., cartn_x vs Cartn_x)
            header_indices = [
                i
                for i, h in enumerate(self.headers)
                if h.lower().replace("_", "") == name_lower.replace("_", "")
            ]

        if header_indices:
            idx = header_indices[0]
            column_values = [row[idx] for row in self.rows]

            return self._infer_column_type(column_values)

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'. "
            f"Available columns: {', '.join(self.headers)}"
        )


class MMcifFile(BaseModel):
    """Main class for handling MMcif file data with dynamic field creation"""

    key_value_pairs: list[MMcifEntry] = Field(default_factory=list)
    tabular_data: dict[str, MMcifTabular] = Field(default_factory=dict)

    #######
    # We are parsing mainly two different objects in an MMCif file. key-value entries
    # and tabular entries
    # All entries are separated by # lines
    # Tabular data always start with a _loop line
    #######

    def __init__(self, **data):
        super().__init__(**data)

        fields = {}

        for kv in self.key_value_pairs:
            if kv.key.startswith("_"):
                parts = kv.key.lstrip("_").split(".")
                if len(parts) >= 2:
                    category = parts[0].lower()
                    # Join rest parts together for urls etc
                    field = ".".join(parts[1:]).lower()
                    field_name = f"{category}_{field}"

                    field_name = field_name.replace(".", "_")
                    field_name = field_name.replace("-", "_")
                    fields[field_name] = (str, kv.value)

        # Process tabular data
        for table_name, table in self.tabular_data.items():
            clean_name = table_name.lstrip("_").lower()
            clean_name = clean_name.replace(".", "_")
            clean_name = clean_name.replace("-", "_")
            fields[clean_name] = (MMcifTabular, table)

        # Create dynamic model
        if fields:
            dynamic_model = create_model("DynamicMMcifFile", **fields)
            dynamic_instance = dynamic_model(**{k: v[1] for k, v in fields.items()})

            for field_name, value in dynamic_instance:
                object.__setattr__(self, field_name, value)

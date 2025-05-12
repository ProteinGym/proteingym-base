from typing import Any

from pydantic import BaseModel, Field, create_model

from pg2_dataset.io.bytes import read_bytes


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

    @classmethod
    def from_file(cls, file_path: str) -> "MMcifFile":
        key_value_pairs = Field(default_factory=list)
        tabular_data = Field(default_factory=dict)

        data_str = read_bytes(file_path).decode("utf-8")
        lines = [line.strip() for line in data_str.splitlines() if line.strip()]

        # TODO: Should save the file header too if we want perfect conversion from
        #  file -> data -> file
        # file_header = lines[0]
        lines = lines[1:]

        is_tabular = False
        current_headers = []
        current_table_name = None

        i = 0
        # TODO: refactor this, too complicated
        while i < len(lines):
            line = lines[i]
            # breaklines
            if line.startswith("#"):
                is_tabular = False
                i += 1
                continue
            # start of tabular lines
            if line == "loop_":
                is_tabular = True
                current_headers = []
                current_table_name = None
                row_data = []
                i += 1
                continue
            # start tabular data
            if is_tabular:
                # headers of tabular data
                if line.startswith("_"):
                    header_line = line
                    if "." in header_line:
                        header_splits = header_line.split(".")
                        category = header_splits[0]
                        field = header_splits[1]
                        if current_table_name is None:
                            current_table_name = category
                        current_headers.append(field)
                    i += 1
                    continue
                # data of tabular data
                else:
                    if current_table_name and current_headers:
                        row = []
                        current_value = ""
                        in_quotes = False
                        for part in line.split():
                            if part.startswith('"'):
                                in_quotes = True
                                current_value += part + " "
                            elif part.endswith('"'):
                                in_quotes = False
                                current_value += part
                                row.append(current_value.strip().strip('"'))
                                current_value = ""
                            else:
                                if in_quotes:
                                    current_value += part + " "
                                else:
                                    row.append(part)

                        if row:
                            row_data.append(row)
                            clean_table_name = current_table_name.lstrip("_")
                            tabular_data[clean_table_name] = MMcifTabular(
                                headers=current_headers, rows=row_data
                            )

                        i += 1

                        continue
            # key-value pairs
            else:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key, value = parts
                    key_value_pairs.append(MMcifEntry(key=key, value=value))
                    i += 1
                # if key value pairs are multiline
                elif len(parts) != 2:
                    if line.startswith("_"):
                        key = line
                        value_string = ""
                        i += 1

                        if i < len(lines) and lines[i].startswith(";"):
                            multi_line_value = []
                            first_line = lines[i][1:].strip()
                            if first_line:  # Add first line if it has content
                                multi_line_value.append(first_line)
                            i += 1

                            while i < len(lines) and not (lines[i].strip() == ";"):
                                multi_line_value.append(lines[i].strip())
                                i += 1

                            if i < len(lines) and lines[i].strip() == ";":
                                i += 1

                            value_string = "\n".join(multi_line_value)
                            key_value_pairs.append(
                                MMcifEntry(key=key, value=value_string)
                            )
                        else:
                            key_value_pairs.append(
                                MMcifEntry(key=key, value=value_string)
                            )
                    else:
                        print(f"Unexpected line format: {line}")
                        i += 1
                continue
            i += 1

        return cls(key_value_pairs=key_value_pairs, tabular_data=tabular_data)

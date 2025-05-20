from functools import cached_property

from pydantic import computed_field, model_validator
from typing_extensions import Self

from pg2_dataset.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes
from pg2_dataset.primitives.structure import MMcifEntry, MMcifFile, MMcifTabular


class StructureDataset(Dataset):

    @computed_field
    @cached_property
    def raw_lines(self) -> list[str]:
        return self._from_cif()

    @computed_field
    @cached_property
    def structure(self) -> MMcifFile:
        if self.include_structure:
            if not hasattr(self, "raw_lines"):
                raise ValueError("No implementation of the raw_lines attribute")

            return self._to_mmcif(self.raw_lines)

        else:
            raise ValueError(
                """Either no implementation of the structure dataset,
                or include_structure is False
                """
            )

    @model_validator(mode="after")
    def configure_structure_file_path(self) -> Self:
        if self.file_path:
            return self

        elif (
            self.settings
            and self.settings.artifacts
            and self.settings.artifacts.structure
        ):
            self.file_path = self.settings.artifacts.structure
            return self

        else:
            raise ValueError("No structure file path provided.")

    def _to_mmcif(self, data: list[str]) -> MMcifFile:
        key_value_pairs = []
        tabular_data = {}

        # TODO: Should save the file header too
        # if we want perfect conversion from file -> data -> file
        # file_header = lines[0]
        lines = data[1:]

        is_tabular = False
        current_headers = []
        current_table_name = None

        i = 0
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

        return MMcifFile(key_value_pairs=key_value_pairs, tabular_data=tabular_data)

    def _from_cif(self) -> list[str]:
        data_str = read_bytes(self.file_path).decode("utf-8")
        lines = [line.strip() for line in data_str.splitlines() if line.strip()]

        return lines

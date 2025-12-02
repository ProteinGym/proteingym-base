from pathlib import Path
from typing import IO, Annotated, Any, Callable

import toml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    field_serializer,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from semver import Version

from .assay import AssayManifestSection, AssayTarget, AssayVariable
from .msa import MSAManifestSection
from .sequence import SequenceManifestSection
from .structure import StructureManifestSection


class _VersionPydanticAnnotation:
    """A version class to represent semantic versions.

    Docs:
        https://docs.pydantic.dev/latest/api/pydantic_extra_types_semantic_version/
        https://python-semver.readthedocs.io/en/latest/advanced/combine-pydantic-and-semver.html
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        """See https://docs.pydantic.dev/latest/concepts/types/#customizing-validation-with-__get_pydantic_core_schema__"""
        _ = source_type
        _ = handler

        def validate_from_str(value: str) -> Version:
            return Version.parse(value)

        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(Version),
                    from_str_schema,
                ]
            ),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """See https://docs.pydantic.dev/latest/concepts/json_schema/#implementing-__get_pydantic_json_schema__"""
        _ = core_schema
        return handler(core_schema.str_schema())


MANIFEST_LATEST_VERSION: Version = Version(1, 0)
"""The latest version of the manifest schema."""


class Manifest(BaseModel):
    """Dataset manifest representing a dataset's metadata and resources.

    A programmatic representation of a dataset's manifest used for validation
    and loading data. The fields have Python built-in data types, the Protein
    Gym data types are constructed while loading the dataset.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    version: Annotated[Version, _VersionPydanticAnnotation]
    """The version of the manifest schema.

    The version follows the semantic version format: `<major>.<minor>.<patch>`
    A major version change indicates breaking changes, while a minor version
    change indicates backward-compatible additions or changes. A patch version
    change indicates bug fixes or minor improvements.
    """

    name: str
    """The name of the dataset."""

    description: str | None = None
    """A brief description of the dataset."""

    assay_variables: list[AssayVariable] = Field(default_factory=list)
    """The variables for the assays defined in the dataset."""

    assay_targets: list[AssayTarget] = Field(default_factory=list)
    """The targets for the assays defined in the dataset."""

    assays: list[AssayManifestSection] = Field(default_factory=list)
    """The assays included in the dataset."""

    sequences: list[SequenceManifestSection] = Field(default_factory=list)
    """The sequences included in the dataset."""

    structures: list[StructureManifestSection] = Field(default_factory=list)
    """The structures included in the dataset."""

    msas: list[MSAManifestSection] = Field(default_factory=list)
    """The multiple sequence alignments included in the dataset."""

    @model_validator(mode="after")
    def _validate_assay_variables(self) -> "Manifest":
        """Validate that all assay variables are defined in the manifest."""
        defined_variable_names = {variable.name for variable in self.assay_variables}
        for assay in self.assays:
            undefined_variable_names = (
                set(assay.variables.keys()) - defined_variable_names
            )
            if undefined_variable_names:
                raise ValueError(
                    f"Assay {assay.name} contains undefined variables:"
                    f"{undefined_variable_names}"
                )
        return self

    @model_validator(mode="after")
    def _validate_assay_targets(self) -> "Manifest":
        """Validate that all assay targets are defined in the manifest."""
        defined_target_names = {target.name for target in self.assay_targets}
        for assay in self.assays:
            undefined_target_names = set(assay.targets.keys()) - defined_target_names
            if undefined_target_names:
                raise ValueError(
                    f"Assay {assay.name} contains undefined targets:"
                    f"{undefined_target_names}"
                )
        return self

    @classmethod
    def from_path(cls, path: Path | str | IO["str"]) -> "Manifest":
        """Create a Manifest instance from a TOML file or string."""
        if isinstance(path, str):  # User-friendly interface to support str
            path = Path(path)
        context = {
            # Resolve paths defined as relative paths to the manifest file
            "relative_to_path": path.parent if isinstance(path, Path) else None,
        }
        return cls.model_validate(toml.load(path), context=context)

    @field_serializer("version")
    def serialize_version(self, version: Version) -> str:
        """Serialize the version to a string."""
        return str(version)

    def dump(self, *, path: Path | str | None = None) -> Path:
        """Dump the manifest to a TOML file.

        The paths in the manifest are serialized as relative paths to the
        manifest path.

        Args:
            path (Path | str | None): The path to dump the manifest to. If None,
              the current working directory is used as path. If path is a
              directory, the manifest name is used as file name. Defaults to None.

        Returns:
            Path: The path to the dumped manifest file.
        """
        if isinstance(path, str):  # User-friendly interface to support str
            path = Path(path)
        path = path or Path.cwd()
        if path.is_dir():
            path /= f"{self.name}.toml"
        # Empty or None values indicate the fields were not set, hence excluded
        # them from the dump.
        include = {key for key, value in self.model_dump().items() if value}
        context = {"relative_to_path": path.parent}
        with path.open("w", encoding="utf-8") as f:
            toml.dump(self.model_dump(include=include, context=context), f)
        return path

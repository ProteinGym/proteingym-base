import sys
from abc import ABC
from importlib.util import find_spec
from typing import ClassVar, Generic, TypeVar

packages = {
    "biotite": find_spec("biotite") is not None,
    "biopython": find_spec("Bio") is not None,
}
if packages["biotite"]:
    pass  # biotite installed
elif packages["biopython"]:
    pass  # biopython installed
else:
    raise ImportError("Neither Biopython nor Biotite is installed.")

T = TypeVar("T")
search_order = ["Bio", "biotite"]


class BackendSearchOrder:
    def __init__(self, order: list[str]):
        self.order = order

    def __enter__(self):
        sys.modules[__name__].search_order = self.order

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.modules[__name__].search_order = ["Bio", "biotite"]


class AbstractBackendManager(ABC, Generic[T]):
    """Base class for backend managers that handle loading data."""

    name: ClassVar[str] = ""
    backend_map: ClassVar[dict] = {}

    def __init_subclass__(cls, **kwargs):
        if cls.name:  # Only register subclasses with non-empty names
            cls.backend_map[cls.name] = cls, find_spec(cls.name)

    @classmethod
    def get_available_manager(cls) -> type["AbstractBackendManager"]:
        """Get an appropriate manager based on available libraries.

        Returns:
            type[AbstractBackendManager]: The selected manager class.

        Raises:
            ImportError: If no suitable manager is found.
        """
        for backend in search_order:
            manager_class, is_available = cls.backend_map[backend]
            if is_available:
                return manager_class
        raise ImportError(
            "No suitable manager found. Please install either biopython or biotite."
        )


class AbstractStructureManager(AbstractBackendManager[T]):
    """Base class for structure managers."""

    backend_map: ClassVar[dict] = {}


class AbstractMSAManager(AbstractBackendManager[T]):
    """Base class for MSA managers."""

    backend_map: ClassVar[dict] = {}

import dataclasses
from pathlib import Path

from .dataset import Dataset, DatasetSlice


@dataclasses.dataclass(kw_only=True, frozen=True)
class Superset:
    """A set of datasets.

    References:
    ../../docs/decisions/0004-dataset-splits.md
    """

    dataset: Dataset
    """The dataset to which this superset belongs."""

    slices: list[DatasetSlice] = dataclasses.field(default_factory=list)
    """The slices that belong to this superset.

    TODO: Also support a dict `dict[str, DatasetSlice]` that maps split methods
    to slices.
    """

    def __iter__(self):
        """Iterate over the slices in this superset."""
        for slc in self.slices:
            yield self.dataset[slc]

    @classmethod
    def from_path(cls, path: Path) -> "Superset":
        """Create a `Superset` from a superset archive.

        Args:
            path: The path to the superset archive.

        Returns:
            The superset in the archive.
        """
        return cls(dataset=Dataset(name="TODO"), slices=[])

    def dump(self, *, path: Path | str | None = None) -> Path:
        """Dump the superset.

        Args:
            path (Path | str | None): The path to dump the dataset in. If None,
                the current working directory is used. Defaults to None.

        Returns:
            Path: The path to the dumped dataset archive.
        """
        if isinstance(path, str):  # User-friendly interface to support str
            path = Path(path)
        path = path or Path.cwd()
        return path

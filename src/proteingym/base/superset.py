import dataclasses

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

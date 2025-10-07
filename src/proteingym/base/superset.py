import dataclasses
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .dataset import Dataset, DatasetArchiveLayout, DatasetSlice


class SupersetArchiveLayout:
    """The layout of a superset archive."""

    SUFFIX = ".splits.pgdata"
    """The suffix of a superset archive."""

    DATASET_ARCHIVE = f"dataset{DatasetArchiveLayout.SUFFIX}"
    """The directory containing the dataset."""

    SLICES_FILE = "slices.json"
    """The file containing the slices."""


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
        """Create a `Superset` from an archive.

        Extract the contents to a temporary directory and load the dataset
        from the manifest file.

        Args:
            path: The path to the superset archive.

        Returns:
            The superset from the archive

        Raises:
            ValueError: If multiple manifest files are found in the ZIP archive.
            FileNotFoundError: If no manifest file is found in the ZIP archive.
        """
        # While a SE practice is to avoid IO to disk where possible,
        # we use a temporary directory here as long as dataset dump requires
        # it.
        with ZipFile(path, "r") as zip, TemporaryDirectory() as temp_dir:
            dataset_archive = zip.extract(
                SupersetArchiveLayout.DATASET_ARCHIVE, path=temp_dir
            )
            dataset = Dataset.from_path(dataset_archive)
            slices_str = json.loads(zip.read(SupersetArchiveLayout.SLICES_FILE))
            slices = [DatasetSlice(**slc) for slc in slices_str]
        return cls(dataset=dataset, slices=slices)

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
        if path.is_dir():
            path = path / f"{self.dataset.name}{SupersetArchiveLayout.SUFFIX}"
        with ZipFile(path, "w") as zip:
            # While a SE practice is to avoid IO to disk where possible,
            # we use a temporary directory here as long as dataset dump requires
            # it.
            with TemporaryDirectory() as temp_dir:
                dataset_archive = self.dataset.dump(path=Path(temp_dir))
                zip.write(
                    dataset_archive, arcname=SupersetArchiveLayout.DATASET_ARCHIVE
                )
            slices_str = json.dumps([dataclasses.asdict(slc) for slc in self.slices])
            zip.writestr(SupersetArchiveLayout.SLICES_FILE, slices_str)
        return path

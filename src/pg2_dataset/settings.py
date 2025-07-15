from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.resolve()

# Default paths for dataset components
datasets_dir = root_dir / "datasets"

_DEFAULT_ASSAYS_FILE = Path("assays.csv")
_DEFAULT_STRUCTURE_DIR = Path("structure")
_DEFAULT_MANIFEST_FILE = Path("manifest.toml")

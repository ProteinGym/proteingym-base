from typing import Annotated
from pathlib import Path
import typer

from pg2_dataset.models.dataset import Dataset, Manifest

app = typer.Typer(
    name="pg2-dataset",
    help="Command line interface for managing PG2 datasets.",
)


@app.callback(invoke_without_command=True)
def main(
):
    """Main entry point for the CLI."""
    typer.echo("Welcome to the PG2 Dataset CLI!")


@app.command("build")
def build(
    manifest_path: Annotated[str, typer.Argument(help="Path to the manifest file")],
    path: Annotated[Path, typer.Option("--path", help="Path to the output directory")] = None,
):
    """Creates a Dataset instance from a manifest TOML file.

    Args:
        manifest_path: The path to the manifest TOML file.
        path: The directory path to dump the dataset archive.
    """

    dataset_manifest = Manifest.from_path(manifest_path)
    dataset = Dataset.from_manifest(dataset_manifest)
    archive_path = dataset.dump(path=path)
    typer.echo(f"Dataset dumped to: {archive_path}")


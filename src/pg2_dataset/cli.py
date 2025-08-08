from pathlib import Path
from typing import Annotated

import typer

from pg2_dataset.models.dataset import Dataset, Manifest

app = typer.Typer(
    name="pg2-dataset",
    help="Command line interface for managing PG2 datasets.",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Main entry point for the CLI."""
    if ctx.invoked_subcommand is None:
        typer.echo("Welcome to the PG2 Dataset CLI!")
        typer.echo("Use --help to see available commands.")


@app.command("build")
def build(
    manifest_path: Annotated[Path, typer.Argument(help="Path to the manifest file")],
    path: Annotated[
        Path, typer.Option("--path", help="Path to the output directory")
    ] = None,
):
    """Creates a Dataset instance from a manifest TOML file and dumps it as zip to a
    specified directory path.
    Args:
        manifest_path: The path to the manifest TOML file.
        path: The directory path to dump the dataset archive.
    """
    dataset_manifest = Manifest.from_path(manifest_path)
    dataset = Dataset.from_manifest(dataset_manifest)
    archive_path = dataset.dump(path=path)
    typer.echo(f"Dataset dumped to: {archive_path}")

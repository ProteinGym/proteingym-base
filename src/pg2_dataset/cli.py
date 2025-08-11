from pathlib import Path
from typing import Annotated

import typer

from pg2_dataset.__about__ import __version__
from pg2_dataset.models.dataset import Dataset, Manifest

app = typer.Typer(
    name="pg2-dataset",
    help="CLI for managing ProteinGym2 (PG2) Dataset(s).",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", help="Show version and exit")
    ] = False,
) -> None:
    """Main entry point for the CLI.

    Args:
        ctx: The context for the CLI.
        version: If True, show the version and exit.

    Returns: None

    Raises:
        typer.Exit: If version is True, exits after showing the version.
    """

    if version:
        typer.echo(f"v{__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        typer.echo("Welcome to the PG2 Dataset CLI!")
        typer.echo("Use --help to see available commands.")


@app.command("build")
def build(
    manifest_path: Annotated[Path, typer.Argument(help="Path to the manifest file")],
    output_path: Annotated[
        Path | None, typer.Option("--output-path", help="Path to the output directory")
    ] = None,
):
    """Creates a Dataset instance from a manifest TOML file and dumps it as zip to a
    specified directory path.

    Args:
        manifest_path: The path to the manifest TOML file.
        output_path: The directory path to dump the dataset archive.

    Returns:
        None

    Outputs:
        A zip file containing the dataset, saved in the specified path.
    """

    typer.echo("Loading manifest...")
    dataset_manifest = Manifest.from_path(manifest_path)

    typer.echo("Building dataset...")
    dataset = Dataset.from_manifest(dataset_manifest)

    typer.echo("Building dataset archive...")
    archive_path = dataset.dump(path=output_path)
    typer.echo(f"Dataset {dataset.name} archived to: {archive_path}")

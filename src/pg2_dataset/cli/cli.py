from typing import Annotated

import typer

from pg2_dataset.models.dataset import Dataset, Manifest

app = typer.Typer()


@app.command("create")
def create(
    manifest_path: str = Annotated[str, typer.Option(help="Path to the manifest file")],
):
    """Creates a Dataset instance from a manifest TOML file.

    Args:
        manifest_path: The path to the manifest TOML file.
    """

    dataset_manifest = Manifest.from_path(manifest_path)
    dataset = Dataset.from_manifest(dataset_manifest)
    typer.echo(f"Dataset created with name: {dataset.name}")

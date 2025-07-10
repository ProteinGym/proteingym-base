import typer

from pg2_dataset.models.dataset import Dataset
from pg2_dataset.models.manifest import DatasetManifest

app = typer.Typer()


@app.command()
def create_new():
    """Create a new dataset."""
    typer.echo("Not implemented!")


@app.command()
def create_from_toml(path: str = typer.Argument(..., help="Path to the TOML file")):
    dataset_manifest = DatasetManifest.from_toml(path)
    dataset = Dataset.from_manifest(dataset_manifest)

    typer.echo(f"Created dataset from {path}")
    typer.echo(f"Dataset Name: {dataset}")

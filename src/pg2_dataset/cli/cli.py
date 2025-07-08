import typer

app = typer.Typer()

from pg2_dataset.models.manifest import DatasetManifest
from pg2_dataset.models.dataset import Dataset

@app.command()
def create_new():
    """Create a new dataset."""
    typer.echo(f"Not implemented!")


@app.command()
def create_from_toml(
    path: str = typer.Argument(..., help="Path to the TOML file")
):
    dataset_manifest = DatasetManifest.from_toml(path)
    dataset = Dataset.from_manifest(dataset_manifest)
    
    typer.echo(f"Created dataset from {path}")
    typer.echo(f"Dataset Name: {dataset}")


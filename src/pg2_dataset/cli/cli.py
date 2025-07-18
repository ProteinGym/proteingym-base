import typer

from pg2_dataset.models.dataset import Dataset
from pg2_dataset.models.manifest import Manifest

app = typer.Typer()
create_app = typer.Typer()

app.add_typer(create_app, name="create")


# Create commands
@create_app.command("from-toml")
def create_from_toml(path: str = typer.Argument(..., help="Path to the TOML file")):
    dataset_manifest = Manifest.from_toml(path)
    dataset = Dataset.from_manifest(dataset_manifest)

    typer.echo(f"Created dataset from {dataset.name}")
    typer.echo(f"Number of sequences: {len(dataset.sequences)}")

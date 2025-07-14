import typer

from pg2_dataset.models.dataset import Dataset
from pg2_dataset.models.manifest import DatasetManifest

app = typer.Typer()
create_app = typer.Typer()

app.add_typer(create_app, name="create")


# Create commands
@create_app.command("from-toml")
def create_from_toml(path: str = typer.Argument(..., help="Path to the TOML file")):
    print(f"Creating dataset from TOML file at {path}")
    dataset_manifest = DatasetManifest.from_toml(path)
    dataset = Dataset.from_manifest(dataset_manifest)
    typer.echo(f"Created dataset from {dataset.name}")

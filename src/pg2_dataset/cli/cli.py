import typer

from pg2_dataset.models.dataset import Dataset

app = typer.Typer()
create_app = typer.Typer()

app.add_typer(create_app, name="create")


# Create commands
@create_app.command("from-manifest")
def create_from_manifest(
    path: str = typer.Argument(..., help="Path to the manifest file"),
):
    dataset = Dataset.from_manifest_toml(path)

    typer.echo(f"Created dataset from {dataset.name}")
    typer.echo(f"Number of sequences: {len(dataset.sequences)}")


@create_app.command("from-zip")
def create_from_zip(path: str = typer.Argument(..., help="Path to the ZIP file")):
    dataset = Dataset.from_zip(path)

    typer.echo(f"Created dataset from ZIP file: {dataset.name}")
    typer.echo(f"Number of sequences: {len(dataset.sequences)}")

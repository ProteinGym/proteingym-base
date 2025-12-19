import json
import logging
from pathlib import Path
from typing import Annotated

import click
import typer
from pydantic import ValidationError

from .__about__ import __version__
from .data_generators import (
    adjust_target_with_two_dummy_features,
    charge_ladder_dataset,
)
from .dataset import Dataset
from .manifest import Manifest
from .model import ModelCard, ModelProject

logger = logging.getLogger("proteingym.base")

app = typer.Typer(
    name="proteingym-base",
    help="CLI for handling ProteinGym resources",
)


def setup_logger(*, level: int = logging.CRITICAL) -> None:
    """Set up the logger for the application.

    Args:
        level (int): The logging level to set. Defaults to
            `logging.CRITICAL`.
    """
    logger = logging.getLogger("proteingym.base")
    logger.setLevel(level)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
    version: Annotated[
        bool, typer.Option("--version", help="Show version and exit")
    ] = False,
) -> None:
    """Main entry point for the CLI.

    Args:
        ctx (typer.Context): The context for the CLI.
        verbose (int): The verbosity level. Use `-v` or `--verbose` to increase
            verbosity. Each `-v` increases the verbosity level:
            0: CRITICAL, 1: ERROR, 2: WARNING, 3: INFO, 4: DEBUG.
            Defaults to 0 (CRITICAL).
        version (bool): If `True`, show the package version. Defaults to `False`.

    Raises:
        typer.Exit: If version is `True`, exits after showing the version.
    """
    setup_logger(level=logging.CRITICAL - verbose * 10)

    if version:
        typer.echo(f"v{__version__}")
        raise typer.Exit()

    if not ctx.invoked_subcommand:
        typer.echo("Welcome to the PG2 Dataset CLI!")
        typer.echo("Use --help to see available commands.")


@app.command("build")
def build(
    manifest_path: Annotated[Path, typer.Argument(help="Path to the manifest file")],
    output_path: Annotated[
        Path | None, typer.Option("--output-path", help="Path to the output directory")
    ] = None,
):
    """Build a ProteinGym2 Dataset from manifest.

    Creates a Dataset instance from a manifest TOML file and dumps it as zip to a
    specified directory path.

    Args:
        manifest_path (Path): The path to the manifest TOML file.
        output_path (Path | None): The directory path to dump the dataset archive. If
            `None`, the current working directory is used. Defaults to `None`.


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


@app.command("validate")
def validate_model(
    project_path: Annotated[
        Path,
        typer.Argument(
            help="Root path to the model project",
            exists=True,
            resolve_path=True,
        ),
    ],
):
    """Validate a model from path."""

    logger = logging.getLogger("proteingym.base")

    try:
        model_project = ModelProject.from_path(project_path)
        typer.echo(
            f"✅ Model {model_project.project['name']} loaded successfully "
            f"with entry points: {model_project.entry_points}"
        )

        model_card = ModelCard.from_path(project_path / "README.md")
        typer.echo(
            f"✅ Loaded {model_card.name} with hyper parameters: "
            f"{model_card.hyper_parameters}."
        )
    except ValueError as e:
        typer.echo(f"❌ Validation failed: {str(e)}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        logger.error("❌ Error running validation", exc_info=e)
        raise typer.Exit(1) from e


@app.command("list-datasets")
def list_datasets(
    path: Annotated[
        Path,
        typer.Argument(
            help="Directory path containing .pgdata dataset archives",
            exists=True,
            file_okay=True,
            dir_okay=True,
        ),
    ],
):
    """List available datasets with optional query filtering."""

    def find_datasets_with_paths(root_path: Path) -> list[dict]:
        """Find all .pgdata datasets in the given directory."""
        datasets_with_paths = []

        if root_path.is_file():
            paths = [path]
        else:
            paths = root_path.rglob("*.pgdata")

        for model_path in paths:
            dataset = Dataset.from_path(model_path)
            dataset_data = json.loads(dataset.model_dump_json())

            dataset_entry = {
                **dataset_data,
                "input_filename": model_path.resolve().as_posix(),
            }

            datasets_with_paths.append(dataset_entry)

        return datasets_with_paths

    datasets_with_paths = find_datasets_with_paths(root_path=path)

    output = json.dumps(datasets_with_paths, indent=2)
    typer.echo(output, nl=False)


@app.command("list-models")
def list_models(
    path: Annotated[
        Path,
        typer.Argument(
            help="Directory path containing model cards",
            exists=True,
            file_okay=True,
            dir_okay=True,
        ),
    ],
):
    """List available models with optional query filtering.

    Note: This custom CLI is used instead of yq because:
    - Parses Markdown files with model card frontmatter, not just YAML/JSON
    - Provides sophisticated error handling with ValidationError logging
    - Creates custom JSON output with both model data and file metadata
    - Includes recursive file discovery for .md files
    - Leverages Pydantic validation for type safety and schema compliance
    """

    def find_models_with_paths(root_path: Path) -> list[dict]:
        """Find all model cards in the given directory."""
        models_with_paths = []

        if root_path.is_file():
            paths = [root_path]
        else:
            paths = root_path.rglob("*.md")

        for model_path in paths:
            try:
                model = ModelCard.from_path(model_path)
            except ValidationError as e:
                logger.error(f"Skipping {model_path}", exc_info=e)
            else:
                model_entry = {
                    **model.model_dump(),
                    "input_filename": model_path.resolve().as_posix(),
                }

                models_with_paths.append(model_entry)

        return models_with_paths

    models_with_paths = find_models_with_paths(root_path=path)

    output = json.dumps(models_with_paths, indent=2)
    typer.echo(output, nl=False)


@app.command("generate-data")
def generate_data(
    feature1: Annotated[
        str,
        typer.Argument(help="Name of the first dummy feature"),
    ] = "foo",
    feature2: Annotated[
        str,
        typer.Argument(help="Name of the second dummy feature"),
    ] = "bar",
    *,
    n_rows: Annotated[
        int, typer.Option(help="Number of rows to generate in a data frame")
    ] = 500,
    sequence_length: Annotated[
        int, typer.Option(help="Length of sequence for the sequence column")
    ] = 100,
    fmt: Annotated[
        str,
        typer.Option(
            help="Output format",
            click_type=click.Choice(choices=["csv"], case_sensitive=False),
        ),
    ] = "csv",
) -> None:
    """Generate dummy data with charge ladder and two dummy features.

    Creates a charge ladder dataset with protein sequences and adds two dummy
    features to the target charge column. The output is formatted as CSV.
    Users can update feature names, but it is currently limited to only two features.

    Args:
        feature1: Name of the first dummy feature. Defaults to "foo".
        feature2: Name of the second dummy feature. Defaults to "bar".
        n_rows: Number of rows to generate in the data frame. Defaults to 500.
        sequence_length: Length of sequence for the sequence column. Defaults to 100.
        fmt: Output format. Currently only supports "csv". Defaults to "csv".

    Outputs:
        Prints the generated CSV data to stdout.
    """
    ladder = charge_ladder_dataset(n_rows, sequence_length)

    output = ladder.pipe(
        adjust_target_with_two_dummy_features,
        target="charge",
        feature_names=[feature1, feature2],
    )

    if fmt.lower() == "csv":
        typer.echo(output.write_csv(), nl=False)


if __name__ == "__main__":
    app()

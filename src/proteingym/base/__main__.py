import logging
from pathlib import Path
from typing import Annotated

import typer

from .__about__ import __version__
from .dataset import Dataset
from .manifest import Manifest
from .model import ModelCard, ModelProject

app = typer.Typer(
    name="proteingym-base",
    help="CLI for handling ProteinGym resources",
)


def setup_logger(*, level: int = logging.CRITICAL) -> None:
    """Set up the logger for the application.

    Args:
        log_level (int): The logging level to set. Defaults to
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
            f"✅ Model {model_project.project.name} loaded successfully "
            f"with entry points: {model_project.entry_points}"
        )

        model_card = ModelCard.from_path(project_path / "README.md")
        typer.echo(
            f"✅ Loaded {model_card.name} with hyper parameters: "
            f"{model_card.hyper_params}."
        )
    except ValueError as e:
        typer.echo(f"❌ Validation failed: {str(e)}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        logger.error("❌ Error running validation", exc_info=e)
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from .__about__ import __version__
from .dataset import Dataset
from .manifest import Manifest
from .model import ModelCard

logger = logging.getLogger("proteingym.base")


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
    """List available models with optional query filtering."""

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
    typer.echo(output)


if __name__ == "__main__":
    app()

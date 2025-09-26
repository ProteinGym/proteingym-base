import json
import logging
from pathlib import Path
from typing import Annotated, Dict, List

import typer
import yaml

from pg2_dataset import Dataset, Manifest
from pg2_dataset.__about__ import __version__

app = typer.Typer(
    name="pg2-dataset",
    help="CLI for managing ProteinGym2 (PG2) Dataset(s).",
)


def setup_logger(*, level: int = logging.CRITICAL) -> None:
    """Set up the logger for the application.

    Args:
        log_level (int): The logging level to set. Defaults to
           `logging.CRITICAL`.
    """
    logger = logging.getLogger("pg2_dataset")
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


@app.command("list")
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
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: json or yaml",
        ),
    ] = "json",
):
    """List available datasets with optional query filtering."""
    logger = logging.getLogger("pg2_dataset")

    def find_datasets(path: Path) -> List[Dict]:
        """Find all .pgdata datasets in the given directory."""
        datasets = []

        if path.is_file():
            if path.suffix != "pgdata":
                typer.echo(
                    f"Only files with '.pgdata' suffix are supported. "
                    f"The input file is: '{path.suffix}'."
                )
                raise typer.Exit(1)

            dataset = Dataset.from_path(path)
            dataset_with_path = {**dataset.model_dump(), "path": str(path.resolve())}

            datasets.append(dataset_with_path)

        else:
            for file_path in path.rglob("*.pgdata"):
                dataset = Dataset.from_path(file_path)
                dataset_with_path = {
                    **dataset.model_dump(),
                    "path": str(file_path.resolve()),
                }

                datasets.append(dataset_with_path)

        return datasets

    def format_output(datasets: List[Dict], output_format: str) -> str:
        """Format the datasets for output."""
        if output_format.lower() == "json":
            return json.dumps(datasets, indent=2)
        elif output_format.lower() == "yaml":
            return yaml.dump(datasets, default_flow_style=False)
        else:
            logger.warning(f"Unsupported dataset output format: {output_format}")

    datasets = find_datasets(path)

    output = format_output(datasets, format)
    typer.echo(output)


if __name__ == "__main__":
    app()

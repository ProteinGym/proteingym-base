from typer.testing import CliRunner

from pg2_dataset.cli.cli import app


def test_cli_callback() -> None:
    """CLI runs the callback function when invoked."""
    runner = CliRunner()
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "Welcome to the PG2 Dataset CLI!" in result.stdout


def test_cli_help() -> None:
    """CLI shows help message when --help is used."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Command line interface for managing PG2 datasets" in result.stdout
    assert "build" in result.stdout


def test_build_command_help() -> None:
    """Build command shows help message when --help is used."""
    runner = CliRunner()
    result = runner.invoke(app, ["build", "--help"])

    assert result.exit_code == 0
    assert "Creates a Dataset instance from a manifest TOML file" in result.stdout


def test_build_command_missing_manifest() -> None:
    """Build command fails when manifest file doesn't exist."""
    runner = CliRunner()
    result = runner.invoke(app, ["build", "bad_file.toml"])

    assert result.exit_code == 1

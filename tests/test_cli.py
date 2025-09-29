from pathlib import Path

from typer.testing import CliRunner

from proteingym.base.__about__ import __version__
from proteingym.base.__main__ import app


def test_cli_callback() -> None:
    """CLI runs the callback function when invoked."""

    runner = CliRunner()
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "Welcome to the PG2 Dataset CLI!" in result.stdout


def test_cli_version() -> None:
    """CLI shows version when --version is used."""

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.startswith("v")
    assert __version__ in result.stdout


def test_cli_help() -> None:
    """CLI shows help message when --help is used."""

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "build" in result.stdout
    assert "version" in result.stdout


def test_build_command_help() -> None:
    """Build command shows help message when --help is used."""

    runner = CliRunner()
    result = runner.invoke(app, ["build", "--help"])

    assert result.exit_code == 0
    assert "Creates a Dataset instance from a manifest TOML file" in result.stdout
    assert "manifest_path" in result.stdout
    assert "output_path" in result.stdout


def test_build_command_invalid_manifest_contents(tmp_path: Path) -> None:
    """Build command fails with invalid manifest contents."""

    invalid_manifest = tmp_path / "invalid_manifest.toml"
    invalid_manifest.write_text("""
    description = "Invalid manifest"
    """)
    runner = CliRunner()
    result = runner.invoke(app, ["build", str(invalid_manifest)])
    assert result.exit_code == 1
    assert "validation errors for Manifest" in str(result.exception)


def test_build_command_with_output_path(tmp_path: Path) -> None:
    """Build command respects custom output path."""

    manifest = tmp_path / "test_manifest.toml"
    dataset_name = "test-dataset"
    manifest.write_text(f"""
    name = "{dataset_name}"
    version = "1.0.0"
    description = "Test dataset"
    """)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        app, ["build", manifest.as_posix(), "--output-path", output_dir.as_posix()]
    )
    assert (output_dir / f"{dataset_name}.pgdata").as_posix() in result.stdout

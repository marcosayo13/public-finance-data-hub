"""Command-line interface for Public Finance Data Hub."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
import yaml

from public_finance_data_hub.utils.logging import setup_logging
from public_finance_data_hub.storage.lake import DataLake
from public_finance_data_hub.connectors.google_drive import GoogleDriveConnector
from public_finance_data_hub.pipelines.ingest_bcb import ingest_bcb_series
from public_finance_data_hub.pipelines.ingest_b3 import ingest_b3_cotahist
from public_finance_data_hub.pipelines.ingest_cvm import ingest_cvm_dfp, ingest_cvm_itr
from public_finance_data_hub.pipelines.ingest_fred import ingest_fred_series
from public_finance_data_hub.pipelines.ingest_world_bank import ingest_world_bank_indicators

app = typer.Typer(
    name="pfdh",
    help="Public Finance Data Hub - Catalog & sync financial data from multiple sources",
    no_args_is_help=True,
)
console = Console()
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_DATA_DIR = Path("./data")
DEFAULT_LOG_DIR = Path("./logs")
DEFAULT_CACHE_DIR = Path("./.cache")


def get_config_path() -> Path:
    """Get path to sources.yml config."""
    return Path(__file__).parent / "config" / "sources.yml"


def load_sources_config() -> dict:
    """Load sources configuration."""
    config_path = get_config_path()
    if not config_path.exists():
        console.print(f"[red]Error:[/red] Config not found at {config_path}")
        raise typer.Exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


@app.command()
def list_sources() -> None:
    """List all available data sources."""
    config = load_sources_config()
    console.print("\n[bold cyan]Available Data Sources:[/bold cyan]\n")

    # Create table
    table = Table(
        title="Data Sources",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Source", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Country", style="yellow")
    table.add_column("Description")
    table.add_column("Auth Required", style="red")

    for source_id, source_info in config["sources"].items():
        table.add_row(
            source_id,
            source_info.get("type", "unknown"),
            source_info.get("country", "N/A"),
            source_info.get("description", "")[:50],
            "Yes" if source_info.get("auth_required") else "No",
        )

    console.print(table)
    console.print()


@app.command()
def auth_google(
    credentials_path: Optional[Path] = typer.Option(
        Path("./secrets/client_secret.json"),
        "--credentials-path",
        "-c",
        help="Path to Google OAuth client_secret.json",
    ),
    token_path: Optional[Path] = typer.Option(
        Path("./token.json"),
        "--token-path",
        "-t",
        help="Path where token.json will be saved",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-authentication even if token exists",
    ),
) -> None:
    """Authenticate with Google Drive (required for sync).

    This command opens your browser to authenticate with Google.
    After authentication, a token will be saved locally for future use.
    """
    console.print("\n[bold cyan]Google Drive Authentication[/bold cyan]\n")

    if not credentials_path.exists():
        console.print(
            f"[red]Error:[/red] client_secret.json not found at {credentials_path}"
        )
        console.print(
            "\n[yellow]Steps to fix:[/yellow]"
            "\n1. Go to: https://console.cloud.google.com/"
            "\n2. Create a project"
            "\n3. Enable Google Drive API"
            "\n4. Create OAuth 2.0 Desktop credentials"
            "\n5. Download JSON and save to ./secrets/client_secret.json"
        )
        raise typer.Exit(1)

    try:
        # Create dummy folder ID just for auth test (will be set properly in sync)
        drive = GoogleDriveConnector(
            folder_id="root",
            credentials_path=str(credentials_path),
            token_path=str(token_path),
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            progress.add_task("Opening browser for authentication...", total=None)
            success = drive.authenticate(force_refresh=force)

        if success:
            console.print(
                f"[green]✓ Successfully authenticated![/green]"
                f"\nToken saved to: {token_path}"
                f"\n\nYou can now use: [bold]pfdh sync-drive[/bold]"
            )
        else:
            console.print("[red]✗ Authentication failed[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def ingest(
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Data source to ingest (e.g., bcb, b3, cvm, fred, world_bank)",
    ),
    all_sources: bool = typer.Option(
        False,
        "--all",
        help="Ingest from all available sources",
    ),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD)",
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD)",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        "--output-dir",
        "-o",
        help="Output directory for data",
    ),
    cache_dir: Path = typer.Option(
        DEFAULT_CACHE_DIR,
        "--cache-dir",
        help="Cache directory",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """Ingest data from specified sources."""
    setup_logging(log_level=log_level, output_dir=DEFAULT_LOG_DIR)

    if not source and not all_sources:
        console.print("[red]Error:[/red] Specify --source or use --all")
        raise typer.Exit(1)

    # Parse dates
    from_dt = datetime.fromisoformat(from_date) if from_date else datetime(2020, 1, 1)
    to_dt = datetime.fromisoformat(to_date) if to_date else datetime.now()

    console.print(
        f"\n[bold cyan]Data Ingestion[/bold cyan]"
        f"\nPeriod: {from_dt.date()} to {to_dt.date()}"
        f"\nOutput: {output_dir.absolute()}\n"
    )

    config = load_sources_config()
    sources_to_ingest = [
        source,
    ] if source else list(config["sources"].keys())

    success_count = 0
    error_count = 0

    for src in sources_to_ingest:
        if src not in config["sources"]:
            logger.warning(f"Unknown source: {src}")
            continue

        try:
            console.print(f"[bold]Ingesting {src}...[/bold]")

            if src == "bcb":
                ingest_bcb_series(from_dt, to_dt, output_dir, cache_dir)
            elif src == "b3":
                ingest_b3_cotahist(from_dt, to_dt, output_dir, cache_dir)
            elif src == "cvm":
                ingest_cvm_dfp(from_dt, to_dt, output_dir, cache_dir)
                ingest_cvm_itr(from_dt, to_dt, output_dir, cache_dir)
            elif src == "fred":
                ingest_fred_series(from_dt, to_dt, output_dir, cache_dir)
            elif src == "world_bank":
                ingest_world_bank_indicators(from_dt, to_dt, output_dir, cache_dir)
            else:
                logger.info(f"Pipeline for {src} not yet implemented")
                continue

            console.print(f"[green]✓ {src} ingestion complete[/green]")
            success_count += 1

        except Exception as e:
            console.print(f"[red]✗ {src} ingestion failed: {e}[/red]")
            logger.exception(f"Error ingesting {src}")
            error_count += 1

    console.print(
        f"\n[bold]Summary:[/bold]"
        f"\nSuccessful: {success_count}"
        f"\nFailed: {error_count}"
    )


@app.command()
def sync_drive(
    folder_id: str = typer.Option(
        ..., "--folder-id", "-f", help="Google Drive folder ID"
    ),
    credentials_path: Path = typer.Option(
        Path("./secrets/client_secret.json"),
        "--credentials-path",
        "-c",
        help="Path to Google OAuth client_secret.json",
    ),
    token_path: Path = typer.Option(
        Path("./token.json"),
        "--token-path",
        "-t",
        help="Path to token.json",
    ),
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        "--data-dir",
        help="Data lake directory to sync",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be synced without uploading",
    ),
) -> None:
    """Sync local data lake to Google Drive."""
    console.print(
        f"\n[bold cyan]Google Drive Sync[/bold cyan]"
        f"\nFolder ID: {folder_id}"
        f"\nData directory: {data_dir.absolute()}"
        f"\nDry-run: {dry_run}\n"
    )

    if not token_path.exists():
        console.print(
            f"[red]Error:[/red] Token not found at {token_path}"
            f"\n\nRun first: [bold]pfdh auth-google[/bold]"
        )
        raise typer.Exit(1)

    try:
        drive = GoogleDriveConnector(
            folder_id=folder_id,
            credentials_path=str(credentials_path),
            token_path=str(token_path),
        )

        if not drive.authenticate():
            console.print("[red]Authentication failed[/red]")
            raise typer.Exit(1)

        # Sync curated data
        curated_dir = data_dir / "curated"
        if curated_dir.exists():
            console.print("[bold]Syncing curated data...[/bold]")
            stats = drive.sync_directory(
                curated_dir,
                remote_prefix="data/curated",
                dry_run=dry_run,
                pattern="*.parquet",
            )

            console.print(
                f"\n[bold]Sync complete:[/bold]"
                f"\nUploaded: {stats['uploaded']}"
                f"\nSkipped: {stats['skipped']}"
                f"\nErrors: {stats['errors']}"
                f"\nTotal size: {stats['total_size'] / 1024 / 1024 / 1024:.2f} GB"
            )
        else:
            console.print(f"[yellow]No curated data found at {curated_dir}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Sync failed")
        raise typer.Exit(1)


@app.command()
def run(
    all_sources: bool = typer.Option(
        False,
        "--all",
        help="Ingest from all sources",
    ),
    sync_drive: bool = typer.Option(
        False,
        "--sync-drive",
        help="Sync to Google Drive after ingestion",
    ),
    folder_id: Optional[str] = typer.Option(
        None,
        "--folder-id",
        "-f",
        help="Google Drive folder ID (required if --sync-drive)",
    ),
    from_date: Optional[str] = typer.Option(
        None,
        "--from",
        help="Start date (YYYY-MM-DD)",
    ),
    to_date: Optional[str] = typer.Option(
        None,
        "--to",
        help="End date (YYYY-MM-DD)",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        "--output-dir",
        "-o",
        help="Output directory",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level",
    ),
) -> None:
    """Run complete pipeline: ingest all sources and optionally sync to Drive."""
    setup_logging(log_level=log_level, output_dir=DEFAULT_LOG_DIR)

    if sync_drive and not folder_id:
        console.print(
            "[red]Error:[/red] --folder-id required when using --sync-drive"
        )
        raise typer.Exit(1)

    # Step 1: Ingest
    console.print("[bold cyan]Starting Full Pipeline[/bold cyan]\n")
    console.print("[bold]Step 1: Ingestion[/bold]")

    ingest.callback(
        source=None,
        all_sources=True,
        from_date=from_date,
        to_date=to_date,
        output_dir=output_dir,
        log_level=log_level,
    )

    # Step 2: Sync to Drive (if requested)
    if sync_drive:
        console.print("\n[bold]Step 2: Google Drive Sync[/bold]")
        sync_drive.callback(
            folder_id=folder_id,
            data_dir=output_dir,
            dry_run=False,
        )

    console.print("\n[green][bold]✓ Pipeline Complete![/bold][/green]")


@app.command()
def status(
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        "--data-dir",
        help="Data lake directory",
    ),
) -> None:
    """Show data lake status and statistics."""
    console.print("\n[bold cyan]Data Lake Status[/bold cyan]\n")

    lake = DataLake(data_dir=data_dir)
    stats = lake.get_stats()

    console.print(f"Location: {data_dir.absolute()}")
    console.print(f"Total datasets: {stats.get('dataset_count', 0)}")
    console.print(f"Total files: {stats.get('file_count', 0)}")
    console.print(f"Total size: {stats.get('total_size_gb', 0):.2f} GB")


if __name__ == "__main__":
    app()

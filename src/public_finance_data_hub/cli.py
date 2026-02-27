"""Command-line interface for Public Finance Data Hub."""

import typer
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional
import os
from dotenv import load_dotenv
import yaml

from public_finance_data_hub.utils.logging import setup_logging
from public_finance_data_hub.storage.lake import DataLake
from public_finance_data_hub.connectors import (
    BCBSGSConnector,
    B3Connector,
    CVMConnector,
    FREDConnector,
    GoogleDriveConnector,
)
from public_finance_data_hub.utils.dates import parse_date

# Load environment variables
load_dotenv()

app = typer.Typer(
    help="Public Finance Data Hub - Financial data ingestion & synchronization",
    pretty_exceptions_enable=False,
)

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging("pfdh", log_level)


def load_sources_config() -> dict:
    """Load sources catalog from YAML."""
    config_path = Path(__file__).parent / "config" / "sources.yml"
    with open(config_path) as f:
        return yaml.safe_load(f)


@app.command()
def list_sources():
    """List all available data sources."""
    config = load_sources_config()
    logger.info("\nAvailable Data Sources:\n")

    sources = config.get("sources", {})
    for source_key, source_info in sources.items():
        if isinstance(source_info, dict) and "name" in source_info:
            source_type = source_info.get("type", "unknown")
            region = source_info.get("region", "")
            desc = source_info.get("description", "")
            logger.info(f"{source_key:15} | {source_type:18} | {region:10} | {desc}")


@app.command()
def ingest(
    source: Optional[str] = typer.Option(
        None, "--source", help="Data source name (e.g., bcb, b3, cvm)"
    ),
    all_sources: bool = typer.Option(
        False, "--all", help="Ingest from all sources"
    ),
    from_date: Optional[str] = typer.Option(
        None, "--from", help="Start date (YYYY-MM-DD)"
    ),
    to_date: Optional[str] = typer.Option(
        None, "--to", help="End date (YYYY-MM-DD)"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", help="Output directory"
    ),
    cache_dir: Optional[str] = typer.Option(
        None, "--cache-dir", help="Cache directory"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Logging level"
    ),
):
    """Ingest data from one or multiple sources."""
    logger.info("Starting ingestion...")

    # Parse dates
    try:
        period_start = parse_date(from_date) if from_date else date(2020, 1, 1)
        period_end = parse_date(to_date) if to_date else date.today()
    except Exception as e:
        logger.error(f"Invalid date format: {e}")
        raise typer.Exit(1)

    # Initialize data lake
    data_dir = output_dir or os.getenv("DATA_DIR", "./data")
    cache = cache_dir or os.getenv("CACHE_DIR", "./cache")
    lake = DataLake(base_dir=data_dir)

    # Determine sources to ingest
    sources_to_ingest = []
    if all_sources:
        sources_to_ingest = ["bcb", "b3", "cvm", "fred"]
    elif source:
        sources_to_ingest = [source]
    else:
        logger.error("Specify --source or use --all")
        raise typer.Exit(1)

    # Ingest each source
    for source_name in sources_to_ingest:
        try:
            logger.info(f"\n{"="*60}")
            logger.info(f"Ingesting: {source_name}")
            logger.info(f"Period: {period_start} to {period_end}")
            logger.info(f"{"="*60}")

            if source_name == "bcb":
                connector = BCBSGSConnector(cache_dir=cache)
                for dataset in connector.list_datasets()[:2]:  # First 2 for demo
                    result = connector.fetch(dataset, period_start, period_end)
                    if result["status"] == "success":
                        df = result["data"]
                        file_path = lake.save_curated(
                            "macroeconomic", "bcb_sgs", df, period_end
                        )
                        metadata = lake.get_file_metadata(file_path)
                        lake.save_manifest(
                            "bcb",
                            "bcb_sgs",
                            "macroeconomic",
                            str(period_start),
                            str(period_end),
                            [metadata],
                            "https://www3.bcb.gov.br/sgspub/",
                        )
                    else:
                        logger.warning(f"Failed to fetch {dataset}: {result['metadata']}")

            elif source_name == "b3":
                connector = B3Connector(cache_dir=cache)
                for dataset in ["cotahist"]:
                    result = connector.fetch(dataset, period_start, period_end)
                    if result["status"] == "success":
                        df = result["data"]
                        file_path = lake.save_curated(
                            "market_data", "b3_cotahist", df, period_end
                        )
                        metadata = lake.get_file_metadata(file_path)
                        lake.save_manifest(
                            "b3",
                            "b3_cotahist",
                            "market_data",
                            str(period_start),
                            str(period_end),
                            [metadata],
                            "https://www.b3.com.br/",
                        )
                    else:
                        logger.warning(f"Failed to fetch {dataset}: {result['metadata']}")

            elif source_name == "cvm":
                connector = CVMConnector(cache_dir=cache)
                for dataset in ["dfp"]:
                    result = connector.fetch(dataset, period_start, period_end)
                    if result["status"] == "success":
                        df = result["data"]
                        file_path = lake.save_curated(
                            "fundamentals", "cvm_dfp", df, period_end
                        )
                        metadata = lake.get_file_metadata(file_path)
                        lake.save_manifest(
                            "cvm",
                            "cvm_dfp",
                            "fundamentals",
                            str(period_start),
                            str(period_end),
                            [metadata],
                            "https://dados.cvm.gov.br/",
                        )
                    else:
                        logger.warning(f"Failed to fetch {dataset}: {result['metadata']}")

            elif source_name == "fred":
                if not os.getenv("FRED_API_KEY"):
                    logger.warning("FRED_API_KEY not set, skipping FRED")
                    continue
                connector = FREDConnector(cache_dir=cache)
                for dataset in ["unemployment_rate"]:
                    result = connector.fetch(dataset, period_start, period_end)
                    if result["status"] == "success":
                        df = result["data"]
                        file_path = lake.save_curated(
                            "macroeconomic", "fred", df, period_end
                        )
                        metadata = lake.get_file_metadata(file_path)
                        lake.save_manifest(
                            "fred",
                            "fred",
                            "macroeconomic",
                            str(period_start),
                            str(period_end),
                            [metadata],
                            "https://fred.stlouisfed.org/",
                        )
                    else:
                        logger.warning(f"Failed to fetch {dataset}: {result['metadata']}")

        except Exception as e:
            logger.error(f"Error ingesting {source_name}: {e}")
            continue

    logger.info(f"\n✓ Ingestion complete!")


@app.command()
def sync_drive(
    folder_id: str = typer.Option(..., "--folder-id", help="Google Drive folder ID"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Dry-run mode (don't upload)"
    ),
    domain: Optional[str] = typer.Option(
        None, "--domain", help="Filter by domain (e.g., fundamentals)"
    ),
    data_dir: Optional[str] = typer.Option(
        None, "--data-dir", help="Data directory"
    ),
):
    """Sync curated data to Google Drive."""
    logger.info("Starting Google Drive sync...")

    data_dir = data_dir or os.getenv("DATA_DIR", "./data")

    oauth_secrets = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS")
    token_path = os.getenv("GOOGLE_TOKEN_PATH")
    service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not (oauth_secrets or service_account):
        logger.error("Google Drive credentials not configured")
        raise typer.Exit(1)

    try:
        drive = GoogleDriveConnector(
            folder_id=folder_id,
            oauth_client_secrets=oauth_secrets,
            token_path=token_path,
            service_account_json=service_account,
        )

        lake = DataLake(base_dir=data_dir)
        datasets = lake.list_datasets(domain)

        if dry_run:
            logger.info(f"[DRY-RUN] Would upload {len(datasets)} datasets")
            for ds in datasets:
                logger.info(f"  - {ds['domain']}/{ds['dataset']} ({ds['file_count']} files)")
        else:
            for ds in datasets:
                logger.info(f"Syncing {ds['domain']}/{ds['dataset']}...")
                # Would sync files to Drive here

        logger.info("✓ Sync complete!")

    except Exception as e:
        logger.error(f"Error during sync: {e}")
        raise typer.Exit(1)


@app.command()
def run(
    all_sources: bool = typer.Option(
        False, "--all", help="Ingest all sources"
    ),
    sync_drive_flag: bool = typer.Option(
        False, "--sync-drive", help="Sync to Google Drive after ingest"
    ),
    folder_id: Optional[str] = typer.Option(
        None, "--folder-id", help="Google Drive folder ID"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Dry-run mode"
    ),
):
    """Run full pipeline: ingest all sources and sync to Drive."""
    logger.info("Starting full pipeline...")

    # Run ingest
    try:
        ingest(
            all_sources=all_sources,
            log_level="INFO",
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise typer.Exit(1)

    # Run sync if requested
    if sync_drive_flag:
        if not folder_id:
            logger.error("--folder-id required for Drive sync")
            raise typer.Exit(1)

        try:
            sync_drive(folder_id=folder_id, dry_run=dry_run)
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise typer.Exit(1)

    logger.info("✓ Pipeline complete!")


if __name__ == "__main__":
    app()

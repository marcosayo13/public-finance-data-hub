"""Data lake manager for partitioned Parquet storage with versioning."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import logging
from dataclasses import dataclass, asdict
from public_finance_data_hub.utils.hashing import calculate_file_sha256
from public_finance_data_hub.utils.dates import format_date
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    """File metadata for manifest."""

    name: str
    sha256: str
    rows: int
    columns: int
    size_bytes: int
    created_at: str


@dataclass
class DatasetManifest:
    """Dataset manifest structure."""

    source: str
    dataset: str
    period_start: str
    period_end: str
    file_count: int
    files: List[Dict[str, Any]]
    source_url: str
    schema_version: str
    ingestion_timestamp: str
    ingestion_status: str


class DataLake:
    """Partitioned data lake manager."""

    def __init__(
        self,
        base_dir: str = "./data",
        raw_dir: str = "raw",
        curated_dir: str = "curated",
        manifest_dir: str = "manifests",
        compression: str = "snappy",
    ):
        """Initialize data lake.

        Args:
            base_dir: Base data directory
            raw_dir: Raw data subdirectory
            curated_dir: Curated data subdirectory
            manifest_dir: Manifest subdirectory
            compression: Parquet compression (snappy, gzip, brotli)
        """
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / raw_dir
        self.curated_dir = self.base_dir / curated_dir
        self.manifest_dir = self.base_dir / manifest_dir
        self.compression = compression

        # Create directories
        for d in [self.raw_dir, self.curated_dir, self.manifest_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_raw(
        self, source: str, filename: str, content: bytes, period_date: Optional[date] = None
    ) -> Path:
        """Save raw file with date partitioning.

        Args:
            source: Data source name
            filename: File name
            content: File content
            period_date: Date for partitioning (default: today)

        Returns:
            Path to saved file
        """
        if period_date is None:
            period_date = date.today()

        # Partition: raw/<source>/<year>/<month>/<filename>
        save_dir = self.raw_dir / source / str(period_date.year) / str(period_date.month)
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / filename

        save_path.write_bytes(content)
        logger.info(f"Saved raw: {save_path} ({len(content)} bytes)")
        return save_path

    def save_curated(
        self,
        domain: str,
        dataset: str,
        df: pd.DataFrame,
        period_date: Optional[date] = None,
        filename: str = "data",
    ) -> Path:
        """Save curated Parquet with date partitioning.

        Args:
            domain: Data domain (e.g., fundamentals, market_data)
            dataset: Dataset name (e.g., b3_cotahist)
            df: DataFrame to save
            period_date: Date for partitioning
            filename: Base filename

        Returns:
            Path to saved file
        """
        if period_date is None:
            period_date = date.today()

        # Partition: curated/<domain>/<dataset>/year=<year>/month=<month>/
        save_dir = (
            self.curated_dir
            / domain
            / dataset
            / f"year={period_date.year}"
            / f"month={period_date.month}"
        )
        save_dir.mkdir(parents=True, exist_ok=True)

        # Add timestamp to filename
        timestamp = period_date.strftime("%Y%m%d")
        save_path = save_dir / f"{filename}_{timestamp}.parquet"

        # Save Parquet
        df.to_parquet(
            save_path, engine="pyarrow", compression=self.compression, index=False
        )
        logger.info(f"Saved curated: {save_path} ({len(df)} rows)")
        return save_path

    def save_manifest(
        self,
        source: str,
        dataset: str,
        domain: str,
        period_start: str,
        period_end: str,
        files: List[Dict[str, Any]],
        source_url: str,
        ingestion_status: str = "success",
    ) -> Path:
        """Save dataset manifest.

        Args:
            source: Data source
            dataset: Dataset name
            domain: Data domain
            period_start: Period start date (YYYY-MM-DD)
            period_end: Period end date (YYYY-MM-DD)
            files: List of file metadata dicts
            source_url: Source URL
            ingestion_status: Ingestion status

        Returns:
            Path to manifest file
        """
        manifest_data = {
            "source": source,
            "dataset": dataset,
            "domain": domain,
            "period_start": period_start,
            "period_end": period_end,
            "file_count": len(files),
            "files": files,
            "source_url": source_url,
            "schema_version": "1.0",
            "ingestion_timestamp": datetime.now().isoformat(),
            "ingestion_status": ingestion_status,
        }

        # Save to manifest dir
        manifest_dir = self.manifest_dir / domain / dataset
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest_file = manifest_dir / f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        manifest_file.write_text(json.dumps(manifest_data, indent=2))
        logger.info(f"Saved manifest: {manifest_file}")
        return manifest_file

    def load_curated(
        self, domain: str, dataset: str, filters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Load curated Parquet dataset.

        Args:
            domain: Data domain
            dataset: Dataset name
            filters: Pyarrow filters for partitions

        Returns:
            Combined DataFrame from all partitions
        """
        dataset_dir = self.curated_dir / domain / dataset

        if not dataset_dir.exists():
            logger.warning(f"Dataset not found: {dataset_dir}")
            return pd.DataFrame()

        # Load all parquet files from partitions
        parquet_files = list(dataset_dir.rglob("*.parquet"))
        if not parquet_files:
            logger.warning(f"No parquet files found in {dataset_dir}")
            return pd.DataFrame()

        logger.info(f"Loading {len(parquet_files)} files from {dataset}")
        dfs = [pd.read_parquet(f) for f in parquet_files]
        return pd.concat(dfs, ignore_index=True)

    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get metadata for a saved file.

        Args:
            file_path: Path to file

        Returns:
            Metadata dict
        """
        if file_path.suffix == ".parquet":
            df = pd.read_parquet(file_path)
            return {
                "name": file_path.name,
                "sha256": calculate_file_sha256(file_path),
                "rows": len(df),
                "columns": len(df.columns),
                "size_bytes": file_path.stat().st_size,
                "created_at": datetime.now().isoformat(),
            }
        else:
            return {
                "name": file_path.name,
                "sha256": calculate_file_sha256(file_path),
                "rows": 0,
                "columns": 0,
                "size_bytes": file_path.stat().st_size,
                "created_at": datetime.now().isoformat(),
            }

    def list_datasets(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all datasets in lake.

        Args:
            domain: Filter by domain (optional)

        Returns:
            List of dataset info dicts
        """
        datasets = []
        search_dir = self.curated_dir / domain if domain else self.curated_dir

        for dataset_dir in search_dir.glob("*/*" if domain else "*/*"):
            if dataset_dir.is_dir():
                parquet_files = list(dataset_dir.rglob("*.parquet"))
                if parquet_files:
                    datasets.append(
                        {
                            "domain": dataset_dir.parent.name,
                            "dataset": dataset_dir.name,
                            "file_count": len(parquet_files),
                            "path": str(dataset_dir),
                        }
                    )

        return datasets

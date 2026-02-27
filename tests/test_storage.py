"""Tests for data lake storage."""

import pytest
from datetime import date
import pandas as pd
from public_finance_data_hub.storage.lake import DataLake


class TestDataLake:
    """Test DataLake functionality."""

    def test_init(self, temp_data_dir):
        """Test DataLake initialization."""
        lake = DataLake(base_dir=str(temp_data_dir))
        assert lake.base_dir.exists()
        assert lake.raw_dir.exists()
        assert lake.curated_dir.exists()
        assert lake.manifest_dir.exists()

    def test_save_raw(self, temp_data_dir):
        """Test saving raw file."""
        lake = DataLake(base_dir=str(temp_data_dir))
        content = b"test content"
        file_path = lake.save_raw(
            "test_source",
            "test_file.txt",
            content,
            period_date=date(2024, 1, 15),
        )

        assert file_path.exists()
        assert file_path.read_bytes() == content
        assert "2024" in str(file_path)
        assert "1" in str(file_path)

    def test_save_curated(self, temp_data_dir, sample_dataframe):
        """Test saving curated Parquet file."""
        lake = DataLake(base_dir=str(temp_data_dir))
        file_path = lake.save_curated(
            "market_data",
            "test_dataset",
            sample_dataframe,
            period_date=date(2024, 1, 15),
        )

        assert file_path.exists()
        assert file_path.suffix == ".parquet"

        # Verify parquet can be read
        df_loaded = pd.read_parquet(file_path)
        assert len(df_loaded) == len(sample_dataframe)

    def test_save_manifest(self, temp_data_dir):
        """Test saving manifest JSON."""
        lake = DataLake(base_dir=str(temp_data_dir))
        files_metadata = [
            {
                "name": "data_20240115.parquet",
                "sha256": "abc123",
                "rows": 100,
                "columns": 5,
                "size_bytes": 50000,
                "created_at": "2024-01-15T10:00:00",
            }
        ]

        manifest_file = lake.save_manifest(
            source="test_source",
            dataset="test_dataset",
            domain="test_domain",
            period_start="2024-01-01",
            period_end="2024-01-31",
            files=files_metadata,
            source_url="https://example.com",
        )

        assert manifest_file.exists()
        assert manifest_file.suffix == ".json"

    def test_load_curated(self, temp_data_dir, sample_dataframe):
        """Test loading curated dataset."""
        lake = DataLake(base_dir=str(temp_data_dir))

        # Save data
        lake.save_curated(
            "market_data",
            "test_dataset",
            sample_dataframe,
            period_date=date(2024, 1, 15),
        )

        # Load data
        df_loaded = lake.load_curated("market_data", "test_dataset")
        assert len(df_loaded) > 0
        assert "date" in df_loaded.columns

    def test_list_datasets(self, temp_data_dir, sample_dataframe):
        """Test listing datasets in lake."""
        lake = DataLake(base_dir=str(temp_data_dir))

        # Save some data
        lake.save_curated(
            "market_data", "dataset1", sample_dataframe, period_date=date(2024, 1, 1)
        )
        lake.save_curated(
            "fundamentals", "dataset2", sample_dataframe, period_date=date(2024, 1, 1)
        )

        # List all datasets
        datasets = lake.list_datasets()
        assert len(datasets) >= 2

        # List by domain
        market_datasets = lake.list_datasets(domain="market_data")
        assert any(ds["dataset"] == "dataset1" for ds in market_datasets)

    def test_get_file_metadata(self, temp_data_dir, sample_dataframe):
        """Test getting file metadata."""
        lake = DataLake(base_dir=str(temp_data_dir))

        file_path = lake.save_curated(
            "market_data", "test_dataset", sample_dataframe
        )

        metadata = lake.get_file_metadata(file_path)
        assert metadata["name"] == file_path.name
        assert metadata["rows"] == len(sample_dataframe)
        assert metadata["columns"] == len(sample_dataframe.columns)
        assert metadata["size_bytes"] > 0
        assert "sha256" in metadata
        assert "created_at" in metadata

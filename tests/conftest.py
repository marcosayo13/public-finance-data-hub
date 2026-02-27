"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile
import pandas as pd
from datetime import date


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
            "ticker": ["A", "B", "C", "A", "B"],
        }
    )


@pytest.fixture
def sample_csv_content():
    """Create sample CSV content as bytes."""
    content = (
        "date,ticker,price,volume\n"
        "2024-01-01,PETR4,25.50,1000000\n"
        "2024-01-02,BBAS3,35.20,1500000\n"
        "2024-01-03,VALE3,30.80,800000\n"
    )
    return content.encode()


@pytest.fixture
def mock_http_client(mocker):
    """Create mock HTTP client."""
    from public_finance_data_hub.utils.http import CachedHTTPClient

    client = CachedHTTPClient()
    mocker.patch.object(client, "get")
    return client

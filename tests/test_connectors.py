"""Tests for data source connectors."""

import pytest
from datetime import date
from public_finance_data_hub.connectors import (
    BCBSGSConnector,
    B3Connector,
    CVMConnector,
    FREDConnector,
)


class TestBCBSGSConnector:
    """Test BCB SGS connector."""

    def test_init(self):
        """Test connector initialization."""
        connector = BCBSGSConnector()
        assert connector.name == "BCB_SGS"
        assert connector.base_url == "https://www3.bcb.gov.br/sgspub/consultarvalores"

    def test_list_datasets(self):
        """Test listing available datasets."""
        connector = BCBSGSConnector()
        datasets = connector.list_datasets()
        assert len(datasets) > 0
        assert "selic_meta" in datasets
        assert "ipca" in datasets

    def test_fetch_returns_dict_with_status(self):
        """Test that fetch returns required dict structure."""
        connector = BCBSGSConnector()
        result = connector.fetch("selic_meta", date(2024, 1, 1), date(2024, 1, 31))

        assert isinstance(result, dict)
        assert "status" in result
        assert "data" in result
        assert "metadata" in result
        assert result["status"] in ["success", "error", "no_data"]


class TestB3Connector:
    """Test B3 connector."""

    def test_init(self):
        """Test connector initialization."""
        connector = B3Connector()
        assert connector.name == "B3"
        assert "cotahist" in connector.datasets
        assert "etf_list" in connector.datasets

    def test_list_datasets(self):
        """Test listing datasets."""
        connector = B3Connector()
        datasets = connector.list_datasets()
        assert len(datasets) >= 3

    def test_fetch_cotahist(self):
        """Test fetching COTAHIST data."""
        connector = B3Connector()
        result = connector.fetch("cotahist", date(2024, 1, 1), date(2024, 1, 31))

        assert result["status"] in ["success", "error", "no_data"]
        if result["status"] == "success":
            df = result["data"]
            assert len(df) > 0
            assert "ticker" in df.columns

    def test_fetch_etf_list(self):
        """Test fetching ETF list."""
        connector = B3Connector()
        result = connector.fetch("etf_list", date(2024, 1, 1), date(2024, 1, 31))

        assert result["status"] == "success"
        df = result["data"]
        assert len(df) > 0
        assert "ticker" in df.columns

    def test_fetch_fii_list(self):
        """Test fetching FII list."""
        connector = B3Connector()
        result = connector.fetch("fii_list", date(2024, 1, 1), date(2024, 1, 31))

        assert result["status"] == "success"
        df = result["data"]
        assert len(df) > 0


class TestCVMConnector:
    """Test CVM connector."""

    def test_init(self):
        """Test connector initialization."""
        connector = CVMConnector()
        assert connector.name == "CVM"
        assert "dfp" in connector.datasets
        assert "itr" in connector.datasets

    def test_list_datasets(self):
        """Test listing datasets."""
        connector = CVMConnector()
        datasets = connector.list_datasets()
        assert len(datasets) >= 4


class TestFREDConnector:
    """Test FRED connector."""

    def test_init(self):
        """Test connector initialization."""
        connector = FREDConnector()
        assert connector.name == "FRED"
        assert connector.base_url == "https://api.stlouisfed.org/fred"

    def test_list_datasets(self):
        """Test listing datasets."""
        connector = FREDConnector()
        datasets = connector.list_datasets()
        assert len(datasets) > 0
        assert "unemployment_rate" in datasets

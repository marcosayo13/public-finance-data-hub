"""Base connector class for data sources."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List, Dict, Any
import logging
from public_finance_data_hub.utils.http import CachedHTTPClient

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base class for all data source connectors."""

    def __init__(
        self,
        name: str,
        cache_dir: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize connector.

        Args:
            name: Connector name
            cache_dir: Cache directory
            timeout: Request timeout
            max_retries: Max retries for HTTP requests
        """
        self.name = name
        self.http_client = CachedHTTPClient(
            cache_dir=cache_dir,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized {name} connector")

    @abstractmethod
    def list_datasets(self) -> List[str]:
        """List available datasets from this source.

        Returns:
            List of dataset identifiers
        """
        pass

    @abstractmethod
    def fetch(
        self,
        dataset: str,
        period_start: date,
        period_end: date,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch data from source.

        Args:
            dataset: Dataset identifier
            period_start: Start date
            period_end: End date
            **kwargs: Additional source-specific parameters

        Returns:
            Dict with keys: 'data', 'metadata', 'status'
        """
        pass

    def close(self) -> None:
        """Close connector resources."""
        self.http_client.close()
        logger.info(f"Closed {self.name} connector")

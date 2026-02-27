"""ANBIMA (Associação Brasileira das Entidades dos Mercados Financeiro e de Capitais) connector.

Provides access to Brazilian financial market data including mutual funds,
fixed income indicators, and market statistics.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import base64

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ANBIMAConnector:
    """Connector for ANBIMA Data API."""

    BASE_URL = "https://data.anbima.com.br/api"
    TOKEN_URL = "https://auth.anbima.com.br/oauth/token"
    ENDPOINTS = {
        "mutual_funds": "/v1/fundos",
        "fiis": "/v1/fiis",
        "fixed_income": "/v1/renda-fixa",
        "market_indices": "/v1/indices",
    }

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        cache_dir: Path = Path(".cache"),
        timeout: int = 30,
    ):
        """Initialize ANBIMA connector.

        Args:
            client_id: ANBIMA OAuth Client ID (defaults to env var)
            client_secret: ANBIMA OAuth Client Secret (defaults to env var)
            cache_dir: Directory for caching responses
            timeout: HTTP request timeout in seconds
        """
        self.client_id = client_id or os.getenv("ANBIMA_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ANBIMA_CLIENT_SECRET")
        self.api_key = os.getenv("ANBIMA_API_KEY")
        self.cache_dir = Path(cache_dir) / "anbima"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.token = None
        self.token_expires_at = None
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": "PFDH/1.0 (public-finance-data-hub)",
            },
        )

    def authenticate(self) -> bool:
        """Authenticate with ANBIMA OAuth 2.0.

        Returns:
            True if authentication successful
        """
        if not self.client_id or not self.client_secret:
            logger.warning(
                "ANBIMA credentials not provided. Set ANBIMA_CLIENT_ID and ANBIMA_CLIENT_SECRET."
            )
            return False

        if self.token and self.token_expires_at > datetime.now():
            logger.debug("Using cached ANBIMA token")
            return True

        try:
            logger.info("Authenticating with ANBIMA OAuth...")

            # Base64 encode credentials
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()

            response = self.client.post(
                self.TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()

            data = response.json()
            self.token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

            logger.info("✓ Successfully authenticated with ANBIMA")
            return True

        except Exception as e:
            logger.error(f"ANBIMA authentication failed: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"User-Agent": "PFDH/1.0 (public-finance-data-hub)"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            Response JSON
        """
        url = f"{self.BASE_URL}{endpoint}"
        kwargs["headers"] = self._get_headers()

        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.info("Token expired, re-authenticating...")
                self.authenticate()
                raise  # Retry
            raise

    def fetch_mutual_funds(
        self,
        date: Optional[datetime] = None,
        limit: int = 1000,
        cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch mutual fund data.

        Args:
            date: Date to fetch data for (defaults to today)
            limit: Maximum number of records
            cache: Use cached data if available

        Returns:
            List of fund records
        """
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        cache_key = f"mutual_funds_{date_str}.json"
        cache_path = self.cache_dir / cache_key

        # Check cache
        if cache and cache_path.exists():
            logger.debug(f"Loading mutual funds from cache: {cache_key}")
            return json.loads(cache_path.read_text())

        if not self.authenticate():
            logger.warning("ANBIMA authentication failed, skipping mutual funds")
            return []

        try:
            logger.info(f"Fetching mutual funds for {date_str}...")
            data = self._request(
                "GET",
                self.ENDPOINTS["mutual_funds"],
                params={"data": date_str, "limite": limit},
            )

            # Cache result
            cache_path.write_text(json.dumps(data))
            logger.info(f"✓ Fetched {len(data)} mutual funds")
            return data

        except Exception as e:
            logger.error(f"Error fetching mutual funds: {e}")
            return []

    def fetch_fiis(
        self,
        date: Optional[datetime] = None,
        limit: int = 1000,
        cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch FII (Real Estate Investment Fund) data.

        Args:
            date: Date to fetch data for (defaults to today)
            limit: Maximum number of records
            cache: Use cached data if available

        Returns:
            List of FII records
        """
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        cache_key = f"fiis_{date_str}.json"
        cache_path = self.cache_dir / cache_key

        # Check cache
        if cache and cache_path.exists():
            logger.debug(f"Loading FIIs from cache: {cache_key}")
            return json.loads(cache_path.read_text())

        if not self.authenticate():
            logger.warning("ANBIMA authentication failed, skipping FIIs")
            return []

        try:
            logger.info(f"Fetching FIIs for {date_str}...")
            data = self._request(
                "GET",
                self.ENDPOINTS["fiis"],
                params={"data": date_str, "limite": limit},
            )

            # Cache result
            cache_path.write_text(json.dumps(data))
            logger.info(f"✓ Fetched {len(data)} FIIs")
            return data

        except Exception as e:
            logger.error(f"Error fetching FIIs: {e}")
            return []

    def fetch_fixed_income(
        self,
        date: Optional[datetime] = None,
        asset_type: Optional[str] = None,
        cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch fixed income market data.

        Args:
            date: Date to fetch data for (defaults to today)
            asset_type: Asset type filter (e.g., 'LTN', 'NTN-B')
            cache: Use cached data if available

        Returns:
            List of fixed income records
        """
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        cache_key = f"fixed_income_{date_str}_{asset_type or 'all'}.json"
        cache_path = self.cache_dir / cache_key

        # Check cache
        if cache and cache_path.exists():
            logger.debug(f"Loading fixed income from cache: {cache_key}")
            return json.loads(cache_path.read_text())

        if not self.authenticate():
            logger.warning("ANBIMA authentication failed, skipping fixed income")
            return []

        try:
            logger.info(f"Fetching fixed income for {date_str}...")
            params = {"data": date_str}
            if asset_type:
                params["tipo_ativo"] = asset_type

            data = self._request(
                "GET",
                self.ENDPOINTS["fixed_income"],
                params=params,
            )

            # Cache result
            cache_path.write_text(json.dumps(data))
            logger.info(f"✓ Fetched {len(data)} fixed income records")
            return data

        except Exception as e:
            logger.error(f"Error fetching fixed income: {e}")
            return []

    def fetch_market_indices(
        self,
        cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch market indices.

        Args:
            cache: Use cached data if available

        Returns:
            List of market indices
        """
        cache_key = "market_indices.json"
        cache_path = self.cache_dir / cache_key

        # Check cache (1 hour)
        if cache and cache_path.exists():
            if (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).seconds < 3600:
                logger.debug("Loading market indices from cache")
                return json.loads(cache_path.read_text())

        if not self.authenticate():
            logger.warning("ANBIMA authentication failed, skipping market indices")
            return []

        try:
            logger.info("Fetching market indices...")
            data = self._request("GET", self.ENDPOINTS["market_indices"])

            # Cache result
            cache_path.write_text(json.dumps(data))
            logger.info(f"✓ Fetched {len(data)} market indices")
            return data

        except Exception as e:
            logger.error(f"Error fetching market indices: {e}")
            return []

    def close(self):
        """Close HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

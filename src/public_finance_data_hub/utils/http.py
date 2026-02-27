"""HTTP client with automatic retry, backoff, and caching."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
import hashlib
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CachedHTTPClient:
    """HTTP client with automatic retry, backoff, and local caching."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_ttl_hours: int = 24,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        timeout: int = 30,
        user_agent: Optional[str] = None,
    ):
        """Initialize HTTP client.

        Args:
            cache_dir: Directory for caching responses
            cache_ttl_hours: Cache time-to-live in hours
            max_retries: Maximum retry attempts
            backoff_factor: Backoff factor for retries
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.timeout = timeout
        self.user_agent = user_agent or "PublicFinanceDataHub/1.0 (+https://github.com/marcosayo13/public-finance-data-hub)"

        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from URL and parameters."""
        cache_str = f"{url}_{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[str]:
        """Load response from cache if valid."""
        if not self.cache_dir:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        cache_data = json.loads(cache_file.read_text())
        cache_time = datetime.fromisoformat(cache_data["timestamp"])

        if datetime.now() - cache_time > self.cache_ttl:
            cache_file.unlink()
            return None

        return cache_data["content"]

    def _save_to_cache(self, cache_key: str, content: str) -> None:
        """Save response to cache."""
        if not self.cache_dir:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"
        cache_data = {"timestamp": datetime.now().isoformat(), "content": content}
        cache_file.write_text(json.dumps(cache_data))

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> requests.Response:
        """Perform GET request with retry and caching.

        Args:
            url: Request URL
            params: Query parameters
            headers: Custom headers
            use_cache: Use local cache

        Returns:
            Response object
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(url, params)
            cached_content = self._load_from_cache(cache_key)
            if cached_content:
                logger.debug(f"Cache hit for {url}")
                response = requests.Response()
                response._content = cached_content.encode()
                response.status_code = 200
                return response

        # Make request
        headers = headers or {}
        headers["User-Agent"] = self.user_agent

        logger.debug(f"GET {url}")
        response = self.session.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()

        # Cache response
        if use_cache and response.status_code == 200:
            cache_key = self._get_cache_key(url, params)
            self._save_to_cache(cache_key, response.text)

        return response

    def download(
        self,
        url: str,
        save_path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        chunk_size: int = 8192,
    ) -> Path:
        """Download file from URL.

        Args:
            url: File URL
            save_path: Local save path
            params: Query parameters
            headers: Custom headers
            chunk_size: Download chunk size in bytes

        Returns:
            Path to downloaded file
        """
        save_file = Path(save_path)
        save_file.parent.mkdir(parents=True, exist_ok=True)

        headers = headers or {}
        headers["User-Agent"] = self.user_agent

        logger.info(f"Downloading {url} -> {save_path}")

        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=self.timeout,
            stream=True,
        )
        response.raise_for_status()

        with open(save_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        logger.info(f"Downloaded: {save_file.stat().st_size} bytes")
        return save_file

    def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """Perform POST request.

        Args:
            url: Request URL
            data: Form data
            json_data: JSON payload
            headers: Custom headers

        Returns:
            Response object
        """
        headers = headers or {}
        headers["User-Agent"] = self.user_agent

        logger.debug(f"POST {url}")
        response = self.session.post(
            url,
            data=data,
            json=json_data,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def close(self) -> None:
        """Close session."""
        self.session.close()

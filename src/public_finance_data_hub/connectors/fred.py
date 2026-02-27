"""FRED (Federal Reserve Economic Data) connector."""

import logging
import os
from datetime import date
from typing import Dict, List, Any, Optional
import pandas as pd
from public_finance_data_hub.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

# Common FRED series
SERIES_MAP = {
    "unemployment_rate": "UNRATE",
    "cpi": "CPIAUCSL",
    "unemployment_level": "EMRSL",
    "nonfarm_payroll": "PAYEMS",
    "gdp": "A191RA1Q225SBEA",
}


class FREDConnector(BaseConnector):
    """Federal Reserve Economic Data (FRED) API connector."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize FRED connector."""
        super().__init__("FRED", cache_dir, timeout, max_retries)
        self.api_key = os.getenv("FRED_API_KEY")
        if not self.api_key:
            logger.warning("FRED_API_KEY not set. FRED connector may have limited functionality.")
        self.base_url = "https://api.stlouisfed.org/fred"

    def list_datasets(self) -> List[str]:
        """List available series."""
        return list(SERIES_MAP.keys())

    def fetch(
        self,
        dataset: str,
        period_start: date,
        period_end: date,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch series from FRED API.

        Args:
            dataset: Series name
            period_start: Start date
            period_end: End date

        Returns:
            Dict with 'data', 'metadata', 'status'
        """
        try:
            if not self.api_key:
                return {
                    "data": pd.DataFrame(),
                    "metadata": {"error": "FRED_API_KEY not configured"},
                    "status": "error",
                }

            if dataset not in SERIES_MAP:
                return {
                    "data": pd.DataFrame(),
                    "metadata": {"error": f"Unknown series: {dataset}"},
                    "status": "error",
                }

            series_id = SERIES_MAP[dataset]
            logger.info(f"Fetching FRED {dataset} ({series_id})...")

            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "observation_start": period_start.isoformat(),
                "observation_end": period_end.isoformat(),
            }

            response = self.http_client.get(
                f"{self.base_url}/series/observations",
                params=params,
                use_cache=True,
            )
            response_json = response.json()

            if "observations" not in response_json:
                logger.warning(f"No data for FRED series {series_id}")
                return {
                    "data": pd.DataFrame(),
                    "metadata": {"info": "No data in period"},
                    "status": "no_data",
                }

            # Parse observations
            observations = response_json["observations"]
            df = pd.DataFrame(observations)
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df[["date", "value"]].rename(columns={"value": dataset})
            df = df.sort_values("date").reset_index(drop=True)

            logger.info(f"✓ Fetched {len(df)} records from FRED")

            return {
                "data": df,
                "metadata": {
                    "series_id": series_id,
                    "series_name": dataset,
                    "rows": len(df),
                },
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error fetching FRED data: {e}")
            return {
                "data": pd.DataFrame(),
                "metadata": {"error": str(e)},
                "status": "error",
            }

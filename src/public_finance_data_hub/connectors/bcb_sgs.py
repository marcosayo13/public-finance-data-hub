"""BCB SGS (Central Bank Macro Series) connector."""

import logging
from datetime import date
from typing import Dict, List, Any, Optional
import pandas as pd
from public_finance_data_hub.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

# Common series IDs from BCB SGS
SERIES_MAP = {
    "selic_meta": "1",  # Selic - Meta
    "ipca": "433",  # IPCA
    "usd_brl": "1",  # USD/BRL
    "unemployment": "11255",  # Unemployment rate
    "industrial_production": "3652",  # Industrial production
}


class BCBSGSConnector(BaseConnector):
    """Central Bank of Brazil SGS connector."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize BCB connector."""
        super().__init__("BCB_SGS", cache_dir, timeout, max_retries)
        self.base_url = "https://www3.bcb.gov.br/sgspub/consultarvalores"

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
        """Fetch series from BCB SGS API.

        Args:
            dataset: Series name (e.g., 'selic_meta')
            period_start: Start date
            period_end: End date

        Returns:
            Dict with 'data' (DataFrame), 'metadata', 'status'
        """
        try:
            if dataset not in SERIES_MAP:
                return {
                    "data": pd.DataFrame(),
                    "metadata": {"error": f"Unknown series: {dataset}"},
                    "status": "error",
                }

            series_id = SERIES_MAP[dataset]

            logger.info(f"Fetching BCB series {dataset} ({series_id})...")

            # Build query parameters
            params = {
                "idSerie": series_id,
                "dataInicial": period_start.strftime("%d/%m/%Y"),
                "dataFinal": period_end.strftime("%d/%m/%Y"),
                "format": "json",
            }

            response = self.http_client.get(self.base_url, params=params, use_cache=True)
            response_json = response.json()

            # Parse response
            if "series" not in response_json:
                logger.warning(f"No data for series {series_id}")
                return {
                    "data": pd.DataFrame(),
                    "metadata": {"info": "No data in period"},
                    "status": "no_data",
                }

            # Extract series data
            series_data = response_json["series"][0]["dado"]
            df = pd.DataFrame(series_data)

            # Rename columns
            df.columns = ["date", dataset]
            df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
            df[dataset] = pd.to_numeric(df[dataset], errors="coerce")
            df = df.sort_values("date").reset_index(drop=True)

            logger.info(f"✓ Fetched {len(df)} records from BCB")

            return {
                "data": df,
                "metadata": {
                    "series_id": series_id,
                    "series_name": dataset,
                    "rows": len(df),
                    "columns": len(df.columns),
                },
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error fetching BCB data: {e}")
            return {
                "data": pd.DataFrame(),
                "metadata": {"error": str(e)},
                "status": "error",
            }

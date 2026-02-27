# Public Finance Data Hub

Production-grade repository for cataloging, downloading, standardizing, and versioning free public financial data sources from Brazil and internationally, with automated synchronization to Google Drive.

## Overview

**Public Finance Data Hub** (`pfdh`) is a data engineering framework that:

- Maintains a versioned catalog of 9+ financial data sources
- Implements reproducible ETL pipelines (download → parse → normalize → validate)
- Stores data locally in a partitioned data lake (Parquet format)
- Syncs curated datasets incrementally to Google Drive
- Provides CLI, structured logging, tests, and CI/CD

### Supported Sources

| Source | Type | Region | Coverage |
|--------|------|--------|----------|
| **CVM (Dados Abertos)** | Fundamentals | Brazil | DFP, ITR, Company Registry, Funds |
| **B3 COTAHIST** | Market Data | Brazil | Historical daily prices (stocks, options) |
| **BCB/SGS** | Macroeconomic | Brazil | Selic, Exchange, Credit via API |
| **IPEA Ipeadata** | Macroeconomic | Brazil | Economic indicators via API |
| **dados.gov.br** | Catalog | Brazil | Curated public datasets |
| **ANBIMA Data** | Fixed Income | Brazil | Public bond and fund data |
| **SEC EDGAR** | Fundamentals | USA | Company filings, XBRL |
| **FRED** | Macroeconomic | USA | Federal Reserve indicators via API |
| **World Bank** | Macroeconomic | Global | Development indicators via API |

---

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/marcosayo13/public-finance-data-hub.git
cd public-finance-data-hub

# Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
make setup
```

### 2. Configure Credentials

Copy `.env.example` to `.env` and fill in optional API keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Google Drive (required for sync)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_OAUTH_CLIENT_SECRETS=./secrets/client_secret.json
GOOGLE_TOKEN_PATH=./secrets/token.json

# External APIs (optional)
FRED_API_KEY=your_fred_key
GOOGLE_SERVICE_ACCOUNT_JSON=./secrets/service_account.json

# Paths
DATA_DIR=./data
CACHE_DIR=./cache
LOG_LEVEL=INFO
```

### 3. Google Drive Setup (First Time)

#### Option A: OAuth (Personal Use - Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Google Drive API**
4. Create **OAuth 2.0 Desktop Application** credentials
5. Download JSON → save as `secrets/client_secret.json`
6. Run: `pfdh auth-google`
7. Browser opens → authorize app
8. Token saved to `secrets/token.json`

#### Option B: Service Account (Automation - Advanced)

1. Create Service Account in Google Cloud
2. Create and download JSON key
3. Share your Google Drive folder with the service account email
4. Set `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env`

### 4. First Run

```bash
# List available sources
pfdh list-sources

# Ingest from a single source (example: BCB)
pfdh ingest --source bcb --from 2020-01-01 --to 2026-12-31

# Ingest all sources
pfdh ingest --all

# Sync to Google Drive (dry-run first)
pfdh sync-drive --folder-id <YOUR_FOLDER_ID> --dry-run

# Full pipeline: ingest + sync
pfdh run --all --sync-drive --folder-id <YOUR_FOLDER_ID>
```

---

## Project Structure

```
public-finance-data-hub/
├── README.md                      # This file
├── pyproject.toml                 # Python project config
├── .env.example                   # Environment template
├── Makefile                        # Development tasks
├── .gitignore                      # Git exclusions
│
├── src/public_finance_data_hub/
│   ├── __init__.py
│   ├── cli.py                      # Typer CLI entry point
│   │
│   ├── config/
│   │   ├── sources.yml             # Data source catalog
│   │   └── schemas/
│   │       ├── market_data.json    # COTAHIST schema
│   │       ├── fundamentals.json   # DFP/ITR schema
│   │       ├── macroeconomic.json  # Macro indicators schema
│   │       └── funds.json          # Fund data schema
│   │
│   ├── connectors/
│   │   ├── base.py                 # Base connector class
│   │   ├── cvm.py                  # CVM API connector
│   │   ├── b3.py                   # B3 COTAHIST connector
│   │   ├── bcb_sgs.py              # BCB SGS connector
│   │   ├── ipea.py                 # IPEA API connector
│   │   ├── dados_gov.py            # dados.gov.br connector
│   │   ├── anbima.py               # ANBIMA connector
│   │   ├── sec_edgar.py            # SEC EDGAR connector
│   │   ├── fred.py                 # FRED API connector
│   │   ├── world_bank.py           # World Bank connector
│   │   └── google_drive.py         # Google Drive uploader
│   │
│   ├── pipelines/
│   │   ├── base.py                 # Base pipeline class
│   │   ├── ingest_cvm.py           # CVM pipeline
│   │   ├── ingest_b3.py            # B3 pipeline
│   │   ├── ingest_bcb.py           # BCB pipeline
│   │   ├── ingest_ipea.py          # IPEA pipeline
│   │   ├── ingest_anbima.py        # ANBIMA pipeline
│   │   ├── ingest_sec.py           # SEC pipeline
│   │   ├── ingest_fred.py          # FRED pipeline
│   │   ├── ingest_world_bank.py    # World Bank pipeline
│   │   └── sync_to_drive.py        # Drive sync pipeline
│   │
│   ├── storage/
│   │   └── lake.py                 # Data lake manager (partition, hash, manifest)
│   │
│   └── utils/
│       ├── http.py                 # HTTP client with retry/backoff
│       ├── logging.py              # Structured logging
│       ├── dates.py                # Date utilities
│       ├── hashing.py              # SHA256 hashing, dedup
│       └── validations.py          # Schema validation (Pydantic)
│
├── tests/
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_connectors.py          # Connector unit tests
│   ├── test_pipelines.py           # Pipeline tests
│   ├── test_storage.py             # Data lake tests
│   └── fixtures/
│       ├── sample_cotahist.csv     # Sample B3 data
│       ├── sample_dfp.xml          # Sample CVM data
│       └── sample_series.json      # Sample macro data
│
├── .github/workflows/
│   └── ci.yml                      # GitHub Actions CI
│
├── data/
│   ├── raw/                        # Raw downloads (gitignored)
│   ├── curated/                    # Normalized Parquet outputs (gitignored)
│   └── manifests/                  # JSON manifests (gitignored)
│
├── cache/                          # HTTP cache (gitignored)
└── secrets/                        # Credentials (gitignored)
```

---

## CLI Commands

### `pfdh list-sources`

List all configured data sources with metadata.

```bash
pfdh list-sources
# Output:
# SOURCE         TYPE            REGION      ENDPOINT
# cvm            fundamentals    Brazil      https://dados.cvm.gov.br/...
# b3             market_data     Brazil      https://www.b3.com.br/...
# ...
```

### `pfdh ingest`

Download and process data from one or multiple sources.

```bash
# Ingest from specific source
pfdh ingest --source bcb --from 2020-01-01 --to 2026-12-31

# Ingest all sources
pfdh ingest --all

# Custom output directory
pfdh ingest --source cvm --output-dir /mnt/data

# Verbose logging
pfdh ingest --all --log-level DEBUG
```

### `pfdh sync-drive`

Sync curated data to Google Drive (requires OAuth setup).

```bash
# Dry-run (no actual upload)
pfdh sync-drive --folder-id <ID> --dry-run

# Actually sync
pfdh sync-drive --folder-id <ID>

# Sync only specific domain
pfdh sync-drive --folder-id <ID> --domain fundamentals
```

### `pfdh run`

Full pipeline: ingest all sources, then sync to Drive.

```bash
pfdh run --all --sync-drive --folder-id <ID>

pfdh run --all --sync-drive --folder-id <ID> --dry-run
```

### `pfdh auth-google`

Interactive Google OAuth setup (generates `token.json`).

```bash
pfdh auth-google
# Browser opens → authorize app → token saved
```

---

## Data Storage & Partitioning

### Raw Data

```
data/raw/
├── cvm/
│   ├── 2024/
│   │   ├── 01/
│   │   │   └── dfp_2024_01_31_raw.xml
│   │   └── 09/
│   │       └── itr_2024_09_30_raw.xml
│   └── 2025/...
│
├── b3/
│   ├── 2024/
│   │   └── 12/
│   │       └── cotahist_20241231.csv
│   └── 2025/...
│
└── bcb/
    ├── 2024/
    │   └── 12/
    │       └── sgs_series_1_2024_12_31.csv
    └── 2025/...
```

### Curated Data (Parquet Partitioned)

```
data/curated/
├── market_data/
│   ├── b3_cotahist/
│   │   ├── year=2024/month=01/
│   │   │   ├── data_20240131.parquet
│   │   │   └── _manifest.json
│   │   └── year=2025/month=01/...
│   │
│   └── b3_etf/
│       ├── year=2024/...
│       └── year=2025/...
│
├── fundamentals/
│   ├── cvm_dfp/
│   │   ├── year=2024/month=12/
│   │   │   ├── data_20241231.parquet
│   │   │   └── _manifest.json
│   │   └── year=2025/...
│   │
│   └── sec_edgar/
│       ├── year=2024/...
│       └── year=2025/...
│
└── macroeconomic/
    ├── bcb_sgs/
    │   ├── year=2024/month=12/
    │   │   ├── data_20241231.parquet
    │   │   └── _manifest.json
    │   └── year=2025/...
    │
    └── fred/
        ├── year=2024/...
        └── year=2025/...
```

### Manifest Structure

Each dataset includes a `_manifest.json`:

```json
{
  "source": "bcb_sgs",
  "dataset": "macro_series",
  "period_start": "2020-01-01",
  "period_end": "2026-12-31",
  "file_count": 3,
  "files": [
    {
      "name": "data_20261231.parquet",
      "sha256": "abc123...",
      "rows": 1500,
      "columns": 12,
      "size_bytes": 45678,
      "created_at": "2026-01-15T10:30:00Z"
    }
  ],
  "source_url": "https://www3.bcb.gov.br/sgspub/consultarvalores",
  "schema_version": "1.0",
  "ingestion_timestamp": "2026-01-15T10:32:15Z",
  "ingestion_status": "success"
}
```

---

## Examples

### Example 1: Download CVM DFP/ITR

```bash
pfdh ingest --source cvm --from 2022-01-01 --to 2026-12-31 --log-level INFO

# Output:
# [2026-01-15 10:30:05] INFO: Connecting to CVM Dados Abertos...
# [2026-01-15 10:30:10] INFO: Downloaded 1,245 DFP files (2022-2025)
# [2026-01-15 10:30:15] INFO: Downloaded 856 ITR files (2022-2025)
# [2026-01-15 10:31:45] INFO: Parsed 2,101 companies
# [2026-01-15 10:32:20] INFO: Normalized to Parquet: data/curated/fundamentals/cvm_dfp/...
# [2026-01-15 10:32:21] INFO: ✓ Ingestion complete. Manifest saved.
```

Files saved to:
- `data/curated/fundamentals/cvm_dfp/year=2022/month=12/data_*.parquet`
- `data/curated/fundamentals/cvm_dfp/year=2023/month=03/data_*.parquet` (ITR)
- etc.

### Example 2: Download B3 COTAHIST & Sync to Drive

```bash
# Step 1: Ingest B3 data
pfdh ingest --source b3 --from 2024-01-01 --to 2026-12-31

# Step 2: Dry-run sync
pfdh sync-drive --folder-id abc123def456 --dry-run

# Output:
# [INFO] Would create: Public Finance Hub / market_data / b3_cotahist
# [INFO] Would upload: b3_cotahist/year=2024/month=01/data_20240131.parquet (12.5 MB)
# [INFO] Would upload: b3_cotahist/year=2024/month=02/data_20240229.parquet (11.8 MB)
# ...
# [INFO] DRY-RUN: 456 files would be uploaded (2.3 GB total)

# Step 3: Actually sync
pfdh sync-drive --folder-id abc123def456

# Output:
# [INFO] Creating folder: market_data...
# [INFO] Creating folder: b3_cotahist...
# [INFO] Uploading: data_20240131.parquet... [████████░░] 12.5 MB
# [INFO] ✓ Sync complete. 456 files uploaded (2.3 GB).
```

### Example 3: Download BCB Macroeconomic Series

```bash
pfdh ingest --source bcb \
  --from 2015-01-01 \
  --to 2026-12-31 \
  --output-dir /mnt/financial_data

# Downloads all SGS series (Selic, IPCA, USD/BRL, etc.)
# Saved to: /mnt/financial_data/curated/macroeconomic/bcb_sgs/...
```

### Example 4: Full Automated Pipeline (Cron/CI)

```bash
# In GitHub Actions or cron job:
pfdh run \
  --all \
  --sync-drive \
  --folder-id $GOOGLE_DRIVE_FOLDER_ID \
  --log-level INFO

# Runs all sources in sequence, syncs to Drive, exits with status code
```

---

## Security

### Credential Management

⚠️ **CRITICAL: Never commit credentials to Git**

1. **Create `.env` from `.env.example`** (already in `.gitignore`)

2. **Store secrets in `secrets/` folder** (also in `.gitignore`):
   - `secrets/client_secret.json` (OAuth credentials)
   - `secrets/token.json` (OAuth token)
   - `secrets/service_account.json` (Service Account key)

3. **API Keys via environment variables**:
   ```bash
   export FRED_API_KEY=your_key
   export GOOGLE_DRIVE_FOLDER_ID=your_folder_id
   ```

4. **GitHub Secrets (for CI/CD)**:
   ```bash
   # Add to repo settings
   GOOGLE_DRIVE_FOLDER_ID=xxx
   FRED_API_KEY=xxx
   GOOGLE_OAUTH_CLIENT_SECRETS=<base64-encoded JSON>
   ```

### OAuth Token Refresh

Tokens are automatically refreshed when expired. The refresh token is stored in `token.json` (never commit).

### Audit

All ingestions are logged with timestamps and file hashes (SHA256). Review logs in `data/manifests/` to track data versions.

---

## Development

### Setup Development Environment

```bash
make setup       # Install deps + pre-commit hooks
make lint        # Format code (black, isort, flake8)
make test        # Run pytest suite
make run-dev     # Run CLI in dev mode
make clean       # Remove cache, builds
```

### Running Tests

```bash
pytest tests/ -v --cov=src/public_finance_data_hub

# Or specific test file
pytest tests/test_connectors.py -v -k "test_b3"
```

### Adding a New Data Source

1. Create connector in `src/public_finance_data_hub/connectors/my_source.py`
2. Create pipeline in `src/public_finance_data_hub/pipelines/ingest_my_source.py`
3. Add source to `src/public_finance_data_hub/config/sources.yml`
4. Register in CLI (`src/public_finance_data_hub/cli.py`)
5. Add tests in `tests/`
6. Update README

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'public_finance_data_hub'"

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall package
pip install -e .
```

### "Google Drive API: Permission Denied"

1. Check `GOOGLE_DRIVE_FOLDER_ID` is correct
2. Verify folder is shared with OAuth account or Service Account email
3. Check API quota in Google Cloud Console

### "Connection timeout to CVM"

The connectors have automatic retry with exponential backoff. If persistent:
- Check internet connection
- Verify CVM service is online: https://dados.cvm.gov.br/
- Increase timeout: set `HTTP_TIMEOUT=60` in `.env`

### "No such file or directory: 'data/raw/...'"

Directories are auto-created. If error persists:
- Check disk space
- Verify `DATA_DIR` path is writable
- Run: `mkdir -p data/{raw,curated} cache`

---

## CI/CD

The repository includes GitHub Actions workflow (`.github/workflows/ci.yml`) that:
- Runs on every push to `main`
- Lints code (black, flake8, isort)
- Runs test suite
- Checks code coverage

---

## Roadmap

- [ ] Support incremental ingestion (only new files since last run)
- [ ] Add data quality checks (null %, duplicates %)
- [ ] Multi-threading for parallel source ingestion
- [ ] Cloud storage backends (S3, GCS, Azure Blob)
- [ ] Web dashboard for data catalog
- [ ] Data lineage & audit trail UI
- [ ] Notifications on ingestion failures (Slack, email)

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit with clear messages
4. Open a Pull Request

---

## License

MIT License - See LICENSE file

---

## Contact & Support

For issues, feature requests, or questions:
- Open an GitHub Issue
- Contact: Marcos Vinícius Miguel da Paixão (marco@example.com)

---

## References

- [CVM Dados Abertos](https://dados.cvm.gov.br/)
- [B3 - Histórico de Cotações](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/)
- [BCB SGS API](https://www3.bcb.gov.br/sgspub/)
- [IPEA Ipeadata](http://www.ipeadata.gov.br/)
- [SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar)
- [FRED API](https://fredaccount.stlouisfed.org/)
- [World Bank Open Data](https://data.worldbank.org/)
- [Google Drive API](https://developers.google.com/drive/api)

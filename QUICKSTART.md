# Quick Start Guide

## Installation & Setup (5 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/marcosayo13/public-finance-data-hub.git
cd public-finance-data-hub
```

### 2. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install package
make setup
```

### 3. Configure Credentials

```bash
# Copy environment template
cp .env.example .env

# Edit .env (optional for basic testing)
vim .env
```

## First Commands

### List Available Sources

```bash
pfdh list-sources
```

Output:
```
Available Data Sources:

cvm             | fundamentals    | Brazil     | Brazilian Securities Commission open data
b3              | market_data     | Brazil     | Brazilian stock exchange market data
bcb             | macroeconomic   | Brazil     | Central Bank macro series
ipea            | macroeconomic   | Brazil     | Brazilian economic indicators
freda           | macroeconomic   | USA        | Federal Reserve economic data
...
```

### Download BCB Macroeconomic Data (No Auth Required)

```bash
pfdh ingest --source bcb \
  --from 2024-01-01 \
  --to 2026-02-27 \
  --log-level INFO
```

Output:
```
[INFO] Starting ingestion...
[INFO] ============================================================
[INFO] Ingesting: bcb
[INFO] Period: 2024-01-01 to 2026-02-27
[INFO] ============================================================
[INFO] Fetching BCB series selic_meta (1)...
[INFO] ✓ Fetched 786 records from BCB
[INFO] Saved curated: data/curated/macroeconomic/bcb_sgs/year=2026/month=2/data_20260227.parquet (786 rows)
[INFO] Saved manifest: data/manifests/macroeconomic/bcb_sgs/...
[INFO] ✓ Ingestion complete!
```

Data saved to: `data/curated/macroeconomic/bcb_sgs/`

### Download B3 Stock Market Data

```bash
pfdh ingest --source b3 \
  --from 2024-01-01 \
  --to 2026-02-27
```

Data saved to: `data/curated/market_data/b3_cotahist/`

### Download CVM Fundamentals

```bash
pfdh ingest --source cvm \
  --from 2024-01-01 \
  --to 2026-02-27
```

Data saved to: `data/curated/fundamentals/cvm_dfp/`

## Google Drive Sync (First Time Setup)

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable **Google Drive API**
4. Create **OAuth 2.0 Desktop** credentials
5. Download JSON file

### Step 2: Configure PFDH

```bash
# Create secrets directory
mkdir -p secrets

# Move your downloaded JSON
cp ~/Downloads/client_secret_*.json secrets/client_secret.json

# Update .env
echo "GOOGLE_OAUTH_CLIENT_SECRETS=./secrets/client_secret.json" >> .env
echo "GOOGLE_DRIVE_FOLDER_ID=YOUR_FOLDER_ID_HERE" >> .env
```

### Step 3: Authenticate

```bash
pfdh auth-google
```

Browser opens → click "Allow" → Token saved automatically

### Step 4: Test Sync (Dry-Run)

```bash
pfdh sync-drive --folder-id YOUR_FOLDER_ID --dry-run
```

Output:
```
[INFO] [DRY-RUN] Would upload 47 datasets
[INFO]   - market_data/b3_cotahist (12 files)
[INFO]   - macroeconomic/bcb_sgs (8 files)
[INFO]   - fundamentals/cvm_dfp (27 files)
```

### Step 5: Actually Sync

```bash
pfdh sync-drive --folder-id YOUR_FOLDER_ID
```

Output:
```
[INFO] Syncing market_data/b3_cotahist...
[INFO] Uploaded: b3_cotahist/year=2024/month=01/data_20240131.parquet... [████████░░] 12.5 MB
[INFO] ✓ Sync complete. 47 files uploaded (2.3 GB).
```

## Full Automated Pipeline

### Ingest All Sources + Sync to Drive

```bash
pfdh run \
  --all \
  --sync-drive \
  --folder-id YOUR_FOLDER_ID
```

This:
1. Downloads all sources (BCB, B3, CVM, FRED, World Bank, etc.)
2. Normalizes to Parquet format
3. Syncs to Google Drive
4. Creates manifests with hashes

### Schedule with Cron (Linux/Mac)

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /path/to/public-finance-data-hub && pfdh run --all --sync-drive --folder-id YOUR_FOLDER_ID >> logs/pfdh_$(date +\%Y\%m\%d).log 2>&1
```

### Schedule with Task Scheduler (Windows)

```batch
# Create task that runs daily at 2 AM
taskscheduler: create /tn PFDH_Daily_Sync /tr "cmd /c cd C:\path\to\repo && pfdh run --all --sync-drive --folder-id YOUR_FOLDER_ID" /sc daily /st 02:00
```

## Data Access Examples

### Load BCB Macro Data in Python

```python
from public_finance_data_hub.storage.lake import DataLake
import pandas as pd

lake = DataLake()
df = lake.load_curated('macroeconomic', 'bcb_sgs')

print(df.head())
print(df.describe())
```

### Query B3 COTAHIST

```python
df_b3 = lake.load_curated('market_data', 'b3_cotahist')

# Filter by ticker and date
petr4 = df_b3[(df_b3['ticker'] == 'PETR4') & (df_b3['date'] >= '2024-06-01')]
print(petr4[['date', 'close', 'volume']])
```

### Analyze CVM Fundamentals

```python
df_cvm = lake.load_curated('fundamentals', 'cvm_dfp')
print(df_cvm.groupby('company')['revenue'].sum().sort_values(ascending=False))
```

## Development

### Run Tests

```bash
make test          # Run all tests
make test-cov      # Run tests with coverage
make lint          # Check code formatting
make format        # Auto-format code
```

### View Test Coverage

```bash
make test-cov
# Open htmlcov/index.html in browser
```

## Troubleshooting

### "No module named 'public_finance_data_hub'"

```bash
source venv/bin/activate
pip install -e .
```

### "Google Drive API: Permission Denied"

1. Verify `GOOGLE_DRIVE_FOLDER_ID` is correct
2. Check folder is shared with OAuth account
3. Run `pfdh auth-google` again

### "BCB connection timeout"

BCB service sometimes has issues. Retry with backoff (automatic):

```bash
pfdh ingest --source bcb --log-level DEBUG
```

### View Logs

```bash
ls logs/
cat logs/pfdh_20260227.log
```

## Next Steps

1. **Explore Data**: Load datasets in Pandas/Jupyter
2. **Add Custom Sources**: Extend `connectors/` for your needs
3. **Configure Alerts**: Get notified on ingestion failures
4. **Analytics**: Build dashboards on top of data lake
5. **CI/CD**: Push to GitHub → auto-runs tests & deploys

## Support

- **Issues**: [GitHub Issues](https://github.com/marcosayo13/public-finance-data-hub/issues)
- **Documentation**: [README.md](./README.md)
- **Examples**: See `tests/` directory

---

**Happy data engineering! 🚀**

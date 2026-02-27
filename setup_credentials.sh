#!/bin/bash

# Setup script for PFDH credentials
# This script helps you configure Google Drive OAuth and API keys

set -e

echo ""
echo "========================================"
echo "  PFDH Credentials Setup"
echo "========================================"
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "[i] Found existing .env file"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping .env update"
        exit 0
    fi
fi

# Create secrets directory
mkdir -p secrets
echo "[✓] Created ./secrets directory"

# Check for client_secret.json
if [ ! -f secrets/client_secret.json ]; then
    echo ""
    echo "[!] Google OAuth credentials not found"
    echo ""
    echo "Steps to get client_secret.json:"
    echo "  1. Go to: https://console.cloud.google.com/"
    echo "  2. Create a new project"
    echo "  3. Enable Google Drive API"
    echo "  4. Create OAuth 2.0 Desktop credentials"
    echo "  5. Download JSON file"
    echo "  6. Save as: secrets/client_secret.json"
    echo ""
    read -p "Press Enter when ready to continue..."
else
    echo "[✓] Found client_secret.json"
fi

# Get Google Drive Folder ID
echo ""
echo "Enter your Google Drive folder ID:"
echo "(Example: 1dHJ_r69H_idQyMJE4H60AtVNnDgEOHgF)"
read -p "Folder ID: " DRIVE_FOLDER_ID

if [ -z "$DRIVE_FOLDER_ID" ]; then
    echo "[!] Folder ID cannot be empty"
    exit 1
fi

# Get FRED API Key
echo ""
read -p "FRED API Key (optional, press Enter to skip): " FRED_KEY

# Get ANBIMA Credentials
echo ""
read -p "ANBIMA Client ID (optional): " ANBIMA_ID
read -sp "ANBIMA Client Secret (optional): " ANBIMA_SECRET
echo ""

# Create/Update .env file
echo ""
echo "Creating .env file..."

cat > .env << EOF
# ============================================================================
# GOOGLE DRIVE CONFIGURATION
# ============================================================================
GOOGLE_DRIVE_FOLDER_ID=$DRIVE_FOLDER_ID
GOOGLE_OAUTH_CLIENT_SECRETS=./secrets/client_secret.json
GOOGLE_TOKEN_PATH=./token.json

# ============================================================================
# EXTERNAL API KEYS
# ============================================================================
FRED_API_KEY=$FRED_KEY

ANBIMA_CLIENT_ID=$ANBIMA_ID
ANBIMA_CLIENT_SECRET=$ANBIMA_SECRET
ANBIMA_API_KEY=

# ============================================================================
# DATA STORAGE
# ============================================================================
DATA_DIR=./data
CACHE_DIR=./.cache
LOGS_DIR=./logs

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============================================================================
# HTTP CLIENT
# ============================================================================
HTTP_TIMEOUT=30
HTTP_RETRIES=3
HTTP_BACKOFF_FACTOR=1.5
HTTP_CACHE_ENABLED=true
HTTP_CACHE_TTL=3600

# ============================================================================
# PIPELINE SETTINGS
# ============================================================================
DRY_RUN=false
VERBOSE=false
EOF

echo "[✓] Created .env file"

# Test authentication
echo ""
echo "========================================"
echo "  Testing Credentials"
echo "========================================"
echo ""

echo "[i] Installing package...
pip install -e . -q

echo "[i] Testing Google Drive authentication...
echo ""
echo "A browser window should open for authentication."
echo "Please grant access when prompted."
echo ""

if python -m public_finance_data_hub.cli auth-google; then
    echo ""
    echo "[✓] Google Drive authentication successful!"
else
    echo ""
    echo "[!] Authentication failed. Please try again:"
    echo "    pfdh auth-google"
fi

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Test data ingestion:"
echo "     pfdh ingest --source bcb --from 2024-01-01 --to 2024-12-31"
echo ""
echo "  2. Sync to Google Drive:"
echo "     pfdh sync-drive --folder-id $DRIVE_FOLDER_ID"
echo ""
echo "  3. Run full pipeline:"
echo "     pfdh run --all --sync-drive --folder-id $DRIVE_FOLDER_ID"
echo ""

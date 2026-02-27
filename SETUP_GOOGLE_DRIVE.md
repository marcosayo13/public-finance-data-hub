# Google Drive Setup for PFDH

This guide walks you through setting up Google Drive OAuth for syncing your data lake.

## Prerequisites

- Google account
- Access to Google Cloud Console
- Already cloned: `public-finance-data-hub` repository

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a Project"** at the top
3. Click **"NEW PROJECT"**
4. Name: `pfdh-data-hub`
5. Click **"CREATE"**
6. Wait ~30 seconds for project creation
7. Select your new project

## Step 2: Enable Google Drive API

1. Go to **APIs & Services** → **Library**
2. Search for: **"Google Drive API"**
3. Click the first result
4. Click **"ENABLE"**
5. Wait for API to be enabled

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** (top-left)
3. Select **"OAuth client ID"**
4. If prompted: Click **"CONFIGURE CONSENT SCREEN"** first
   - Select: **"External"** user type
   - Click **"CREATE"**
   - Fill in: App name = `PFDH`
   - Add your email
   - Click **"SAVE AND CONTINUE"** through all screens
5. Back in Credentials: Click **"+ CREATE CREDENTIALS"** again
6. Select **"OAuth client ID"**
7. Select application type: **"Desktop application"**
8. Name: `PFDH Desktop`
9. Click **"CREATE"**

## Step 4: Download Credentials

1. In Credentials page, you should see your newly created credential
2. Click the **download icon** (↓) on the right
3. File will be: `client_secret_*.json`
4. Move to your project:
   ```bash
   # From your Downloads folder:
   cp ~/Downloads/client_secret_*.json /path/to/public-finance-data-hub/secrets/client_secret.json
   ```

**⚠️ IMPORTANT**: Never commit this file to Git! It's already in `.gitignore`.

## Step 5: Create Data Folder in Google Drive

1. Go to [Google Drive](https://drive.google.com/)
2. Click **"+ New"** → **"Folder"**
3. Name: `PFDH Data Lake`
4. Right-click folder → **"Get link"** (if needed to share)
5. Click on folder to open it
6. Look at the URL:
   ```
   https://drive.google.com/drive/folders/[THIS_IS_YOUR_FOLDER_ID]
   ```
7. Copy the folder ID (long alphanumeric string)

**Your Folder ID looks like:**
```
1dHJ_r69H_idQyMJE4H60AtVNnDgEOHgF
```

## Step 6: Configure PFDH

### Option A: Automated Setup (Recommended)

```bash
cd public-finance-data-hub
bash setup_credentials.sh
```

This will:
- Create `.env` file
- Ask for your credentials
- Test authentication

### Option B: Manual Setup

1. Copy template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```bash
   nano .env  # or vim, or open in your editor
   ```

3. Update these lines:
   ```
   GOOGLE_DRIVE_FOLDER_ID=1dHJ_r69H_idQyMJE4H60AtVNnDgEOHgF
   GOOGLE_OAUTH_CLIENT_SECRETS=./secrets/client_secret.json
   GOOGLE_TOKEN_PATH=./token.json
   ```

4. Verify `client_secret.json` exists:
   ```bash
   ls -la secrets/client_secret.json
   ```

## Step 7: Authenticate PFDH

```bash
# First time only - opens browser
pfdh auth-google
```

What happens:
1. Browser opens to Google login
2. You'll see a consent screen
3. Click **"Allow"**
4. You'll be redirected to `localhost`
5. Window closes automatically
6. `token.json` is created in your project

**✓ You're done!** token.json is now saved and will be reused.

## Step 8: Test Sync

```bash
# First, download some data
pfdh ingest --source bcb --from 2024-01-01 --to 2024-12-31

# Then test sync (dry-run shows what would be uploaded)
pfdh sync-drive --folder-id 1dHJ_r69H_idQyMJE4H60AtVNnDgEOHgF --dry-run

# Actually sync
pfdh sync-drive --folder-id 1dHJ_r69H_idQyMJE4H60AtVNnDgEOHgF
```

## Troubleshooting

### "client_secret.json not found"

```bash
# Check if file exists
ls -la secrets/client_secret.json

# If not, download it again from Google Cloud Console
```

### "Folder ID is invalid"

1. Go to your folder in Google Drive
2. Check URL:
   ```
   https://drive.google.com/drive/folders/YOUR_FOLDER_ID
   ```
3. Copy the ID after `/folders/`
4. Update `.env` with correct ID

### "Authentication failed"

Re-authenticate:
```bash
pfdh auth-google --force
```

### "Permission denied"

1. Make sure the folder in Google Drive is not in a shared drive
2. Only your personal Drive folders work with OAuth
3. If it's a shared drive, use Service Account instead (see advanced section)

## Advanced: Service Account (for automation)

If you want to run PFDH on a server without browser interaction:

1. In Google Cloud Console → **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** → **"Service Account"**
3. Name: `pfdh-automation`
4. Create key: **"JSON"** type
5. File will be: `pfdh-automation-*.json`
6. Move to project:
   ```bash
   cp ~/Downloads/pfdh-automation-*.json secrets/service_account.json
   ```
7. Update `.env`:
   ```
   GOOGLE_SERVICE_ACCOUNT_JSON=./secrets/service_account.json
   ```
8. In your Google Drive folder: Right-click → **"Share"** → Add service account email
9. Done! PFDH will now use Service Account instead of OAuth

## File Structure After Setup

```
public-finance-data-hub/
├── .env                              # Your credentials (NOT committed)
├── secrets/
│   └── client_secret.json           # Google OAuth (NOT committed)
├── token.json                        # OAuth token (NOT committed)
├── data/
│   ├── raw/
│   └── curated/
└── ... (rest of files)
```

## Security Notes

✅ **These files are protected:**
- `.env` - listed in `.gitignore`
- `secrets/` - listed in `.gitignore`
- `token.json` - listed in `.gitignore`
- Nothing with credentials will be committed to Git

⚠️ **If you accidentally commit credentials:**
1. GitHub will notify you
2. Regenerate the credentials (invalidate the old ones)
3. Update your `.env`
4. Use `git filter-branch` to remove from history

## Next Steps

1. **Ingest data:**
   ```bash
   pfdh ingest --all
   ```

2. **Sync to Drive:**
   ```bash
   pfdh sync-drive --folder-id YOUR_ID
   ```

3. **Automate (cron):**
   ```bash
   # Add to crontab (runs daily at 2 AM)
   0 2 * * * cd /path/to/pfdh && pfdh run --all --sync-drive --folder-id YOUR_ID
   ```

---

**Still having issues?** Check:
- [README.md](./README.md) - General setup
- [QUICKSTART.md](./QUICKSTART.md) - Quick commands
- GitHub Issues - Community support

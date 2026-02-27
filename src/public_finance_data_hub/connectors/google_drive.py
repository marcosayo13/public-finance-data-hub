"""Google Drive connector for syncing data lake to cloud storage."""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

logger = logging.getLogger(__name__)


class GoogleDriveConnector:
    """Manages OAuth authentication and file syncing to Google Drive."""

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    CHUNK_SIZE = 50 * 1024 * 1024  # 50 MB chunks

    def __init__(self, folder_id: str, credentials_path: str, token_path: str):
        """Initialize Google Drive connector.

        Args:
            folder_id: Google Drive folder ID where data will be synced
            credentials_path: Path to client_secret.json
            token_path: Path where token.json will be stored
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google API client not available. Install with: pip install google-auth-oauthlib google-auth-httplib2"
            )

        self.folder_id = folder_id
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service = None
        self._authenticated = False

    def authenticate(self, force_refresh: bool = False) -> bool:
        """Authenticate with Google Drive using OAuth 2.0.

        Args:
            force_refresh: Force re-authentication even if token exists

        Returns:
            True if authentication successful
        """
        try:
            creds = None

            # Load existing token if available
            if self.token_path.exists() and not force_refresh:
                logger.info(f"Loading existing token from {self.token_path}")
                creds = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)
            else:
                # Create new OAuth flow
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"client_secret.json not found at {self.credentials_path}\n"
                        f"Get it from: https://console.cloud.google.com/"
                    )

                logger.info("Starting OAuth 2.0 authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info(f"Saving token to {self.token_path}")
                self.token_path.write_text(creds.to_json())

            # Refresh credentials if expired
            if creds and creds.expired and creds.refresh_token:
                logger.debug("Refreshing expired credentials")
                creds.refresh(Request())

            self.service = build("drive", "v3", credentials=creds)
            self._authenticated = True
            logger.info("✓ Successfully authenticated with Google Drive")
            return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def authenticate_service_account(self, service_account_json: str) -> bool:
        """Authenticate using Service Account (for automation).

        Args:
            service_account_json: Path to service account JSON key

        Returns:
            True if authentication successful
        """
        try:
            sa_path = Path(service_account_json)
            if not sa_path.exists():
                raise FileNotFoundError(f"Service account JSON not found: {service_account_json}")

            logger.info("Authenticating with Service Account...")
            creds = ServiceAccountCredentials.from_service_account_file(
                str(sa_path), scopes=self.SCOPES
            )
            self.service = build("drive", "v3", credentials=creds)
            self._authenticated = True
            logger.info("✓ Successfully authenticated with Service Account")
            return True

        except Exception as e:
            logger.error(f"Service Account authentication failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self._authenticated and self.service is not None

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def find_remote_file(self, name: str, parent_id: str) -> Optional[str]:
        """Find file in Google Drive by name.

        Returns:
            File ID if found, None otherwise
        """
        try:
            results = (
                self.service.files()
                .list(
                    q=f"name='{name}' and '{parent_id}' in parents and trashed=false",
                    spaces="drive",
                    fields="files(id, name, size, modifiedTime)",
                    pageSize=1,
                )
                .execute()
            )
            files = results.get("files", [])
            return files[0]["id"] if files else None
        except HttpError as e:
            logger.warning(f"Error searching for file: {e}")
            return None

    def ensure_folder_exists(self, folder_name: str, parent_id: str) -> str:
        """Create folder if it doesn't exist.

        Returns:
            Folder ID
        """
        try:
            # Check if folder exists
            results = (
                self.service.files()
                .list(
                    q=f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                    spaces="drive",
                    fields="files(id)",
                    pageSize=1,
                )
                .execute()
            )
            files = results.get("files", [])

            if files:
                return files[0]["id"]

            # Create new folder
            logger.debug(f"Creating folder: {folder_name}")
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = self.service.files().create(body=file_metadata, fields="id").execute()
            return folder["id"]

        except HttpError as e:
            logger.error(f"Error managing folder: {e}")
            raise

    def upload_file(
        self, file_path: Path, remote_path: str, dry_run: bool = False
    ) -> Optional[str]:
        """Upload file to Google Drive.

        Args:
            file_path: Local file path
            remote_path: Remote path (e.g., "market_data/b3_cotahist/file.parquet")
            dry_run: If True, only show what would be uploaded

        Returns:
            File ID if uploaded, None if skipped
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated with Google Drive")

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            # Parse remote path
            parts = remote_path.split("/")
            file_name = parts[-1]
            folder_parts = parts[:-1]

            # Navigate/create folder hierarchy
            current_folder_id = self.folder_id
            for folder_name in folder_parts:
                current_folder_id = self.ensure_folder_exists(folder_name, current_folder_id)

            file_size = file_path.stat().st_size
            file_hash = self.get_file_hash(file_path)

            # Check if file exists remotely
            existing_file_id = self.find_remote_file(file_name, current_folder_id)

            if existing_file_id:
                logger.info(
                    f"File exists remotely: {remote_path} (ID: {existing_file_id})"
                )
                # Could check hash here to determine if update needed
                return existing_file_id

            if dry_run:
                logger.info(f"[DRY-RUN] Would upload: {remote_path} ({file_size / 1024 / 1024:.2f} MB)")
                return None

            logger.info(f"Uploading: {remote_path} ({file_size / 1024 / 1024:.2f} MB)")

            file_metadata = {
                "name": file_name,
                "parents": [current_folder_id],
                "properties": {
                    "local_path": str(file_path),
                    "hash_sha256": file_hash,
                    "uploaded_at": datetime.now().isoformat(),
                },
            }

            media = MediaFileUpload(str(file_path), resumable=True, chunksize=self.CHUNK_SIZE)
            request = self.service.files().create(
                body=file_metadata, media_body=media, fields="id, webViewLink"
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Upload progress: {progress}%")

            file_id = response["id"]
            logger.info(f"✓ Uploaded: {remote_path} (ID: {file_id})")
            return file_id

        except Exception as e:
            logger.error(f"Upload failed for {remote_path}: {e}")
            return None

    def sync_directory(
        self,
        local_dir: Path,
        remote_prefix: str = "",
        dry_run: bool = False,
        pattern: str = "*.parquet",
    ) -> Dict[str, Any]:
        """Recursively sync directory to Google Drive.

        Args:
            local_dir: Local directory to sync
            remote_prefix: Remote folder path prefix
            dry_run: If True, only show what would be synced
            pattern: File pattern to sync (e.g., "*.parquet")

        Returns:
            Sync statistics
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated with Google Drive")

        if not local_dir.exists():
            logger.warning(f"Local directory not found: {local_dir}")
            return {"uploaded": 0, "skipped": 0, "errors": 0, "total_size": 0}

        stats = {"uploaded": 0, "skipped": 0, "errors": 0, "total_size": 0, "files": []}

        # Find all files matching pattern
        files = list(local_dir.rglob(pattern))
        logger.info(f"Found {len(files)} files to sync")

        for file_path in files:
            try:
                # Calculate relative path
                rel_path = file_path.relative_to(local_dir)
                remote_path = str(Path(remote_prefix) / rel_path).replace("\\", "/")

                file_id = self.upload_file(file_path, remote_path, dry_run=dry_run)

                if file_id:
                    stats["uploaded"] += 1
                    stats["files"].append(
                        {
                            "name": str(rel_path),
                            "size": file_path.stat().st_size,
                            "file_id": file_id,
                        }
                    )
                else:
                    stats["skipped"] += 1

                stats["total_size"] += file_path.stat().st_size

            except Exception as e:
                logger.error(f"Error syncing {file_path}: {e}")
                stats["errors"] += 1

        logger.info(
            f"Sync complete: {stats['uploaded']} uploaded, "
            f"{stats['skipped']} skipped, {stats['errors']} errors"
        )
        return stats

    def list_remote_files(self, folder_id: Optional[str] = None) -> list:
        """List files in remote folder."""
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated with Google Drive")

        folder_id = folder_id or self.folder_id
        try:
            results = (
                self.service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces="drive",
                    fields="files(id, name, mimeType, size, modifiedTime)",
                    pageSize=1000,
                )
                .execute()
            )
            return results.get("files", [])
        except HttpError as e:
            logger.error(f"Error listing files: {e}")
            return []

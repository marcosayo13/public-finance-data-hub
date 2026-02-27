"""Google Drive connector for syncing data."""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
import os
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    raise ImportError("Google API client not installed")

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleDriveConnector:
    """Google Drive connector for file sync."""

    def __init__(
        self,
        folder_id: str,
        oauth_client_secrets: Optional[str] = None,
        token_path: Optional[str] = None,
        service_account_json: Optional[str] = None,
    ):
        """Initialize Google Drive connector.

        Args:
            folder_id: Target Drive folder ID
            oauth_client_secrets: Path to OAuth client secrets JSON
            token_path: Path to store/load OAuth token
            service_account_json: Path to service account JSON key
        """
        self.folder_id = folder_id
        self.oauth_client_secrets = oauth_client_secrets
        self.token_path = token_path
        self.service = None

        # Initialize with OAuth or Service Account
        if service_account_json and Path(service_account_json).exists():
            self._init_service_account(service_account_json)
        elif oauth_client_secrets:
            self._init_oauth(oauth_client_secrets, token_path)
        else:
            raise ValueError("Must provide oauth_client_secrets or service_account_json")

    def _init_oauth(self, client_secrets: str, token_path: Optional[str]) -> None:
        """Initialize OAuth 2.0 authentication."""
        token_path = token_path or "token.json"

        credentials = None
        if Path(token_path).exists():
            with open(token_path, "rb") as token_file:
                credentials = pickle.load(token_file)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets, SCOPES
                )
                credentials = flow.run_local_server(port=0)

            with open(token_path, "wb") as token_file:
                pickle.dump(credentials, token_file)

        self.service = build("drive", "v3", credentials=credentials)
        logger.info("Initialized Google Drive with OAuth 2.0")

    def _init_service_account(self, service_account_json: str) -> None:
        """Initialize service account authentication."""
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json, scopes=SCOPES
        )
        self.service = build("drive", "v3", credentials=credentials)
        logger.info("Initialized Google Drive with Service Account")

    def upload_file(
        self,
        file_path: Path,
        parent_folder_id: Optional[str] = None,
        remote_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> Optional[str]:
        """Upload file to Drive.

        Args:
            file_path: Local file path
            parent_folder_id: Parent folder ID (default: self.folder_id)
            remote_name: Remote file name (default: file_path.name)
            dry_run: If True, don't actually upload

        Returns:
            File ID if successful
        """
        parent_folder_id = parent_folder_id or self.folder_id
        remote_name = remote_name or file_path.name

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        if dry_run:
            logger.info(f"[DRY-RUN] Would upload {file_path.name} to Drive")
            return None

        try:
            file_metadata = {
                "name": remote_name,
                "parents": [parent_folder_id],
            }

            media = MediaFileUpload(file_path, chunksize=10 * 1024 * 1024)
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )

            file_id = file.get("id")
            logger.info(f"Uploaded {file_path.name} -> {file_id}")
            return file_id

        except Exception as e:
            logger.error(f"Error uploading {file_path.name}: {e}")
            return None

    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Optional[str]:
        """Create folder in Drive.

        Args:
            folder_name: Folder name
            parent_folder_id: Parent folder ID
            dry_run: If True, don't actually create

        Returns:
            Folder ID if successful
        """
        parent_folder_id = parent_folder_id or self.folder_id

        if dry_run:
            logger.info(f"[DRY-RUN] Would create folder '{folder_name}'")
            return None

        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id],
            }

            folder = (
                self.service.files()
                .create(
                    body=file_metadata,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )

            folder_id = folder.get("id")
            logger.info(f"Created folder '{folder_name}' -> {folder_id}")
            return folder_id

        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return None

    def list_files(
        self, folder_id: Optional[str] = None, query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List files in Drive folder.

        Args:
            folder_id: Folder ID
            query: Optional query string

        Returns:
            List of file metadata dicts
        """
        folder_id = folder_id or self.folder_id

        try:
            q = f"'{folder_id}' in parents and trashed=false"
            if query:
                q += f" and {query}"

            results = (
                self.service.files()
                .list(
                    q=q,
                    spaces="drive",
                    fields="files(id, name, mimeType, size, createdTime)",
                    pageSize=1000,
                    supportsAllDrives=True,
                )
                .execute()
            )

            return results.get("files", [])

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def file_exists(self, filename: str, folder_id: Optional[str] = None) -> bool:
        """Check if file exists in Drive.

        Args:
            filename: File name to search for
            folder_id: Folder ID

        Returns:
            True if file exists
        """
        files = self.list_files(
            folder_id, query=f"name='{filename}'"
        )
        return len(files) > 0

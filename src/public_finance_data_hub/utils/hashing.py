"""Hashing utilities for data deduplication and integrity verification."""

import hashlib
from pathlib import Path
from typing import Optional


def calculate_sha256(content: bytes) -> str:
    """Calculate SHA256 hash of content.

    Args:
        content: Bytes to hash

    Returns:
        SHA256 hex digest
    """
    return hashlib.sha256(content).hexdigest()


def calculate_file_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of file.

    Args:
        file_path: Path to file

    Returns:
        SHA256 hex digest
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """Verify file SHA256 hash.

    Args:
        file_path: Path to file
        expected_hash: Expected SHA256 hash

    Returns:
        True if hash matches
    """
    return calculate_file_sha256(file_path) == expected_hash


def calculate_md5(content: bytes) -> str:
    """Calculate MD5 hash of content.

    Args:
        content: Bytes to hash

    Returns:
        MD5 hex digest
    """
    return hashlib.md5(content).hexdigest()


def calculate_file_md5(file_path: Path) -> str:
    """Calculate MD5 hash of file.

    Args:
        file_path: Path to file

    Returns:
        MD5 hex digest
    """
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

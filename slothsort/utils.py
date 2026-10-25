"""Utility functions for SlothSort: filename sanitization, collision handling, and time helpers."""

import json
import os
import re
import time
from pathlib import Path

# Characters disallowed in Windows file systems: < > : " / \ | ? * and ASCII controls
ILLEGAL_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE_PATTERN = re.compile(r'\s+')

DEFAULT_CONFIG = {
    "categories": [
        "Bills",
        "Study",
        "Career",
        "Photos",
        "Installers",
        "Archives",
        "Documents",
        "Other",
    ],
    "extension_rules": {
        "Photos": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"],
        "Installers": [".exe", ".msi", ".dmg"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    },
    "skip_extensions": [".crdownload", ".part", ".tmp"],
    "skip_if_modified_within_minutes": 10,
    "default_model": "gemma3:4b",
}


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Sanitize a filename candidate by removing illegal characters and trimming.

    - Removes Windows illegal characters: < > : " / \\ | ? * and control chars
    - Normalizes consecutive spaces
    - Trims leading/trailing spaces and dots
    - Limits stem length to avoid MAX_PATH issues
    """
    if not name or not isinstance(name, str):
        return "unnamed_file"

    # Replace illegal characters with empty string
    cleaned = ILLEGAL_CHARS_PATTERN.sub("", name)

    # Normalize whitespace
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned).strip()

    # Strip leading/trailing dots and spaces (Windows limitation)
    cleaned = cleaned.strip(". ")

    if not cleaned:
        return "unnamed_file"

    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". ")

    return cleaned or "unnamed_file"


def get_unique_path(target_path: Path) -> Path:
    """Ensure target path does not overwrite an existing file.

    If target_path exists, appends ' (2)', ' (3)', etc. before suffix.
    """
    if not target_path.exists():
        return target_path

    parent = target_path.parent
    stem = target_path.stem
    suffix = target_path.suffix

    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def is_recent_file(path: Path, minutes: int = 10) -> bool:
    """Return True if the file was modified within the given number of minutes."""
    try:
        mtime = path.stat().st_mtime
        age_seconds = time.time() - mtime
        return age_seconds < (minutes * 60)
    except (OSError, FileNotFoundError):
        return False


def load_categories_config(config_path: Path | None = None) -> dict:
    """Load categories.json or fall back to safe default configuration."""
    if config_path is None:
        # Check current working dir then project root
        candidates = [
            Path.cwd() / "categories.json",
            Path(__file__).resolve().parent.parent / "categories.json",
        ]
        for c in candidates:
            if c.is_file():
                config_path = c
                break

    if config_path and config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Verify minimum required fields
                if "categories" in data and isinstance(data["categories"], list):
                    return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError):
            pass

    return DEFAULT_CONFIG.copy()

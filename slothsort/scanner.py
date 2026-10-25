"""Scanner module: Discovers top-level files in a directory while filtering out

subdirectories, active downloads, temporary files, and recent files.
"""

from pathlib import Path
from typing import List, Optional
from slothsort.utils import is_recent_file, load_categories_config

# Files created by SlothSort or OS that should never be sorted
IGNORED_FILENAMES = {
    "slothsort_undo.json",
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
}


def scan_folder(
    folder_path: str | Path,
    config: Optional[dict] = None,
    ignore_recent_check: bool = False,
) -> List[Path]:
    """Scan folder for candidate files to sort.

    Safety requirements:
    1. Top-level only: subdirectories are never processed.
    2. Skips active download files (.crdownload, .part, .tmp).
    3. Skips files modified within the configured threshold (default: 10 mins).
    4. Skips undo manifest and system files.
    """
    target = Path(folder_path).resolve()
    if not target.is_dir():
        raise NotADirectoryError(f"Target path '{folder_path}' is not a directory.")

    if config is None:
        config = load_categories_config()

    skip_extensions = [ext.lower() for ext in config.get("skip_extensions", [".crdownload", ".part", ".tmp"])]
    skip_minutes = int(config.get("skip_if_modified_within_minutes", 10))

    eligible_files: List[Path] = []

    for item in target.iterdir():
        # Top-level only: never touch directories
        if not item.is_file():
            continue

        filename_lower = item.name.lower()

        # Skip hidden/system and SlothSort log files
        if filename_lower in IGNORED_FILENAMES or item.name.startswith("."):
            continue

        # Skip active download and temp extensions
        if any(filename_lower.endswith(ext) for ext in skip_extensions):
            continue

        # Skip files modified recently (might still be in use / downloading)
        if not ignore_recent_check and is_recent_file(item, minutes=skip_minutes):
            continue

        eligible_files.append(item)

    # Sort files by name for consistent, deterministic processing order
    eligible_files.sort(key=lambda p: p.name.lower())
    return eligible_files

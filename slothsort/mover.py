"""Mover module: Safely executes planned file moves, writes the undo log,

and reverses previous operations.
"""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from slothsort.planner import PlanItem

logger = logging.getLogger(__name__)
UNDO_FILENAME = "slothsort_undo.json"


def execute_plan(plan: List[PlanItem], root_folder: str | Path) -> Dict[str, Any]:
    """Execute the plan moves on disk and record an undo manifest.

    Guarantees:
    - Never deletes any file.
    - Creates destination category directories if needed.
    - Writes an undo log (slothsort_undo.json) with exact source and destination paths.
    """
    root = Path(root_folder).resolve()
    successful_moves: List[Dict[str, str]] = []
    errors: List[str] = []

    for item in plan:
        src = item.source_path
        dest = item.destination_path

        # If source doesn't exist, record error and skip
        if not src.exists():
            errors.append(f"Source file not found: {src.name}")
            continue

        try:
            # Ensure destination category folder exists
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Move file safely
            shutil.move(str(src), str(dest))
            successful_moves.append(
                {
                    "source": str(src.resolve()),
                    "destination": str(dest.resolve()),
                    "category": item.category,
                    "old_name": item.old_filename,
                    "new_name": item.new_filename,
                }
            )
        except Exception as exc:
            logger.error("Failed to move %s -> %s: %s", src, dest, exc)
            errors.append(f"Failed to move {src.name}: {exc}")

    # Write undo manifest
    undo_file = root / UNDO_FILENAME
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "root_folder": str(root),
        "total_planned": len(plan),
        "total_moved": len(successful_moves),
        "moves": successful_moves,
    }

    try:
        with open(undo_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    except OSError as exc:
        logger.error("Failed to write undo manifest to %s: %s", undo_file, exc)
        errors.append(f"Failed to write undo log: {exc}")

    return {
        "success": len(errors) == 0,
        "moved_count": len(successful_moves),
        "error_count": len(errors),
        "errors": errors,
        "undo_file": str(undo_file),
    }


def undo_last_run(root_folder: str | Path) -> Dict[str, Any]:
    """Reverse the last run recorded in slothsort_undo.json.

    Moves files back to their original locations and cleans up empty category folders.
    """
    root = Path(root_folder).resolve()
    undo_file = root / UNDO_FILENAME

    if not undo_file.is_file():
        return {
            "success": False,
            "restored_count": 0,
            "error_count": 1,
            "errors": [f"No undo file found at: {undo_file}"],
        }

    try:
        with open(undo_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as exc:
        return {
            "success": False,
            "restored_count": 0,
            "error_count": 1,
            "errors": [f"Failed to read undo manifest: {exc}"],
        }

    moves: List[Dict[str, str]] = manifest.get("moves", [])
    restored: List[str] = []
    errors: List[str] = []
    affected_directories = set()

    # Process in reverse order of execution
    for entry in reversed(moves):
        src_path = Path(entry["source"])
        dest_path = Path(entry["destination"])

        if not dest_path.exists():
            errors.append(f"Target file missing, cannot restore: {dest_path.name}")
            continue

        try:
            # Ensure original parent directory exists
            src_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file back
            shutil.move(str(dest_path), str(src_path))
            restored.append(dest_path.name)
            affected_directories.add(dest_path.parent)
        except Exception as exc:
            errors.append(f"Failed to restore {dest_path.name}: {exc}")

    # Clean up empty category directories created by SlothSort
    for folder in affected_directories:
        try:
            # Only remove if empty and within root
            if folder != root and folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
        except OSError:
            pass

    # Remove the undo manifest once undone
    try:
        undo_file.unlink(missing_ok=True)
    except OSError:
        pass

    return {
        "success": len(errors) == 0,
        "restored_count": len(restored),
        "error_count": len(errors),
        "errors": errors,
    }

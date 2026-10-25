"""Planner module: Combines scanner, rule engine, text extractors,

and AI classifier to construct a complete file organization plan.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from slothsort.ai import classify_with_ai
from slothsort.extract import extract_text_snippet
from slothsort.rules import get_rule_category
from slothsort.scanner import scan_folder
from slothsort.utils import get_unique_path, load_categories_config, sanitize_filename


@dataclass
class PlanItem:
    """Represents an intended move for a single file."""

    source_path: Path
    destination_path: Path
    category: str
    old_filename: str
    new_filename: str
    method: str  # 'rule', 'ai', 'no-ai-default'

    @property
    def is_renamed(self) -> bool:
        return self.old_filename != self.new_filename


def build_plan(
    folder_path: str | Path,
    config: Optional[dict] = None,
    use_ai: bool = True,
    model: Optional[str] = None,
    ignore_recent_check: bool = False,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
) -> List[PlanItem]:
    """Scan folder and build the list of planned file moves.

    Does not move or alter any files on disk (pure dry-run planning).
    """
    root_folder = Path(folder_path).resolve()
    if config is None:
        config = load_categories_config()

    categories: List[str] = config.get("categories", ["Other"])
    extension_rules: Dict[str, List[str]] = config.get("extension_rules", {})
    selected_model: str = model or config.get("default_model", "gemma3:4b")

    files = scan_folder(root_folder, config=config, ignore_recent_check=ignore_recent_check)
    plan_items: List[PlanItem] = []
    # Track reserved destination paths to avoid internal collisions in a single plan run
    reserved_destinations: Set[Path] = set()

    total_files = len(files)

    for index, file_path in enumerate(files, start=1):
        filename = file_path.name
        suffix = file_path.suffix

        # Step 1: Fast rules check
        category = get_rule_category(filename, extension_rules)
        method = "rule"
        new_stem = file_path.stem

        if category is None:
            # Step 2: Ambiguous file (needs AI or fallback)
            if use_ai:
                if progress_callback:
                    progress_callback(filename, "Analyzing with AI...", index, total_files)

                snippet = extract_text_snippet(file_path, max_chars=500)
                ai_result = classify_with_ai(
                    name=filename,
                    snippet=snippet,
                    categories=categories,
                    model=selected_model,
                )
                category = ai_result.get("category", "Other")
                new_stem = ai_result.get("new_name", file_path.stem)
                method = "ai"
            else:
                # No-AI mode: group documents or use Other
                method = "no-ai-default"
                if suffix.lower() in (".pdf", ".docx", ".doc", ".txt"):
                    category = "Documents" if "Documents" in categories else "Other"
                else:
                    category = "Other"

        if progress_callback and method == "rule":
            progress_callback(filename, "Classified by extension rule", index, total_files)

        # Validate category again defensively
        if category not in categories:
            category = "Other"

        # Build proposed clean filename
        sanitized_stem = sanitize_filename(new_stem)
        proposed_filename = f"{sanitized_stem}{suffix}"

        # Target directory: <root>/<Category>/
        target_dir = root_folder / category
        candidate_dest = target_dir / proposed_filename

        # Collision avoidance: check disk AND already planned items
        unique_dest = _resolve_collision(candidate_dest, reserved_destinations)
        reserved_destinations.add(unique_dest)

        plan_items.append(
            PlanItem(
                source_path=file_path,
                destination_path=unique_dest,
                category=category,
                old_filename=filename,
                new_filename=unique_dest.name,
                method=method,
            )
        )

    return plan_items


def _resolve_collision(candidate_dest: Path, reserved_destinations: Set[Path]) -> Path:
    """Find a unique destination path considering both disk and currently reserved plan targets."""
    # First check disk collision
    resolved = get_unique_path(candidate_dest)

    # Then check against destinations already reserved in this plan session
    if resolved not in reserved_destinations:
        return resolved

    parent = resolved.parent
    stem = resolved.stem
    suffix = resolved.suffix

    counter = 2
    while True:
        alt = parent / f"{stem} ({counter}){suffix}"
        if not alt.exists() and alt not in reserved_destinations:
            return alt
        counter += 1

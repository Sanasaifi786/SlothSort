"""Fast rules-based classification for obvious file extensions."""

from pathlib import Path


def get_rule_category(filename_or_path: str | Path, extension_rules: dict[str, list[str]]) -> str | None:
    """Check if the file matches an obvious extension rule.

    Returns the category name (e.g., 'Photos', 'Installers', 'Archives')
    or None if ambiguous (e.g. .pdf, .docx, .txt, .csv) and requires AI or deeper analysis.
    """
    path = Path(filename_or_path)
    suffix = path.suffix.lower()

    if not suffix:
        return None

    for category, extensions in extension_rules.items():
        # Match case-insensitively
        normalized_exts = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions]
        if suffix in normalized_exts:
            return category

    return None

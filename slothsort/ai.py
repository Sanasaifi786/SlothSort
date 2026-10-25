"""Local AI classification module using Ollama and Gemma 3."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from slothsort.utils import sanitize_filename

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You organise files. Choose ONE category from: {categories}.
Also suggest a short, clean file name (no extension, max 6 words) based on its content.
File name: {name}
Start of content: {snippet}
Reply ONLY as JSON: {{"category": "...", "new_name": "..."}}"""


def parse_ai_response(content: str, categories: List[str], original_filename: str) -> Dict[str, str]:
    """Defensively parse and validate AI response string.

    Guarantees:
    - Never throws an exception
    - Category is strictly validated against allowed categories (fallback: 'Other')
    - Suggested new_name is sanitized and stripped of accidental file extensions
    """
    stem = Path(original_filename).stem
    default_result = {"category": "Other", "new_name": sanitize_filename(stem)}

    if not content or not isinstance(content, str):
        return default_result

    cleaned = content.strip()
    # Strip markdown code blocks if the model wrapped output in ```json ... ```
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("AI output is not valid JSON: %r", content)
        return default_result

    if not isinstance(data, dict):
        return default_result

    category = data.get("category")
    if not isinstance(category, str) or category not in categories:
        category = "Other"

    raw_new_name = data.get("new_name")
    if isinstance(raw_new_name, str) and raw_new_name.strip():
        # Remove any file extension the model might have appended
        name_candidate = Path(raw_new_name).stem
        sanitized = sanitize_filename(name_candidate)
        new_name = sanitized if sanitized and sanitized != "unnamed_file" else sanitize_filename(stem)
    else:
        new_name = sanitize_filename(stem)

    return {"category": category, "new_name": new_name}


def classify_with_ai(
    name: str,
    snippet: str,
    categories: List[str],
    model: str = "gemma3:4b",
    client: Optional[Any] = None,
) -> Dict[str, str]:
    """Call local Ollama model to classify a document and suggest a clean filename.

    Falls back safely if Ollama is unreachable, model missing, or output malformed.
    """
    stem = Path(name).stem
    fallback_result = {"category": "Other", "new_name": sanitize_filename(stem)}

    try:
        if client is None:
            import ollama

            client = ollama

        prompt = PROMPT_TEMPLATE.format(
            categories=", ".join(categories),
            name=name,
            snippet=snippet[:500] if snippet else "(no text extractable)",
        )

        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.0},
        )

        content = response["message"]["content"]
        return parse_ai_response(content, categories, original_filename=name)

    except Exception as exc:
        logger.warning("Ollama AI classification failed for '%s': %s", name, exc)
        # Safe fallback: category remains 'Documents' if extension is document-like, else 'Other'
        ext = Path(name).suffix.lower()
        cat = "Documents" if ext in (".pdf", ".docx", ".txt", ".rtf") else "Other"
        if cat not in categories:
            cat = "Other"
        fallback_result["category"] = cat
        return fallback_result

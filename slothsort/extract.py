"""Extract text snippets from documents (.pdf, .docx, .txt, etc.) for AI classification."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_snippet(file_path: str | Path, max_chars: int = 500) -> str:
    """Extract up to max_chars of text from a document to help AI understand its content.

    Returns an empty string if text cannot be extracted or file is binary/unsupported.
    Never raises an unhandled exception.
    """
    path = Path(file_path)
    if not path.is_file():
        return ""

    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            return _extract_from_pdf(path, max_chars)
        elif suffix in (".docx", ".doc"):
            return _extract_from_docx(path, max_chars)
        elif suffix in (".txt", ".md", ".csv", ".json", ".log", ".rtf", ".xml", ".html", ".htm"):
            return _extract_from_plaintext(path, max_chars)
        else:
            return ""
    except Exception as exc:
        logger.debug("Failed to extract snippet from %s: %s", path.name, exc)
        return ""


def _extract_from_pdf(path: Path, max_chars: int) -> str:
    """Extract text from the first page of a PDF."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return ""

        if not reader.pages:
            return ""

        first_page = reader.pages[0]
        text = first_page.extract_text() or ""
        return " ".join(text.split())[:max_chars]
    except Exception:
        return ""


def _extract_from_docx(path: Path, max_chars: int) -> str:
    """Extract text from paragraphs of a DOCX document."""
    try:
        import docx

        doc = docx.Document(str(path))
        lines = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                lines.append(text)
            if sum(len(line) for line in lines) >= max_chars:
                break

        full_text = " ".join(lines)
        return " ".join(full_text.split())[:max_chars]
    except Exception:
        return ""


def _extract_from_plaintext(path: Path, max_chars: int) -> str:
    """Extract text from a plain text or markup file."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(max_chars * 2)
            return " ".join(content.split())[:max_chars]
    except Exception:
        return ""

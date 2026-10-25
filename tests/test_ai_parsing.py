import pytest
from unittest.mock import MagicMock
from slothsort.ai import parse_ai_response, classify_with_ai

CATEGORIES = ["Bills", "Study", "Career", "Photos", "Installers", "Documents", "Other"]


def test_parse_valid_json():
    raw = '{"category": "Bills", "new_name": "2026-10 Airtel bill"}'
    res = parse_ai_response(raw, CATEGORIES, "airtel_oct.pdf")
    assert res["category"] == "Bills"
    assert res["new_name"] == "2026-10 Airtel bill"


def test_parse_markdown_fenced_json():
    raw = '```json\n{"category": "Study", "new_name": "Data Structures Notes"}\n```'
    res = parse_ai_response(raw, CATEGORIES, "ds_notes.pdf")
    assert res["category"] == "Study"
    assert res["new_name"] == "Data Structures Notes"


def test_parse_unknown_category_fallback():
    raw = '{"category": "Astronomy", "new_name": "Star map"}'
    res = parse_ai_response(raw, CATEGORIES, "sky.pdf")
    # Category not in allowed list must safely fall back to 'Other'
    assert res["category"] == "Other"
    assert res["new_name"] == "Star map"


def test_parse_broken_json():
    raw = 'Not JSON at all! Just raw text.'
    res = parse_ai_response(raw, CATEGORIES, "important_doc.pdf")
    assert res["category"] == "Other"
    assert res["new_name"] == "important_doc"


def test_parse_strips_extension_from_suggested_name():
    # If the model accidentally appends '.pdf' to new_name, we must strip it so it doesn't become .pdf.pdf
    raw = '{"category": "Bills", "new_name": "october_electricity.pdf"}'
    res = parse_ai_response(raw, CATEGORIES, "bill(1).pdf")
    assert res["new_name"] == "october_electricity"


def test_classify_with_ai_mock_client():
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {
            "content": '{"category": "Career", "new_name": "Senior Software Resume"}'
        }
    }

    result = classify_with_ai(
        name="my_cv_v2.docx",
        snippet="John Doe, 5 years python experience...",
        categories=CATEGORIES,
        client=mock_client,
    )

    assert result["category"] == "Career"
    assert result["new_name"] == "Senior Software Resume"
    mock_client.chat.assert_called_once()

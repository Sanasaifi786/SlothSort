from pathlib import Path
import pytest
from slothsort.utils import (
    sanitize_filename,
    get_unique_path,
    is_recent_file,
    load_categories_config,
)


def test_sanitize_filename_illegal_chars():
    dirty = 'Airtel:oct*bill?version<1>|test"file.pdf'
    clean = sanitize_filename(dirty)
    assert ":" not in clean
    assert "*" not in clean
    assert "?" not in clean
    assert "<" not in clean
    assert ">" not in clean
    assert "|" not in clean
    assert '"' not in clean
    assert clean == "Airteloctbillversion1testfile.pdf"


def test_sanitize_filename_trailing_dots_and_spaces():
    dirty = "   my resume notes. . .   "
    clean = sanitize_filename(dirty)
    assert clean == "my resume notes"


def test_sanitize_filename_empty():
    assert sanitize_filename("") == "unnamed_file"
    assert sanitize_filename("   ???:::***  ") == "unnamed_file"


def test_sanitize_filename_max_length():
    long_name = "a" * 150
    clean = sanitize_filename(long_name, max_length=50)
    assert len(clean) <= 50


def test_get_unique_path(tmp_path: Path):
    file1 = tmp_path / "document.pdf"
    # When file does not exist yet, returns exact path
    assert get_unique_path(file1) == file1

    # Create file1
    file1.touch()
    unique1 = get_unique_path(file1)
    assert unique1.name == "document (2).pdf"

    # Create document (2).pdf as well
    unique1.touch()
    unique2 = get_unique_path(file1)
    assert unique2.name == "document (3).pdf"


def test_is_recent_file(tmp_path: Path):
    file1 = tmp_path / "fresh.txt"
    file1.touch()
    assert is_recent_file(file1, minutes=10) is True
    assert is_recent_file(file1, minutes=0) is False


def test_load_categories_config():
    config = load_categories_config()
    assert "categories" in config
    assert "Photos" in config["categories"]
    assert "Bills" in config["categories"]
    assert ".jpg" in config["extension_rules"]["Photos"]

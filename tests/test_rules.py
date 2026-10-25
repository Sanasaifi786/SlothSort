from pathlib import Path
import pytest
from slothsort.rules import get_rule_category


@pytest.fixture
def sample_extension_rules():
    return {
        "Photos": [".jpg", ".jpeg", ".png", ".webp"],
        "Installers": [".exe", ".msi"],
        "Archives": [".zip", ".tar.gz", ".7z"],
    }


def test_get_rule_category_photos(sample_extension_rules):
    assert get_rule_category("IMG_2026.JPG", sample_extension_rules) == "Photos"
    assert get_rule_category(Path("holiday_photo.png"), sample_extension_rules) == "Photos"


def test_get_rule_category_installers(sample_extension_rules):
    assert get_rule_category("vscode_setup.exe", sample_extension_rules) == "Installers"
    assert get_rule_category("installer.MSI", sample_extension_rules) == "Installers"


def test_get_rule_category_ambiguous_returns_none(sample_extension_rules):
    # Documents and code should not match simple extension rules; they require deeper analysis
    assert get_rule_category("Airtel_bill_oct.pdf", sample_extension_rules) is None
    assert get_rule_category("DS_notes.docx", sample_extension_rules) is None
    assert get_rule_category("readme.txt", sample_extension_rules) is None
    assert get_rule_category("data.csv", sample_extension_rules) is None


def test_get_rule_category_no_extension(sample_extension_rules):
    assert get_rule_category("LICENSE", sample_extension_rules) is None

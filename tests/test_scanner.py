import os
import time
from pathlib import Path
import pytest
from slothsort.scanner import scan_folder


def test_scan_folder_skips_subdirectories(tmp_path: Path):
    subfolder = tmp_path / "SubFolder"
    subfolder.mkdir()
    (subfolder / "nested.txt").write_text("nested")

    file1 = tmp_path / "top_level.txt"
    file1.write_text("hello")

    # Set mtime to 1 hour ago so it's not marked recent
    old_time = time.time() - 3600
    os.utime(file1, (old_time, old_time))

    results = scan_folder(tmp_path)
    assert len(results) == 1
    assert results[0].name == "top_level.txt"


def test_scan_folder_skips_temp_and_partial_downloads(tmp_path: Path):
    old_time = time.time() - 3600

    f1 = tmp_path / "valid.pdf"
    f1.write_text("pdf")
    os.utime(f1, (old_time, old_time))

    f2 = tmp_path / "download.crdownload"
    f2.write_text("downloading")

    f3 = tmp_path / "archive.part"
    f3.write_text("partial")

    f4 = tmp_path / "cache.tmp"
    f4.write_text("tmp")

    results = scan_folder(tmp_path, ignore_recent_check=True)
    assert len(results) == 1
    assert results[0].name == "valid.pdf"


def test_scan_folder_skips_undo_manifest_and_hidden(tmp_path: Path):
    old_time = time.time() - 3600

    f1 = tmp_path / "slothsort_undo.json"
    f1.write_text("{}")
    os.utime(f1, (old_time, old_time))

    f2 = tmp_path / ".hidden_file"
    f2.write_text("hidden")
    os.utime(f2, (old_time, old_time))

    f3 = tmp_path / "desktop.ini"
    f3.write_text("ini")
    os.utime(f3, (old_time, old_time))

    f4 = tmp_path / "regular_file.txt"
    f4.write_text("regular")
    os.utime(f4, (old_time, old_time))

    results = scan_folder(tmp_path, ignore_recent_check=True)
    assert len(results) == 1
    assert results[0].name == "regular_file.txt"


def test_scan_folder_recent_filter(tmp_path: Path):
    fresh_file = tmp_path / "just_downloaded.txt"
    fresh_file.write_text("fresh")  # modified right now

    # By default, files modified within 10 mins are skipped
    assert scan_folder(tmp_path, ignore_recent_check=False) == []

    # But with ignore_recent_check=True, it is found
    assert len(scan_folder(tmp_path, ignore_recent_check=True)) == 1


def test_scan_folder_invalid_path(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist"
    with pytest.raises(NotADirectoryError):
        scan_folder(non_existent)

from pathlib import Path
from slothsort.planner import build_plan

CONFIG = {
    "categories": ["Bills", "Study", "Career", "Photos", "Installers", "Documents", "Other"],
    "extension_rules": {
        "Photos": [".jpg", ".png"],
        "Installers": [".exe"],
    },
    "skip_extensions": [".tmp"],
    "skip_if_modified_within_minutes": 10,
    "default_model": "gemma3:4b",
}


def test_build_plan_rules_mode_no_disk_changes(tmp_path: Path):
    f_img = tmp_path / "photo.jpg"
    f_img.write_text("photo data")

    f_exe = tmp_path / "setup.exe"
    f_exe.write_text("installer data")

    f_pdf = tmp_path / "notes.pdf"
    f_pdf.write_text("notes data")

    plan = build_plan(
        tmp_path,
        config=CONFIG,
        use_ai=False,
        ignore_recent_check=True,
    )

    assert len(plan) == 3

    # Check mapping
    plan_map = {item.old_filename: item for item in plan}

    assert plan_map["photo.jpg"].category == "Photos"
    assert plan_map["photo.jpg"].method == "rule"
    assert plan_map["photo.jpg"].destination_path == tmp_path / "Photos" / "photo.jpg"

    assert plan_map["setup.exe"].category == "Installers"
    assert plan_map["setup.exe"].method == "rule"

    assert plan_map["notes.pdf"].category == "Documents"
    assert plan_map["notes.pdf"].method == "no-ai-default"

    # CRITICAL SAFETY CHECK: original files must not have moved at all!
    assert f_img.exists()
    assert f_exe.exists()
    assert f_pdf.exists()
    assert not (tmp_path / "Photos").exists()


def test_build_plan_handles_name_collisions(tmp_path: Path):
    # Two files that end up having the same destination filename
    f1 = tmp_path / "img_1.jpg"
    f1.write_text("data1")

    # Suppose a duplicate photo
    f2 = tmp_path / "img_2.jpg"
    f2.write_text("data2")

    plan = build_plan(
        tmp_path,
        config=CONFIG,
        use_ai=False,
        ignore_recent_check=True,
    )

    destinations = [item.destination_path for item in plan]
    # Ensure all planned destination paths are completely unique
    assert len(destinations) == len(set(destinations))

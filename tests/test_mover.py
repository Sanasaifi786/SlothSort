from pathlib import Path
from slothsort.mover import execute_plan, undo_last_run, UNDO_FILENAME
from slothsort.planner import PlanItem


def test_execute_plan_and_undo(tmp_path: Path):
    # Setup test files
    f1 = tmp_path / "img_001.jpg"
    f1.write_text("image bytes")

    f2 = tmp_path / "invoice.pdf"
    f2.write_text("invoice data")

    dest1 = tmp_path / "Photos" / "img_001.jpg"
    dest2 = tmp_path / "Bills" / "Electricity Bill 2026.pdf"

    plan = [
        PlanItem(
            source_path=f1,
            destination_path=dest1,
            category="Photos",
            old_filename="img_001.jpg",
            new_filename="img_001.jpg",
            method="rule",
        ),
        PlanItem(
            source_path=f2,
            destination_path=dest2,
            category="Bills",
            old_filename="invoice.pdf",
            new_filename="Electricity Bill 2026.pdf",
            method="ai",
        ),
    ]

    # Step 1: Execute Plan
    result = execute_plan(plan, tmp_path)
    assert result["success"] is True
    assert result["moved_count"] == 2
    assert result["error_count"] == 0

    # Verify original files no longer in root, but now in destination categories
    assert not f1.exists()
    assert not f2.exists()
    assert dest1.exists()
    assert dest2.exists()

    # Verify undo file exists
    undo_file = tmp_path / UNDO_FILENAME
    assert undo_file.exists()

    # Step 2: Perform Undo
    undo_result = undo_last_run(tmp_path)
    assert undo_result["success"] is True
    assert undo_result["restored_count"] == 2

    # Verify original files are back
    assert f1.exists()
    assert f2.exists()

    # Verify category folders were cleaned up because they are now empty
    assert not (tmp_path / "Photos").exists()
    assert not (tmp_path / "Bills").exists()

    # Verify undo file was unlinked
    assert not undo_file.exists()


def test_undo_nonexistent_manifest(tmp_path: Path):
    result = undo_last_run(tmp_path)
    assert result["success"] is False
    assert result["restored_count"] == 0
    assert "No undo file found" in result["errors"][0]


def test_execute_plan_missing_source(tmp_path: Path):
    missing_file = tmp_path / "ghost.txt"
    dest = tmp_path / "Other" / "ghost.txt"

    plan = [
        PlanItem(
            source_path=missing_file,
            destination_path=dest,
            category="Other",
            old_filename="ghost.txt",
            new_filename="ghost.txt",
            method="default",
        )
    ]

    result = execute_plan(plan, tmp_path)
    assert result["moved_count"] == 0
    assert result["error_count"] == 1
    assert not dest.exists()

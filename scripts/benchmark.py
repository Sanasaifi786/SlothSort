"""Benchmark script: Measures accuracy and execution time for:

1. Rules-only sorting
2. Hybrid sorting (Rules + Gemma 3 4B via Ollama)
against the ground truth in labels.csv.
"""

import csv
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from slothsort.planner import build_plan
from slothsort.utils import load_categories_config

# Safe console encoding for Windows
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(safe_box=True)


def load_ground_truth(labels_path: Path) -> dict[str, str]:
    if not labels_path.is_file():
        raise FileNotFoundError(f"Cannot find labels file at {labels_path}")
    truth = {}
    with open(labels_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 2:
                truth[row[0].strip()] = row[1].strip()
    return truth


def run_benchmark(folder_path: Path, use_ai: bool, model: str = "gemma3:4b") -> tuple[int, int, float, list[dict]]:
    truth = load_ground_truth(folder_path / "labels.csv")
    config = load_categories_config()

    start_time = time.perf_counter()
    plan = build_plan(
        folder_path,
        config=config,
        use_ai=use_ai,
        model=model,
        ignore_recent_check=True,
    )
    elapsed = time.perf_counter() - start_time

    correct = 0
    total = len(truth)
    details = []

    plan_dict = {item.old_filename: item.category for item in plan}

    for filename, expected_cat in truth.items():
        predicted_cat = plan_dict.get(filename, "Uncategorized")
        is_match = predicted_cat.lower() == expected_cat.lower()
        if is_match:
            correct += 1
        details.append(
            {
                "filename": filename,
                "expected": expected_cat,
                "predicted": predicted_cat,
                "matched": is_match,
            }
        )

    return total, correct, elapsed, details


def main():
    test_folder = Path("test_downloads").resolve()
    if not test_folder.exists() or not (test_folder / "labels.csv").exists():
        console.print("[yellow]test_downloads folder not found. Generating now...[/yellow]")
        from scripts.make_test_folder import main as make_folder

        make_folder()

    console.print(Panel("[bold cyan]SlothSort Benchmark Suite[/bold cyan]\n"
                        "Comparing Rules-Only vs Hybrid (Rules + Gemma 3 4B)",
                        border_style="cyan"))

    # Test 1: Rules Only
    console.print("[bold yellow]Running Mode 1: Rules Only...[/bold yellow]")
    r_total, r_correct, r_time, r_details = run_benchmark(test_folder, use_ai=False)
    r_acc = (r_correct / r_total) * 100 if r_total else 0

    # Test 2: Hybrid (Rules + Gemma 3)
    console.print("[bold magenta]Running Mode 2: Hybrid (Rules + Gemma 3 4B)...[/bold magenta]")
    h_total, h_correct, h_time, h_details = run_benchmark(test_folder, use_ai=True, model="gemma3:4b")
    h_acc = (h_correct / h_total) * 100 if h_total else 0

    # Render Comparison Table
    table = Table(title="Hacktoberfest Benchmark Results (The 'Lazy Payoff')", border_style="green", show_lines=True)
    table.add_column("Mode", style="bold")
    table.add_column("Total Files", justify="center")
    table.add_column("Correct", justify="center")
    table.add_column("Accuracy", justify="center")
    table.add_column("Elapsed Time", justify="right")

    table.add_row(
        "[yellow]Rules Only[/yellow]",
        str(r_total),
        f"{r_correct}/{r_total}",
        f"{r_acc:.1f}%",
        f"{r_time:.2f}s",
    )
    table.add_row(
        "[magenta]Hybrid (Rules + Gemma 3 4B)[/magenta]",
        str(h_total),
        f"{h_correct}/{h_total}",
        f"[bold green]{h_acc:.1f}%[/bold green]",
        f"{h_time:.2f}s",
    )
    table.add_row(
        "[dim]Manual Sorting (Estimated)[/dim]",
        str(r_total),
        f"{r_total}/{r_total}",
        "100.0%",
        "~120.0s (2 min)",
    )

    console.print(table)


if __name__ == "__main__":
    main()

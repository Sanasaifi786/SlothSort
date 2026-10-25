"""Command-line interface for SlothSort using Rich terminal formatting."""

import argparse
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from slothsort.mover import execute_plan, undo_last_run
from slothsort.planner import PlanItem, build_plan
from slothsort.utils import load_categories_config

# Fix Windows console encoding if needed
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(safe_box=True)

BANNER = "[bold cyan]SlothSort[/bold cyan] - [dim]The Lazy, Private, Offline File Tidier[/dim]"


def print_banner() -> None:
    try:
        console.print(Panel(f"🦥 {BANNER}", border_style="cyan"))
    except UnicodeEncodeError:
        console.print(Panel(f"[*] {BANNER}", border_style="cyan"))



def display_plan_table(plan: list[PlanItem], root_folder: Path) -> None:
    """Render a clean Rich table showing planned file actions."""
    table = Table(title="Proposed File Organization Plan", border_style="blue", show_lines=True)

    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Original File", style="white", max_width=32, overflow="ellipsis")
    table.add_column("Category", style="bold green", no_wrap=True)
    table.add_column("Destination Path", style="cyan", max_width=45, overflow="ellipsis")
    table.add_column("Engine", justify="center", no_wrap=True)

    for i, item in enumerate(plan, 1):
        rel_dest = item.destination_path.relative_to(root_folder)

        if item.method == "rule":
            engine_str = "[yellow]Rule[/yellow]"
        elif item.method == "ai":
            engine_str = "[magenta]AI[/magenta]"
        else:
            engine_str = "[blue]Default[/blue]"

        dest_display = str(rel_dest)
        if item.is_renamed:
            dest_display = f"[bold cyan]{dest_display}[/bold cyan]"

        table.add_row(
            str(i),
            item.old_filename,
            item.category,
            dest_display,
            engine_str,
        )

    console.print(table)


def run_sort(args: argparse.Namespace) -> int:
    target_path = Path(args.folder).resolve()

    if not target_path.exists() or not target_path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Folder '{target_path}' does not exist or is not a directory.")
        return 1

    config = load_categories_config()
    model = args.model or config.get("default_model", "gemma3:4b")
    use_ai = not args.no_ai

    console.print(f"[bold]Target Folder:[/bold] [cyan]{target_path}[/cyan]")
    console.print(f"[bold]Mode:[/bold] {'[magenta]Hybrid (Rules + AI)[/magenta]' if use_ai else '[yellow]Rules Only (--no-ai)[/yellow]'}")
    if use_ai:
        console.print(f"[bold]Model:[/bold] [magenta]{model}[/magenta]")

    with console.status("[bold green]Scanning and analyzing files...[/bold green]"):
        try:
            plan = build_plan(
                target_path,
                config=config,
                use_ai=use_ai,
                model=model,
                ignore_recent_check=args.ignore_recent,
            )
        except Exception as exc:
            console.print(f"[bold red]Failed to build plan:[/bold red] {exc}")
            return 1

    if not plan:
        console.print(Panel("[green]No candidate files found to organize![/green]\n"
                            "(Files may be in subfolders, active downloads, or modified in the last 10 minutes)",
                            title="Result", border_style="green"))
        return 0

    display_plan_table(plan, target_path)

    # Calculate statistics
    rule_count = sum(1 for p in plan if p.method == "rule")
    ai_count = sum(1 for p in plan if p.method == "ai")
    renamed_count = sum(1 for p in plan if p.is_renamed)

    summary_text = (
        f"Total Files: [bold]{len(plan)}[/bold] | "
        f"Rule matches: [yellow]{rule_count}[/yellow] | "
        f"AI classified: [magenta]{ai_count}[/magenta] | "
        f"Smart renamed: [cyan]{renamed_count}[/cyan]"
    )
    console.print(Panel(summary_text, title="Plan Summary", border_style="blue"))

    if not args.apply:
        console.print(
            Panel(
                "[bold yellow]DRY-RUN COMPLETE[/bold yellow]: No files were moved or changed on disk.\n"
                f"To execute this plan, run:\n"
                f"  [bold green]python -m slothsort \"{target_path}\" --apply[/bold green]",
                border_style="yellow",
            )
        )
        return 0

    # Apply changes
    with console.status("[bold green]Executing file moves...[/bold green]"):
        result = execute_plan(plan, target_path)

    if result["success"]:
        console.print(
            Panel(
                f"[bold green]Successfully organized {result['moved_count']} files![/bold green]\n"
                f"Undo log created: [dim]{result['undo_file']}[/dim]\n"
                f"To reverse this operation at any time, run:\n"
                f"  [bold cyan]python -m slothsort undo \"{target_path}\"[/bold cyan]",
                title="Success",
                border_style="green",
            )
        )
        return 0
    else:
        console.print(
            Panel(
                f"[bold red]Completed with errors:[/bold red]\n"
                f"Moved: {result['moved_count']} | Errors: {result['error_count']}\n"
                + "\n".join(f"- {e}" for e in result["errors"]),
                title="Partial Error",
                border_style="red",
            )
        )
        return 1


def run_undo(args: argparse.Namespace) -> int:
    target_path = Path(args.folder).resolve()

    if not target_path.exists() or not target_path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Folder '{target_path}' does not exist or is not a directory.")
        return 1

    console.print(f"[bold]Reversing organization in:[/bold] [cyan]{target_path}[/cyan]")

    with console.status("[bold green]Restoring files to original locations...[/bold green]"):
        result = undo_last_run(target_path)

    if result["success"]:
        console.print(
            Panel(
                f"[bold green]Successfully restored {result['restored_count']} files to their original locations![/bold green]\n"
                "Empty category folders cleaned up.",
                title="Undo Complete",
                border_style="green",
            )
        )
        return 0
    else:
        console.print(
            Panel(
                f"[bold red]Undo failed or encountered errors:[/bold red]\n"
                f"Restored: {result['restored_count']} | Errors: {result['error_count']}\n"
                + "\n".join(f"- {e}" for e in result["errors"]),
                title="Undo Failed",
                border_style="red",
            )
        )
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    raw_args = argv if argv is not None else sys.argv[1:]

    # Handle 'undo' command directly without parser conflicts
    if raw_args and raw_args[0] == "undo":
        undo_parser = argparse.ArgumentParser(
            prog="slothsort undo",
            description="Reverse the last SlothSort run in a folder",
        )
        undo_parser.add_argument(
            "folder",
            nargs="?",
            default=".",
            help="Target folder to reverse (default: current directory)",
        )
        parsed_undo = undo_parser.parse_args(raw_args[1:])
        print_banner()
        return run_undo(parsed_undo)

    parser = argparse.ArgumentParser(
        prog="slothsort",
        description="A lazy, private, offline file tidier powered by local open-weight AI.",
    )
    parser.add_argument("folder", nargs="?", default=".", help="Target folder to organize (default: current directory)")
    parser.add_argument("--apply", action="store_true", help="Execute the file moves (default is dry-run preview)")
    parser.add_argument("--no-ai", action="store_true", help="Fast mode: classify by extension rules only")
    parser.add_argument("--model", type=str, default=None, help="Ollama model name (default: gemma3:4b)")
    parser.add_argument("--ignore-recent", action="store_true", help="Process files even if modified within last 10 mins")

    print_banner()
    args = parser.parse_args(raw_args)
    return run_sort(args)



if __name__ == "__main__":
    sys.exit(main())

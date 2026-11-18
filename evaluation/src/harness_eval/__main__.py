"""CLI entry point for the SDLC Harness evaluation framework.

Usage:
    python -m harness_eval list-evaluators
"""

from __future__ import annotations

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("harness_eval")


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        description="SDLC Harness Evaluation Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── list-evaluators ──────────────────────────────────────────────
    subparsers.add_parser("list-evaluators", help="List available evaluators")

    args = parser.parse_args()

    if args.command == "list-evaluators":
        _cmd_list_evaluators()
    else:
        parser.print_help()


def _cmd_list_evaluators() -> None:
    """Execute the ``list-evaluators`` subcommand with a styled table."""
    from rich.console import Console
    from rich.table import Table

    from harness_eval.runner import list_evaluators

    console = Console()
    evals = list_evaluators()

    if evals:
        table = Table(title=f"Available Evaluators ({len(evals)})")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        for i, name in enumerate(evals, 1):
            table.add_row(str(i), name)
        console.print(table)
    else:
        console.print("[yellow]No evaluators registered.[/]")


if __name__ == "__main__":
    main()

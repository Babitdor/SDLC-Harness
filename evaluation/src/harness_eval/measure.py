"""Standalone cost/token measurement for the SDLC pipeline.

Runs the real pipeline on a prompt one or more times and reports the tokens
consumed and estimated USD cost for each trial, plus a summary. This is the
ad-hoc measurement path, independent of the graded task-suite: perfect for
benchmarking a prompt, comparing models/endpoints, or checking a cost budget
before committing to a longer eval run.

Usage:
    uv run python -m harness_eval.measure --prompt "Build a UAV SDLC model..." --trials 3
    uv run python -m harness_eval.measure --prompt "..." --model gpt-4o --output cost_report

Writes ``<output>.json`` and ``<output>.csv`` when ``--output`` is given, and always
prints a table to the terminal.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import time
import uuid
from pathlib import Path

from harness_eval.costs import estimate_cost, get_prices

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("harness_eval.measure")


async def measure(
    prompt: str,
    trials: int = 1,
    model: str | None = None,
    keep_containers: bool = False,
) -> list[dict]:
    """Run the pipeline ``trials`` times and return a row of metrics per trial."""
    from harness_eval.run import run_pipeline

    rows: list[dict] = []
    for i in range(trials):
        thread_id = f"measure-{i}-{uuid.uuid4().hex[:8]}"
        inputs = {
            "request": prompt,
            "project_id": f"measure-{uuid.uuid4().hex[:6]}",
            "thread_id": thread_id,
            "cleanup": not keep_containers,
        }
        t0 = time.time()
        outputs = await run_pipeline(inputs)
        wall_s = round(time.time() - t0, 2)

        usage = outputs.get("usage") or {}
        in_tok = int(usage.get("input_tokens") or 0)
        out_tok = int(usage.get("output_tokens") or 0)
        total = int(usage.get("total_tokens") or 0)
        reasoning_tok = int(usage.get("reasoning_tokens") or 0)
        calls = int(usage.get("calls") or 0)
        invocations = int(usage.get("invocations") or calls or 0)
        process = outputs.get("process") or {}
        subagent_calls = process.get("subagent_calls") or {}
        subagent_total = sum(subagent_calls.values())
        used_model = model or usage.get("model")
        prices, fallback = get_prices(used_model)
        est = estimate_cost(in_tok, out_tok, used_model, prices=prices)

        rows.append(
            {
                "trial": i,
                "thread_id": thread_id,
                "wall_s": wall_s,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": total,
                "reasoning_tokens": reasoning_tok,
                "llm_calls": calls,
                "llm_invocations": invocations,
                "subagent_calls": subagent_total,
                "model": used_model,
                "cost_usd": est["cost_usd"],
                "used_fallback_price": fallback or est["used_fallback_price"],
                "error": outputs.get("_error"),
            }
        )
        logger.info(
            "trial=%d total=%d in=%d out=%d reasoning=%d calls=%d invocations=%d "
            "subagents=%d cost=$%.4f",
            i, total, in_tok, out_tok, reasoning_tok, calls, invocations,
            subagent_total, est["cost_usd"],
        )
    return rows


def _print_table(rows: list[dict]) -> None:
    from rich.console import Console
    from rich.table import Table

    table = Table(title="Cost / Token / Process measurement")
    for col in (
        "trial", "total_tokens", "input_tokens", "output_tokens",
        "reasoning_tokens", "llm_calls", "llm_invocations", "subagent_calls",
        "wall_s", "model", "cost_usd",
    ):
        table.add_column(col, style="cyan" if col != "cost_usd" else "green")
    for r in rows:
        table.add_row(
            str(r["trial"]), str(r["total_tokens"]), str(r["input_tokens"]),
            str(r["output_tokens"]), str(r["reasoning_tokens"]),
            str(r["llm_calls"]), str(r["llm_invocations"]), str(r["subagent_calls"]),
            str(r["wall_s"]),
            str(r["model"] or ""), f"${r['cost_usd']:.4f}",
        )
    Console().print(table)

    totals = sum(r["total_tokens"] for r in rows)
    total_cost = sum(r["cost_usd"] for r in rows)
    print(f"Trials: {len(rows)} | total tokens: {totals} "
          f"| total cost: ${total_cost:.4f} | "
          f"avg cost/trial: ${(total_cost / len(rows)):.4f}" if rows else "No trials.")


def _write_files(rows: list[dict], out_stem: Path) -> None:
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    json_path = out_stem.with_suffix(".json")
    json_path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote %s", json_path)

    csv_path = out_stem.with_suffix(".csv")
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    logger.info("Wrote %s", csv_path)


async def _run(
    prompt: str, trials: int, model: str | None, output: str | None,
    keep_containers: bool,
) -> None:
    rows = await measure(prompt, trials=trials, model=model, keep_containers=keep_containers)
    _print_table(rows)
    if output:
        _write_files(rows, Path(output))


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure cost/tokens of SDLC pipeline runs")
    parser.add_argument("--prompt", required=True, help="The user prompt / requirements brief")
    parser.add_argument("--trials", type=int, default=1, help="Number of runs (default: 1)")
    parser.add_argument("--model", default=None, help="Override model name for pricing")
    parser.add_argument("--output", default=None, help="Write JSON+CSV report to this stem (no extension)")
    parser.add_argument("--keep-containers", action="store_true", help="Do not tear down per-run Docker containers")
    args = parser.parse_args()
    asyncio.run(_run(args.prompt, args.trials, args.model, args.output, args.keep_containers))


if __name__ == "__main__":
    main()

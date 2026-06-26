"""
main.py — Entry point for the Playwright Recorder → Converter → Executor
framework.

Modes
-----
convert   Convert a JSONL recording to simplified JSON (no browser).
run       Convert + execute a JSONL recording end-to-end.
execute   Execute an already-converted JSON file.

Examples
--------
# Convert only
python main.py convert recordings/amazon.jsonl

# Convert then execute
python main.py run recordings/amazon.jsonl --headless

# Execute a pre-converted file
python main.py execute output/amazon.json --browser firefox
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from converter.jsonl_converter import JSONLConverter
from executor.playwright_executor import ActionExecutor
from executor.report_generator import ReportGenerator

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------

def cmd_convert(args: argparse.Namespace) -> None:
    """Convert a JSONL recording to structured flow JSON."""
    input_path = Path(args.input)
    output_path = (
        Path(args.output)
        if args.output
        else Path("output") / input_path.with_suffix(".json").name
    )

    converter = JSONLConverter()
    flow = converter.convert_file(input_path)
    converter.save(output_path, flow)
    print(f"Converted {len(flow['steps'])} steps \u2192 {output_path}")
    cred_count = len(flow["schema"]["credentials"])
    param_count = len(flow["schema"]["runParameters"])
    if cred_count or param_count:
        print(f"Schema: {cred_count} credential(s), {param_count} run parameter(s) detected.")


async def _execute_flow(
    flow: dict,
    runtime_values: dict,
    recording_file: str,
    headless: bool,
    browser: str,
    channel: str | None,
    slow_mo: int,
) -> None:
    executor = ActionExecutor(
        headless=headless,
        browser=browser,
        channel=channel,
        slow_mo=slow_mo,
    )
    reporter = ReportGenerator()

    report = await executor.execute(
        flow, runtime_values=runtime_values, recording_file=recording_file
    )

    reporter.print_summary(report)
    saved = reporter.save(report)
    print(f"Full report: {saved}")

    if report.failed:
        sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    """Convert a JSONL recording and immediately execute it."""
    input_path = Path(args.input)
    output_path = (
        Path(args.output)
        if args.output
        else Path("output") / input_path.with_suffix(".json").name
    )

    converter = JSONLConverter()
    actions = converter.convert_file(input_path)
    converter.save(output_path, actions)
    print(f"Converted {len(actions)} actions → {output_path}")

    asyncio.run(
        _execute_actions(
            actions=actions,
            recording_file=str(input_path),
            headless=args.headless,
            browser=args.browser,
            channel=args.channel,
            slow_mo=args.slow_mo,
        )
    )


def cmd_execute(args: argparse.Namespace) -> None:
    """Execute an already-converted flow JSON file."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found \u2014 {input_path}", file=sys.stderr)
        sys.exit(1)

    flow = json.loads(input_path.read_text(encoding="utf-8"))
    runtime_values = _load_params(args.params)

    asyncio.run(
        _execute_flow(
            flow=flow,
            runtime_values=runtime_values,
            recording_file=str(input_path),
            headless=args.headless,
            browser=args.browser,
            channel=args.channel,
            slow_mo=args.slow_mo,
        )
    )


def _load_params(params_path: str | None) -> dict:
    """Load runtime values from a JSON file (flat key=value dict)."""
    if not params_path:
        return {}
    p = Path(params_path)
    if not p.exists():
        logger.warning("Params file not found: %s", p)
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main",
        description="Playwright Recorder → Converter → Executor Framework",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── convert ─────────────────────────────────────────────────────────
    p_convert = subparsers.add_parser("convert", help="Convert JSONL to structured flow JSON")
    p_convert.add_argument("input", help="Path to the .jsonl recording")
    p_convert.add_argument("-o", "--output", help="Output .json path (default: output/<name>.json)")

    # ── run ─────────────────────────────────────────────────────────────
    p_run = subparsers.add_parser("run", help="Convert and execute a JSONL recording")
    p_run.add_argument("input", help="Path to the .jsonl recording")
    p_run.add_argument("-o", "--output", help="Output .json path (default: output/<name>.json)")
    p_run.add_argument("--params", default=None, help="JSON file with runtime parameter values")
    _add_browser_args(p_run)

    # ── execute ──────────────────────────────────────────────────────────
    p_exec = subparsers.add_parser("execute", help="Execute a pre-converted flow JSON file")
    p_exec.add_argument("input", help="Path to the converted .json flow file")
    p_exec.add_argument("--params", default=None, help="JSON file with runtime parameter values")
    _add_browser_args(p_exec)

    return parser


def _add_browser_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--headless", action="store_true", default=False,
        help="Run browser in headless mode",
    )
    p.add_argument(
        "--browser", default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser engine (default: chromium)",
    )
    p.add_argument(
        "--channel", default=None,
        help="Browser channel, e.g. msedge, chrome",
    )
    p.add_argument(
        "--slow-mo", dest="slow_mo", type=int, default=0,
        help="Milliseconds between operations (default: 0)",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "convert": cmd_convert,
        "run":     cmd_run,
        "execute": cmd_execute,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()

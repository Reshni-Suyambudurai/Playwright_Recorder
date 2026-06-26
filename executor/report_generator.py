"""
Report Generator — serialises an ``ExecutionReport`` to JSON and
writes it to the ``reports/`` directory.

Features
--------
* Human-readable summary JSON
* Timestamped filenames so reports are never overwritten
* Console summary printed to stdout
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.action_models import ExecutionReport

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")


class ReportGenerator:
    """
    Serialises an ``ExecutionReport`` to JSON and saves it to disk.

    Parameters
    ----------
    reports_dir:
        Directory where report files will be stored.
        Defaults to ``reports/``.
    """

    def __init__(self, reports_dir: str | Path = REPORTS_DIR) -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        report: ExecutionReport,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Write *report* to a JSON file.

        Parameters
        ----------
        report:
            The report to save.
        filename:
            Optional explicit filename (without extension).
            Defaults to a timestamp-based name.

        Returns
        -------
        Path
            Absolute path to the saved report file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = Path(report.recording_file).stem if report.recording_file else "run"
            filename = f"{stem}_{timestamp}"

        out_path = self.reports_dir / f"{filename}.json"
        payload = self._build_payload(report)
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Report saved: %s", out_path)
        return out_path

    def print_summary(self, report: ExecutionReport) -> None:
        """Print a concise summary to the console."""
        separator = "-" * 40
        print(separator)
        print("EXECUTION REPORT")
        print(separator)
        print(f"  Recording : {report.recording_file or 'N/A'}")
        print(f"  Total     : {report.total}")
        print(f"  Passed    : {report.passed}")
        print(f"  Failed    : {report.failed}")
        print(f"  Skipped   : {report.skipped}")
        print(f"  Duration  : {report.duration}")
        print(separator)

        if report.failed:
            print("FAILURES:")
            for result in report.results:
                if result.status == "failed":
                    print(f"  [{result.index}] {result.action}: {result.error}")
                    if result.screenshot:
                        print(f"       Screenshot: {result.screenshot}")
        print(separator)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_payload(report: ExecutionReport) -> dict:
        """
        Construct the JSON-serialisable payload.

        The summary block is placed first for readability; the detailed
        per-action results follow.
        """
        return {
            "summary": {
                "total":    report.total,
                "passed":   report.passed,
                "failed":   report.failed,
                "skipped":  report.skipped,
                "duration": report.duration,
                "recording_file": report.recording_file,
            },
            "results": [asdict(r) for r in report.results],
        }

"""
server.py — FastAPI backend for the Playwright Recorder Angular UI.

Endpoints
---------
GET  /api/flows           List all converted flow JSON files in output/
GET  /api/flows/{name}    Return a specific flow JSON (with schema)
POST /api/run             Execute a flow with user-supplied runtime values

Start:
    pip install fastapi uvicorn
    python server.py
Then open the Angular UI at http://localhost:8000
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import json
import logging
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from executor.playwright_executor import ActionExecutor
from executor.report_generator import ReportGenerator


# ---------------------------------------------------------------------------
# Windows / ProactorEventLoop helper
# ---------------------------------------------------------------------------

def _run_playwright_in_thread(
    executor: ActionExecutor,
    flow: dict,
    runtime_values: Dict[str, str],
    recording_file: str,
):
    """
    Run the async Playwright executor inside a **brand-new** ProactorEventLoop.

    uvicorn's server event loop is a SelectorEventLoop on Windows, which cannot
    launch subprocesses (Playwright uses them for browser IPC).  Running in a
    dedicated thread sidesteps that loop entirely.
    """
    if sys.platform == "win32":
        loop: asyncio.AbstractEventLoop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            executor.execute(
                flow,
                runtime_values=runtime_values,
                recording_file=recording_file,
            )
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Playwright Recorder API", version="1.0.0")

# Allow Angular dev server (ng serve on :4200) to call the API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all origins during development
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path("output")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    flowFile: str                        # e.g. "amazon.json"
    runtimeValues: Dict[str, str] = {}  # {"runParameters.email": "...", ...}
    headless: bool = False
    browser: str = "chromium"
    channel: Optional[str] = None
    slowMo: int = 0


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/flows")
def list_flows():
    """Return names of all flow JSON files in the output/ directory."""
    if not OUTPUT_DIR.exists():
        return {"flows": []}
    flows = sorted(f.name for f in OUTPUT_DIR.glob("*.json"))
    return {"flows": flows}


@app.get("/api/flows/{name}")
def get_flow(name: str):
    """Return the full flow JSON (including schema) for a given file name."""
    path = OUTPUT_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Flow '{name}' not found.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/run")
async def run_flow(req: RunRequest):
    """
    Execute a flow with caller-supplied runtime values.

    The runtimeValues dict is keyed by paramKey
    (e.g. ``"runParameters.email"`` or ``"credentials.password"``).
    """
    path = OUTPUT_DIR / req.flowFile
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Flow '{req.flowFile}' not found.")

    flow = json.loads(path.read_text(encoding="utf-8"))

    executor = ActionExecutor(
        headless=req.headless,
        browser=req.browser,
        channel=req.channel,
        slow_mo=req.slowMo,
    )
    reporter = ReportGenerator()

    report = None
    try:
        run_fn = functools.partial(
            _run_playwright_in_thread,
            executor, flow, req.runtimeValues, req.flowFile,
        )
        running_loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            report = await running_loop.run_in_executor(pool, run_fn)
    except Exception as exc:
        logging.error("Executor crashed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")

    reporter.save(report)

    return {
        "summary": {
            "total":    report.total,
            "passed":   report.passed,
            "failed":   report.failed,
            "skipped":  report.skipped,
            "duration": report.duration,
        },
        "results": [asdict(r) for r in report.results],
    }


# ---------------------------------------------------------------------------
# Serve Angular production build (optional — after `ng build`)
# ---------------------------------------------------------------------------

_dist = Path("ui/dist/playwright-recorder-ui/browser")
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

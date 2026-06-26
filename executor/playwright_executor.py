"""
Playwright Executor — replays a structured flow JSON against a live
browser using playwright.async_api.

Step format (new schema):
    { step, action, by, selector, value, rawValue, paramKey, isSensitive, meta }

    • `by`       — locator strategy: role | css | text | label | placeholder | testId | url
    • `selector` — locator value (string or {role, name} dict for role locators)
    • `value`    — may contain {{runParameters.xxx}} / {{credentials.xxx}} placeholders
    • `rawValue` — the literal value recorded; used as fallback when no runtime param given

Runtime values are passed as a flat dict:
    { "runParameters.email": "me@example.com", "credentials.password": "s3cr3t" }
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from models.action_models import ActionResult, ExecutionReport

logger = logging.getLogger(__name__)

ActionHandler = Callable[["ActionExecutor", Page, Dict[str, Any]], Coroutine[Any, Any, None]]
SCREENSHOTS_DIR = Path("screenshots")


# ---------------------------------------------------------------------------
# Locator builder  (uses new by/selector step format)
# ---------------------------------------------------------------------------

def _build_locator(page: Page, by: str, selector: Any):
    """Build a Playwright locator from a (by, selector) pair."""
    if by == "role" and isinstance(selector, dict):
        role = selector.get("role", "")
        kwargs: Dict[str, Any] = {}
        if "name" in selector:
            kwargs["name"] = selector["name"]
            kwargs["exact"] = False          # partial — recorded names may be truncated
        return page.get_by_role(role, **kwargs)

    if by == "text":        return page.get_by_text(str(selector),        exact=False)
    if by == "label":       return page.get_by_label(str(selector),       exact=False)
    if by == "placeholder": return page.get_by_placeholder(str(selector), exact=False)
    if by == "testId":      return page.get_by_test_id(str(selector))

    # css / default
    return page.locator(str(selector))


def _resolve(value: Any, runtime_values: Dict[str, str]) -> str:
    """Resolve {{xxx}} placeholders; fall back to raw string if not a placeholder."""
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        key = value[2:-2].strip()
        return runtime_values.get(key, "")
    return str(value) if value is not None else ""


# ---------------------------------------------------------------------------
# ActionExecutor
# ---------------------------------------------------------------------------

class ActionExecutor:
    """Replays a structured flow JSON (or steps list) using Playwright."""

    def __init__(
        self,
        headless: bool = False,
        browser: str = "chromium",
        channel: Optional[str] = None,
        slow_mo: int = 0,
        screenshots_dir: str | Path = SCREENSHOTS_DIR,
    ) -> None:
        self.headless = headless
        self.browser_name = browser
        self.channel = channel
        self.slow_mo = slow_mo
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_values: Dict[str, str] = {}
        self._dispatch: Dict[str, ActionHandler] = self._build_dispatch_table()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        flow: Dict[str, Any],
        runtime_values: Optional[Dict[str, str]] = None,
        recording_file: str = "",
    ) -> ExecutionReport:
        """
        Replay *flow* steps sequentially.

        Parameters
        ----------
        flow:
            Structured flow dict produced by JSONLConverter, or a plain
            list of steps for backward compatibility.
        runtime_values:
            Flat dict of resolved parameter values keyed by paramKey,
            e.g. ``{"runParameters.email": "me@x.com", "credentials.password": "s3cr3t"}``.
        """
        steps: List[Dict[str, Any]] = (
            flow.get("steps", []) if isinstance(flow, dict) else flow
        )
        self.runtime_values = runtime_values or {}

        report = ExecutionReport(
            total=len(steps),
            recording_file=recording_file or (
                flow.get("flowName", "") if isinstance(flow, dict) else ""
            ),
        )
        start_time = time.monotonic()

        async with async_playwright() as pw:
            browser = await self._launch_browser(pw)
            context: BrowserContext = await browser.new_context()
            page: Page = await context.new_page()

            for idx, step in enumerate(steps):
                result = await self._execute_step(page, idx, step)
                report.results.append(result)

                if result.status == "passed":
                    report.passed += 1
                elif result.status == "failed":
                    report.failed += 1
                    if not step.get("continueOnError", False):
                        logger.error(
                            "Halting at step %d (%s) — set continueOnError:true to skip.",
                            idx + 1, step.get("action"),
                        )
                        for remaining in steps[idx + 1:]:
                            report.results.append(ActionResult(
                                index=idx + 1,
                                action=remaining.get("action", "unknown"),
                                status="skipped",
                            ))
                            report.skipped += 1
                        break
                else:
                    report.skipped += 1

            await context.close()
            await browser.close()

        elapsed = time.monotonic() - start_time
        report.duration = f"{elapsed:.2f}s"
        return report

    # ------------------------------------------------------------------
    # Browser launch
    # ------------------------------------------------------------------

    async def _launch_browser(self, pw: Playwright) -> Browser:
        launcher = getattr(pw, self.browser_name)
        kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "slow_mo": self.slow_mo,
        }
        if self.channel:
            kwargs["channel"] = self.channel
        return await launcher.launch(**kwargs)

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------

    async def _execute_step(self, page: Page, idx: int, step: Dict[str, Any]) -> ActionResult:
        action_name = step.get("action", "unknown")
        result = ActionResult(index=idx, action=action_name, status="passed")
        t0 = time.monotonic()

        try:
            handler = self._dispatch.get(action_name)
            if handler is None:
                raise NotImplementedError(f"No handler for action '{action_name}'.")
            logger.info("[%d] %s", idx + 1, action_name)
            await handler(self, page, step)

        except Exception as exc:  # noqa: BLE001
            result.status = "failed"
            result.error = str(exc)
            logger.error("[%d] FAILED %s — %s", idx + 1, action_name, exc)
            screenshot_path = self.screenshots_dir / f"failure_{idx + 1}_{action_name}.png"
            try:
                await page.screenshot(path=str(screenshot_path))
                result.screenshot = str(screenshot_path)
            except Exception:  # noqa: BLE001
                pass

        finally:
            result.duration_ms = (time.monotonic() - t0) * 1000

        return result

    # ------------------------------------------------------------------
    # Action handlers  (step format: { action, by, selector, value, ... })
    # ------------------------------------------------------------------

    async def handle_goto(self, page: Page, step: Dict[str, Any]) -> None:
        await page.goto(step["selector"])

    async def handle_click(self, page: Page, step: Dict[str, Any]) -> None:
        await _build_locator(page, step["by"], step["selector"]).click()

    async def handle_fill(self, page: Page, step: Dict[str, Any]) -> None:
        locator = _build_locator(page, step["by"], step["selector"])
        value = _resolve(step.get("value"), self.runtime_values)
        if not value:                            # no runtime value — fall back to rawValue
            value = step.get("rawValue") or ""
        await locator.fill(value)

    async def handle_check(self, page: Page, step: Dict[str, Any]) -> None:
        await _build_locator(page, step["by"], step["selector"]).check()

    async def handle_uncheck(self, page: Page, step: Dict[str, Any]) -> None:
        await _build_locator(page, step["by"], step["selector"]).uncheck()

    async def handle_select_option(self, page: Page, step: Dict[str, Any]) -> None:
        locator = _build_locator(page, step["by"], step["selector"])
        raw = step.get("rawValue", "")
        await locator.select_option([raw] if raw else [])

    async def handle_hover(self, page: Page, step: Dict[str, Any]) -> None:
        await _build_locator(page, step["by"], step["selector"]).hover()

    async def handle_press(self, page: Page, step: Dict[str, Any]) -> None:
        await _build_locator(page, step["by"], step["selector"]).press(
            step.get("value", "")
        )

    async def handle_wait_for_timeout(self, page: Page, step: Dict[str, Any]) -> None:
        await page.wait_for_timeout(int(step.get("value", 1000)))

    async def handle_close_page(self, page: Page, step: Dict[str, Any]) -> None:  # noqa: ARG002
        await page.close()

    # ------------------------------------------------------------------
    # Dispatch table — register new actions here
    # ------------------------------------------------------------------

    def _build_dispatch_table(self) -> Dict[str, ActionHandler]:
        """
        Add a new action:
          1. Implement handle_<name>(self, page, step).
          2. Add one entry below.
        """
        return {
            "goto":           ActionExecutor.handle_goto,
            "click":          ActionExecutor.handle_click,
            "fill":           ActionExecutor.handle_fill,
            "check":          ActionExecutor.handle_check,
            "uncheck":        ActionExecutor.handle_uncheck,
            "selectOption":   ActionExecutor.handle_select_option,
            "hover":          ActionExecutor.handle_hover,
            "press":          ActionExecutor.handle_press,
            "waitForTimeout": ActionExecutor.handle_wait_for_timeout,
            "closePage":      ActionExecutor.handle_close_page,
            # ── Future: uploadFile, dragAndDrop, newTab, download, apiCall, assertion
        }

"""
JSONL Converter — reads Playwright JSONL recordings and produces a
structured flow JSON compatible with the framework executor and UI.

Output schema per step:
  { step, action, by, selector, value, rawValue, paramKey, isSensitive, meta }

Fill values are automatically parameterised:
  - sensitive fields (password/token/…) → credentials.xxx  → secret input
  - all other fill values               → runParameters.xxx → text input

Usage (CLI):
    python -m converter.jsonl_converter recordings/sample.jsonl output/sample.json

Usage (Python API):
    from converter.jsonl_converter import JSONLConverter
    converter = JSONLConverter()
    flow = converter.convert_file("recordings/sample.jsonl")
    converter.save("output/sample.json", flow)
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from converter.locator_parser import parse_locator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sensitive-field detection
# ---------------------------------------------------------------------------
SENSITIVE_KEYWORDS = {
    "password", "secret", "token", "apikey", "api_key",
    "passwd", "pin", "otp",
}

_MODIFIER_MAP = {1: "Alt", 2: "Control", 4: "Meta", 8: "Shift"}


def _is_sensitive(label: str, value: str = "") -> bool:
    text = f"{label} {value}".lower()
    return any(k in text for k in SENSITIVE_KEYWORDS)


def _safe_key(name: str) -> str:
    """Turn any string into a valid snake_case parameter key."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return clean or "field"


def _selector_label(by: str, selector: Any) -> str:
    """Derive a human-readable label from a locator for paramKey generation."""
    if by == "role" and isinstance(selector, dict):
        return selector.get("name") or selector.get("role", "field")
    if isinstance(selector, str):
        return re.sub(r"^[#.]", "", selector)   # strip CSS # / . prefix
    return "field"


def _param_key(field_label: str, sensitive: bool) -> str:
    prefix = "credentials" if sensitive else "runParameters"
    return f"{prefix}.{_safe_key(field_label)}"


def _placeholder(field_label: str, sensitive: bool) -> str:
    return "{{" + _param_key(field_label, sensitive) + "}}"


def _synthetic_raw(action: str, by: str, selector: Any, raw_value: Optional[str] = None) -> str:
    """Produce a TypeScript-style raw string for the meta field."""

    def _loc(b: str, s: Any) -> str:
        if b == "role" and isinstance(s, dict):
            return f"page.getByRole('{s.get('role', '')}', {{ name: '{s.get('name', '')}' }})"
        if b == "label":  return f"page.getByLabel('{s}')"
        if b == "text":   return f"page.getByText('{s}')"
        if b == "placeholder": return f"page.getByPlaceholder('{s}')"
        if b == "testId": return f"page.getByTestId('{s}')"
        return f"page.locator('{s}')"

    if action == "goto":           return f"await page.goto('{selector}');"
    if action == "fill":           return f"await {_loc(by, selector)}.fill('{raw_value}');"
    if action == "click":          return f"await {_loc(by, selector)}.click();"
    if action == "check":          return f"await {_loc(by, selector)}.check();"
    if action == "uncheck":        return f"await {_loc(by, selector)}.uncheck();"
    if action == "selectOption":   return f"await {_loc(by, selector)}.selectOption('{raw_value}');"
    if action == "hover":          return f"await {_loc(by, selector)}.hover();"
    if action == "press":          return f"await {_loc(by, selector)}.press('{raw_value}');"
    if action == "waitForTimeout": return f"await page.waitForTimeout({raw_value});"
    if action == "closePage":      return "await page.close();"
    return f"// {action}"


def _locator_to_by_selector(locator_dict: Dict[str, Any]) -> Tuple[str, Any]:
    """Convert a parsed locator dict → (by, selector) pair."""
    loc_type = locator_dict.get("type", "css")
    if loc_type == "role":
        sel: Dict[str, Any] = {"role": locator_dict.get("role", "")}
        if "name" in locator_dict:
            sel["name"] = locator_dict["name"]
        return "role", sel
    if loc_type == "text":        return "text",        locator_dict.get("value", "")
    if loc_type == "label":       return "label",       locator_dict.get("value", "")
    if loc_type == "placeholder": return "placeholder", locator_dict.get("value", "")
    if loc_type == "testId":      return "testId",      locator_dict.get("value", "")
    return "css", locator_dict.get("value", locator_dict.get("selector", ""))


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

class JSONLConverter:
    """
    Converts a Playwright JSONL recording to a structured flow JSON dict.

    Returns:
        {
          "flowName": str,
          "source": { "type": "playwright_jsonl" },
          "steps": [ { step, action, by, selector, value, rawValue,
                       paramKey, isSensitive, meta } ],
          "schema": { "credentials": {...}, "runParameters": {...} }
        }
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_file(
        self, jsonl_path: str | Path, flow_name: Optional[str] = None
    ) -> Dict[str, Any]:
        path = Path(jsonl_path)
        if not path.exists():
            raise FileNotFoundError(f"Recording not found: {path}")

        if flow_name is None:
            flow_name = path.stem

        raw_lines = path.read_text(encoding="utf-8").splitlines()
        steps: List[Dict[str, Any]] = []
        step_no = 1

        for line_no, line in enumerate(raw_lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSON on line %d: %s", line_no, exc)
                continue

            step = self._convert_action(raw, step_no)
            if step is not None:
                steps.append(step)
                step_no += 1

        steps = self._post_process_steps(steps)
        schema = _build_schema(steps)
        logger.info("Converted %d steps from %s", len(steps), path.name)
        return {
            "flowName": flow_name,
            "source": {"type": "playwright_jsonl"},
            "steps": steps,
            "schema": schema,
        }

    def _post_process_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        When the user presses Enter in a search/input field, Playwright records
        the resulting page navigation as a 'goto' instead of a keypress.
        This causes replays to always navigate to the hardcoded recorded URL,
        ignoring whatever the user typed at runtime.

        Fix: if a 'goto' immediately follows a 'fill' AND the goto URL contains
        the fill's rawValue (URL-encoded), replace the goto with press('Enter')
        on the same locator so the search uses the runtime value.
        """
        result: List[Dict[str, Any]] = []
        for step in steps:
            if (
                step["action"] == "goto"
                and result
                and result[-1]["action"] == "fill"
            ):
                prev = result[-1]
                raw_val = prev.get("rawValue") or ""
                url = step["selector"] or ""
                encoded_plus = urllib.parse.quote_plus(raw_val)   # iphone+17+pro
                encoded_pct  = urllib.parse.quote(raw_val)        # iphone%2017%20pro
                if raw_val and (encoded_plus in url or encoded_pct in url):
                    logger.info(
                        "Step %d: replacing hardcoded goto URL with press('Enter') "
                        "so runtime fill value is used for search.",
                        step["step"],
                    )
                    result.append(self._make_step(
                        step["step"], "press",
                        prev["by"], prev["selector"],
                        value="Enter",
                        raw_line=_synthetic_raw("press", prev["by"], prev["selector"], "Enter"),
                    ))
                    continue   # skip the original goto
            result.append(step)

        # Re-number steps sequentially after any replacements
        for idx, s in enumerate(result, 1):
            s["step"] = idx
        return result

    def save(self, output_path: str | Path, flow: Dict[str, Any]) -> None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(flow, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved flow to %s", out)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_step(
        self,
        step_no: int,
        action: str,
        by: str,
        selector: Any,
        value: Optional[str] = None,
        raw_value: Optional[str] = None,
        param_key: Optional[str] = None,
        is_sensitive: bool = False,
        raw_line: str = "",
    ) -> Dict[str, Any]:
        return {
            "step": step_no,
            "action": action,
            "by": by,
            "selector": selector,
            "value": value,
            "rawValue": raw_value,
            "paramKey": param_key,
            "isSensitive": is_sensitive,
            "meta": {"raw": raw_line or _synthetic_raw(action, by, selector, raw_value)},
        }

    def _convert_action(self, raw: Dict[str, Any], step_no: int) -> Optional[Dict[str, Any]]:
        name = raw.get("name", "")
        if name in ("openPage", "") or not name:
            return None

        handlers = {
            "navigate":       self._handle_navigate,
            "click":          self._handle_click,
            "fill":           self._handle_fill,
            "check":          self._handle_check,
            "uncheck":        self._handle_uncheck,
            "selectOption":   self._handle_select_option,
            "hover":          self._handle_hover,
            "press":          self._handle_press,
            "waitForTimeout": self._handle_wait_for_timeout,
            "closePage":      self._handle_close_page,
        }

        handler = handlers.get(name)
        if handler:
            return handler(raw, step_no)

        logger.warning("Unknown action '%s' — skipping.", name)
        return None

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _handle_navigate(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        url = raw.get("url", "")
        return self._make_step(step_no, "goto", "url", url,
                               raw_line=f"await page.goto('{url}');")

    def _handle_click(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        loc = parse_locator(raw.get("selector", ""), raw.get("locator"))
        by, selector = _locator_to_by_selector(loc)
        return self._make_step(step_no, "click", by, selector,
                               raw_line=_synthetic_raw("click", by, selector))

    def _handle_fill(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        loc = parse_locator(raw.get("selector", ""), raw.get("locator"))
        by, selector = _locator_to_by_selector(loc)
        raw_value = raw.get("text", "")
        label = _selector_label(by, selector)
        sensitive = _is_sensitive(label, raw_value)
        pk = _param_key(label, sensitive)
        return self._make_step(
            step_no, "fill", by, selector,
            value=_placeholder(label, sensitive),
            raw_value=raw_value,
            param_key=pk,
            is_sensitive=sensitive,
            raw_line=_synthetic_raw("fill", by, selector, raw_value),
        )

    def _handle_check(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        loc = parse_locator(raw.get("selector", ""), raw.get("locator"))
        by, selector = _locator_to_by_selector(loc)
        return self._make_step(step_no, "check", by, selector,
                               raw_line=_synthetic_raw("check", by, selector))

    def _handle_uncheck(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        loc = parse_locator(raw.get("selector", ""), raw.get("locator"))
        by, selector = _locator_to_by_selector(loc)
        return self._make_step(step_no, "uncheck", by, selector,
                               raw_line=_synthetic_raw("uncheck", by, selector))

    def _handle_select_option(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        loc = parse_locator(raw.get("selector", ""), raw.get("locator"))
        by, selector = _locator_to_by_selector(loc)
        values = raw.get("values", [])
        raw_value = values[0] if isinstance(values, list) and values else str(values)
        return self._make_step(step_no, "selectOption", by, selector,
                               raw_value=raw_value,
                               raw_line=_synthetic_raw("selectOption", by, selector, raw_value))

    def _handle_hover(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        loc = parse_locator(raw.get("selector", ""), raw.get("locator"))
        by, selector = _locator_to_by_selector(loc)
        return self._make_step(step_no, "hover", by, selector,
                               raw_line=_synthetic_raw("hover", by, selector))

    def _handle_press(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        loc = parse_locator(raw.get("selector", ""), raw.get("locator"))
        by, selector = _locator_to_by_selector(loc)
        key = raw.get("key", "")
        return self._make_step(step_no, "press", by, selector,
                               value=key,
                               raw_line=_synthetic_raw("press", by, selector, key))

    def _handle_wait_for_timeout(self, raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        timeout = raw.get("timeout", 1000)
        return self._make_step(step_no, "waitForTimeout", "timeout", None,
                               value=str(timeout),
                               raw_line=_synthetic_raw("waitForTimeout", "timeout", None, str(timeout)))

    def _handle_close_page(self, _raw: Dict[str, Any], step_no: int) -> Dict[str, Any]:
        return self._make_step(step_no, "closePage", "page", None,
                               raw_line="await page.close();")


# ---------------------------------------------------------------------------
# Schema builder (module-level — also used by server)
# ---------------------------------------------------------------------------

def _build_schema(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive credentials / runParameters schema from parameterised steps."""
    credentials: Dict[str, Any] = {}
    run_params: Dict[str, Any] = {}
    seen: set = set()

    for step in steps:
        pk = step.get("paramKey")
        if not pk or pk in seen:
            continue
        seen.add(pk)
        prefix, name = pk.split(".", 1)
        entry: Dict[str, Any] = {
            "type": "string",
            "required": True,
            "default": None,
            "label": name.replace("_", " ").title(),
        }
        if step.get("isSensitive"):
            entry["secret"] = True
            credentials[name] = entry
        else:
            run_params[name] = entry

    return {"credentials": credentials, "runParameters": run_params}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Convert a Playwright JSONL recording to simplified JSON."
    )
    parser.add_argument("input", help="Path to the .jsonl recording file")
    parser.add_argument("output", help="Path for the output .json file")
    args = parser.parse_args()

    converter = JSONLConverter()
    try:
        actions = converter.convert_file(args.input)
        converter.save(args.output, actions)
        print(f"Done — {len(actions)} actions written to {args.output}")
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

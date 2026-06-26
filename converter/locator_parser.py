"""
Locator Parser — normalizes Playwright internal selector strings and
locator objects into the framework's canonical locator schema.

Supports:
  - role    (internal:role=…)
  - css     (plain CSS / default selectors)
  - text    (internal:text=…)
  - label   (internal:label=…)
  - placeholder (internal:attr[placeholder=…])
  - testId  (internal:testid=…)
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_role_selector(selector: str) -> Dict[str, Any]:
    """
    Parses selectors of the form:
        internal:role=searchbox[name="Search Amazon.in"i]
    """
    match = re.match(
        r"internal:role=([^\[]+)(?:\[name=\"([^\"]+)\"(i)?\])?",
        selector,
    )
    if match:
        role = match.group(1).strip()
        name = match.group(2)
        exact = match.group(3) is None  # absence of 'i' flag means exact
        result: Dict[str, Any] = {"type": "role", "role": role}
        if name:
            result["name"] = name
            result["exact"] = exact
        return result
    return {"type": "role", "role": selector}


def _parse_text_selector(selector: str) -> Dict[str, Any]:
    """
    Parses selectors of the form:
        internal:text="Submit"i
        internal:text="Submit"
    """
    match = re.match(r'internal:text="([^"]+)"(i)?', selector)
    if match:
        return {
            "type": "text",
            "value": match.group(1),
            "exact": match.group(2) is None,
        }
    return {"type": "text", "value": selector}


def _parse_label_selector(selector: str) -> Dict[str, Any]:
    """
    Parses selectors of the form:
        internal:label="Email"i
    """
    match = re.match(r'internal:label="([^"]+)"(i)?', selector)
    if match:
        return {
            "type": "label",
            "value": match.group(1),
            "exact": match.group(2) is None,
        }
    return {"type": "label", "value": selector}


def _parse_placeholder_selector(selector: str) -> Dict[str, Any]:
    """
    Parses selectors of the form:
        internal:attr[placeholder="Enter email"i]
    """
    match = re.match(r'internal:attr\[placeholder="([^"]+)"(i)?\]', selector)
    if match:
        return {
            "type": "placeholder",
            "value": match.group(1),
            "exact": match.group(2) is None,
        }
    return {"type": "placeholder", "value": selector}


def _parse_testid_selector(selector: str) -> Dict[str, Any]:
    """
    Parses selectors of the form:
        internal:testid=[data-testid="submit-btn"s]
    """
    match = re.match(r'internal:testid=\[data-testid="([^"]+)"', selector)
    if match:
        return {"type": "testId", "value": match.group(1)}
    return {"type": "testId", "value": selector}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_locator(selector: str, locator_obj: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Normalize a Playwright selector string (and optional locator metadata)
    into the framework's canonical locator schema.

    Priority:
      1. If a ``locator`` object with a ``kind`` field is present, use it.
      2. Otherwise derive the locator type from the selector string prefix.
      3. Fall back to a raw CSS locator.

    Parameters
    ----------
    selector:
        The raw Playwright selector string (e.g. ``internal:role=button``).
    locator_obj:
        Optional ``locator`` dict from the JSONL action object.

    Returns
    -------
    dict
        Normalized locator dictionary compatible with the framework schema.
    """
    # -- Prefer structured locator metadata when available ------------------
    if locator_obj:
        kind = locator_obj.get("kind", "")
        body = locator_obj.get("body", "")
        options = locator_obj.get("options", {})

        if kind == "role":
            result: Dict[str, Any] = {"type": "role", "role": body}
            if options.get("name"):
                result["name"] = options["name"]
                result["exact"] = False  # always partial — recorded names may be truncated
            return result

        if kind == "text":
            return {
                "type": "text",
                "value": body,
                "exact": options.get("exact", False),
            }

        if kind == "label":
            return {
                "type": "label",
                "value": body,
                "exact": options.get("exact", False),
            }

        if kind == "placeholder":
            return {
                "type": "placeholder",
                "value": body,
                "exact": options.get("exact", False),
            }

        if kind == "testId":
            return {"type": "testId", "value": body}

        if kind == "default":
            # Fall through to selector-based parsing using the body as selector
            selector = body or selector

    # -- Derive from selector string prefix ---------------------------------
    if selector.startswith("internal:role="):
        return _parse_role_selector(selector)

    if selector.startswith("internal:text="):
        return _parse_text_selector(selector)

    if selector.startswith("internal:label="):
        return _parse_label_selector(selector)

    if selector.startswith("internal:attr[placeholder="):
        return _parse_placeholder_selector(selector)

    if selector.startswith("internal:testid="):
        return _parse_testid_selector(selector)

    # -- Default: raw CSS selector ------------------------------------------
    return {"type": "css", "value": selector}

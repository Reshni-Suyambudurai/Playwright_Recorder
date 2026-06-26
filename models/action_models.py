"""
Action models for the Playwright Recorder Framework.

Defines the canonical schema for all supported Playwright actions.
All locators and actions are normalized into these dataclasses before
being passed to the executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Locator models
# ---------------------------------------------------------------------------

@dataclass
class RoleLocator:
    """Locates an element by ARIA role."""
    type: str = "role"
    role: str = ""
    name: Optional[str] = None
    exact: bool = False


@dataclass
class CSSLocator:
    """Locates an element by CSS selector."""
    type: str = "css"
    value: str = ""


@dataclass
class TextLocator:
    """Locates an element by visible text."""
    type: str = "text"
    value: str = ""
    exact: bool = False


@dataclass
class LabelLocator:
    """Locates an element by its associated label text."""
    type: str = "label"
    value: str = ""
    exact: bool = False


@dataclass
class PlaceholderLocator:
    """Locates an element by placeholder attribute."""
    type: str = "placeholder"
    value: str = ""
    exact: bool = False


@dataclass
class TestIdLocator:
    """Locates an element by data-testid attribute."""
    type: str = "testId"
    value: str = ""


# Union type alias — used for type hints throughout the framework
LocatorModel = RoleLocator | CSSLocator | TextLocator | LabelLocator | PlaceholderLocator | TestIdLocator


# ---------------------------------------------------------------------------
# Action models
# ---------------------------------------------------------------------------

@dataclass
class BaseAction:
    """Common fields present on every action."""
    action: str = ""
    continue_on_error: bool = False
    description: Optional[str] = None


@dataclass
class GotoAction(BaseAction):
    action: str = "goto"
    url: str = ""


@dataclass
class ClickAction(BaseAction):
    action: str = "click"
    locator: Optional[Dict[str, Any]] = None
    button: str = "left"
    click_count: int = 1
    modifiers: List[str] = field(default_factory=list)


@dataclass
class FillAction(BaseAction):
    action: str = "fill"
    locator: Optional[Dict[str, Any]] = None
    value: str = ""


@dataclass
class CheckAction(BaseAction):
    action: str = "check"
    locator: Optional[Dict[str, Any]] = None


@dataclass
class UncheckAction(BaseAction):
    action: str = "uncheck"
    locator: Optional[Dict[str, Any]] = None


@dataclass
class SelectOptionAction(BaseAction):
    action: str = "selectOption"
    locator: Optional[Dict[str, Any]] = None
    values: List[str] = field(default_factory=list)


@dataclass
class HoverAction(BaseAction):
    action: str = "hover"
    locator: Optional[Dict[str, Any]] = None


@dataclass
class PressAction(BaseAction):
    action: str = "press"
    locator: Optional[Dict[str, Any]] = None
    key: str = ""


@dataclass
class WaitForTimeoutAction(BaseAction):
    action: str = "waitForTimeout"
    timeout: int = 1000


@dataclass
class ClosePageAction(BaseAction):
    action: str = "closePage"


# ---------------------------------------------------------------------------
# Execution result model
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """Records the outcome of a single action execution."""
    index: int
    action: str
    status: str          # "passed" | "failed" | "skipped"
    duration_ms: float = 0.0
    error: Optional[str] = None
    screenshot: Optional[str] = None


@dataclass
class ExecutionReport:
    """Aggregated report for a full test run."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: str = "0s"
    results: List[ActionResult] = field(default_factory=list)
    recording_file: str = ""

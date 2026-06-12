# Record and Convert JSONL Guide

This guide explains how to record with Playwright codegen and convert JSONL into a structured JSON file without modifying PlaywrightNotes.

## Files Added

- `record-and-convert.js` (project root): main CLI for recording and conversion.
- `JSON/test-structured.json`: structured output generated from `tests/test.jsonl`.

## What the CLI Does

1. Accepts a URL and optional file name.
2. Runs Playwright codegen in JSONL mode.
3. Saves JSONL under `tests/<fileName>.jsonl`.
4. Prompts to convert JSONL to structured JSON.
5. Redacts sensitive values in output.
6. Saves JSON under `JSON/<fileName>.json`.
7. Handles filename conflicts with a timestamp suffix.
8. Prompts to optionally delete the JSONL source file.

## Execution Steps

### Option A: Record and Convert (Interactive)

```bash
node record-and-convert.js "https://demo.playwright.dev/todomvc/#/" demo
```

What happens:

1. Recorder opens.
2. Perform UI actions.
3. Close recorder/browser.
4. Answer `Y/N` for JSON save.
5. Answer `Y/N` for JSONL deletion.

Output paths:

- JSONL: `tests/demo.jsonl`
- JSON: `JSON/demo.json` (or timestamped if already present)

### Option B: Convert Existing JSONL (Non-Recorder)

```bash
node record-and-convert.js --convert tests/test.jsonl test-structured "https://demo.playwright.dev/todomvc/#/"
```

Output:

- `JSON/test-structured.json`

### Option C: Use npm Scripts

```bash
npm run record:convert -- "https://demo.playwright.dev/todomvc/#/" demo
npm run jsonl:convert -- tests/test.jsonl test-structured "https://demo.playwright.dev/todomvc/#/"
```

## Structured JSON Shape

The JSON output contains:

- `meta`: source path, URL, generated time, browser/context details.
- `uiVersatility`: pages summary, frame summary, action counts, locator kind counts, iframe usage.
- `actions`: ordered action list with step number, page/frame info, selectors, keys, and redacted payload.

## Redaction Rules

The converter redacts sensitive fields such as:

- password
- otp
- secret
- token
- apiKey
- email
- username

Also, `fill` action `text` is redacted.

## Notes

- Keep recording in the project root so paths resolve correctly.
- Use `--help` to see command usage:

```bash
node record-and-convert.js --help
```

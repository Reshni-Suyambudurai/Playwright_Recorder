# Playwright Recorder — Converter — Executor

A full-stack automation tool that lets you **record** browser interactions with Playwright, **convert** the raw JSONL recording into a structured flow JSON, and **execute** it — with an Angular UI to trigger runs visually.

---

## Project Structure

```
Playwright_Recorder/
├── converter/        # JSONL → JSON conversion logic
├── executor/         # Playwright action executor & report generator
├── models/           # Pydantic/dataclass action models
├── recordings/       # Raw .jsonl recordings (output of codegen)
├── output/           # Converted .json flow files
├── reports/          # Execution report JSONs
├── screenshots/      # Failure screenshots
├── ui/               # Angular frontend (ng serve)
├── main.py           # CLI: convert / run / execute
├── server.py         # FastAPI backend (python server.py)
└── requirements.txt
```

---

## Prerequisites

- Python 3.9+
- Node.js 18+
- Playwright browsers installed

```bash
pip install -r requirements.txt
playwright install
```

```bash
cd ui
npm install
```

---

## Quick Start

### 1. Start the Backend

```bash
python server.py
```

Runs on **http://localhost:8000**

### 2. Start the Frontend

```bash
cd ui
ng serve
```

Runs on **http://localhost:4200**

---

## CLI Usage

### Record a session

```bash
npx playwright codegen --target=jsonl -o ./recordings/amazon.jsonl https://myhrms.kanini.com/kanini/zp#home/myspace/overview-actionlist
```

### Convert JSONL → JSON

```bash
python main.py convert recordings/zoho.jsonl
```

Output saved to `output/zoho.json`

### Execute a flow

```bash
python main.py execute output/zoho.json --browser chromium --slow-mo 2000
```

Options:
| Flag | Description |
|------|-------------|
| `--browser` | `chromium` / `firefox` / `webkit` |
| `--slow-mo` | Milliseconds between actions |
| `--headless` | Run without a visible browser window |
| `--params` | Path to a JSON file with runtime values |

### Convert + Execute in one step

```bash
python main.py run recordings/zoho.jsonl --browser chromium
```

---

## API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/flows` | List all converted flow JSON files |
| GET | `/api/flows/{name}` | Get a specific flow |
| POST | `/api/run` | Execute a flow with runtime values |

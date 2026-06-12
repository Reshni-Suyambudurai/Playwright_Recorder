const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { spawn } = require('child_process');

const PROJECT_ROOT = __dirname;
const TESTS_DIR = path.join(PROJECT_ROOT, 'tests');
const JSON_DIR = path.join(PROJECT_ROOT, 'JSON');

// Returns a compact timestamp string (e.g. 20260612-143022) used for naming files uniquely.
function timestamp() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

// Cleans a raw string (URL or user input) into a safe, lowercase filename-friendly slug.
function sanitizeName(raw) {
  return String(raw || '')
    .trim()
    .replace(/^https?:\/\//i, '')
    .replace(/[^a-zA-Z0-9-_]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase() || `recording-${timestamp()}`;
}

// Builds a readable filename from a URL by combining the hostname and pathname segments.
function deriveNameFromUrl(url) {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/\./g, '-');
    const pathname = parsed.pathname.replace(/\/+$/, '').replace(/\//g, '-');
    return sanitizeName(`${host}${pathname ? `-${pathname}` : ''}`);
  } catch (_) {
    return sanitizeName(url);
  }
}

// Prompts the user with a Y/N question in the terminal and resolves to true (yes) or false (no).
function askYesNo(rl, question) {
  return new Promise((resolve) => {
    rl.question(`${question} (Y/N): `, (answer) => {
      const normalized = String(answer || '').trim().toLowerCase();
      resolve(normalized === 'y' || normalized === 'yes');
    });
  });
}

// Creates a directory (and any missing parent directories) if it does not already exist.
function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

// Returns a JSON output path that will not overwrite an existing file — appends a timestamp if needed.
function createNonConflictingJsonPath(baseName) {
  const primaryPath = path.join(JSON_DIR, `${baseName}.json`);
  if (!fs.existsSync(primaryPath)) {
    return primaryPath;
  }
  return path.join(JSON_DIR, `${baseName}-${timestamp()}.json`);
}

// Parses a single JSONL line and throws a clear error message if the JSON is malformed.
function safeParseJsonLine(line, lineNumber) {
  try {
    return JSON.parse(line);
  } catch (error) {
    throw new Error(`Invalid JSON at line ${lineNumber}: ${error.message}`);
  }
}

// Returns true if a string contains any keyword that suggests the value is sensitive (password, token, etc.).
function containsSensitiveHint(value) {
  return /(password|otp|secret|token|apikey|api_key|authorization|auth|email|username|user_name)/i.test(String(value || ''));
}

// Converts a key name and a modifier bitmask into a human-readable string like "Shift+Enter" or "Control+A".
function formatKeyWithModifiers(key, modifiers) {
  if (!key) {
    return undefined;
  }

  const parts = [];
  const mod = Number(modifiers || 0);
  if (mod & 1) parts.push('Alt');
  if (mod & 2) parts.push('Control');
  if (mod & 4) parts.push('Meta');
  if (mod & 8) parts.push('Shift');
  parts.push(key);
  return parts.join('+');
}

const KNOWN_ROLES = [
  'textbox', 'button', 'checkbox', 'radio',
  'link', 'slider', 'listitem', 'combobox',
  'tabpanel', 'menuitem', 'switch', 'tab',
  'navigation', 'main', 'banner', 'heading',
  'dialog', 'alert', 'status', 'img', 'region',
];

// Converts a raw Playwright locator object (from JSONL) into a clean JSON shape used in the output.
// Handles role chaining (within), nth index, hasText, label, getByText, and CSS fallback.
function normalizeLocator(locator, selector) {
  if (!locator || typeof locator !== 'object') {
    return selector ? { css: selector } : undefined;
  }

  if (locator.kind === 'role') {
    if (locator.next && locator.next.kind === 'role') {
      const inner = normalizeLocator(locator.next, undefined);
      if (inner && typeof inner === 'object') {
        inner.within = compactObject({
          role: locator.body,
          ...(locator.options && locator.options.name ? { name: locator.options.name } : {}),
        });
        return inner;
      }
    }

    const out = { role: locator.body };
    if (locator.options && locator.options.name) {
      out.name = locator.options.name;
    }

    let node = locator.next;
    while (node) {
      if (node.kind === 'has-text' && node.body) {
        out.hasText = node.body;
      }
      if (node.kind === 'label' && node.body) {
        out.label = node.body;
      }
      if (node.kind === 'first') {
        out.nth = 0;
      }
      if (node.kind === 'nth' && node.body !== undefined) {
        out.nth = Number(node.body);
      }
      node = node.next;
    }

    if (!KNOWN_ROLES.includes(locator.body)) {
      console.warn(`[record-and-convert] Unknown role encountered: ${locator.body}`);
    }

    return out;
  }

  if (locator.kind === 'default') {
    const out = {};
    if (locator.body) {
      out.css = locator.body;
    }
    let node = locator.next;
    while (node) {
      if (node.kind === 'has-text' && node.body) {
        out.hasText = node.body;
      }
      node = node.next;
    }
    return out;
  }

  if (locator.kind === 'text') {
    return { getByText: locator.body };
  }

  if (locator.kind === 'label') {
    return { label: locator.body };
  }

  return selector ? { css: selector } : undefined;
}

// Recursively removes all null, undefined, empty string, empty array, and empty object fields from a value.
function compactObject(value) {
  if (Array.isArray(value)) {
    return value.map(compactObject).filter((item) => item !== undefined);
  }

  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, val] of Object.entries(value)) {
      const compacted = compactObject(val);
      if (compacted === undefined || compacted === null) {
        continue;
      }
      if (typeof compacted === 'string' && compacted.length === 0) {
        continue;
      }
      if (Array.isArray(compacted) && compacted.length === 0) {
        continue;
      }
      if (typeof compacted === 'object' && !Array.isArray(compacted) && Object.keys(compacted).length === 0) {
        continue;
      }
      out[key] = compacted;
    }
    return Object.keys(out).length > 0 ? out : undefined;
  }

  return value;
}

// Returns true if the event targets a generic textbox role — used to track typed text across any app.
function isTextInputEvent(event) {
  return Boolean(
    event &&
    event.locator &&
    event.locator.kind === 'role' &&
    event.locator.body === 'textbox'
  );
}

// Returns true if the fill event's locator hints (selector, name, label) suggest the field is sensitive.
// Falls back to keyword matching when Playwright's own sensitive flag is not set.
function shouldRedactFill(event) {
  const hints = [
    event.selector,
    event.locator && event.locator.body,
    event.locator && event.locator.options && event.locator.options.name,
    event.locator && event.locator.options && event.locator.options.label,
  ];
  return hints.some((hint) => containsSensitiveHint(hint));
}

// Creates a fresh per-page item-tracking state used to infer nearText for Delete button steps.
function createTodoState() {
  return {
    items: [],
    pendingText: null,
    lastReferencedText: null,
  };
}

// Finds the index of a tracked item by its text value, or -1 if not found.
function findTodoIndex(items, text) {
  return items.findIndex((item) => item.text === text);
}

// Infers which item a Delete button click is targeting, using the last referenced text as the best guess.
function chooseDeleteTarget(state) {
  const remaining = state.items.map((item) => item.text);
  if (remaining.length === 0) {
    return undefined;
  }

  if (state.lastReferencedText && remaining.includes(state.lastReferencedText)) {
    return state.lastReferencedText;
  }

  return remaining[0];
}

// Reads a JSONL file recorded by Playwright Codegen and converts it into a clean structured JSON file.
// Groups steps by page, resolves locators, redacts sensitive values, and tracks popups and item state.
function convertJsonlToStructuredJson(jsonlPath, jsonOutPath, sourceUrl) {
  const raw = fs.readFileSync(jsonlPath, 'utf8');
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length === 0) {
    throw new Error(`No records found in ${jsonlPath}`);
  }

  const events = lines.map((line, index) => safeParseJsonLine(line, index + 1));
  const firstEvent = events[0] || {};

  const firstNavigate = events.find((e) => e.name === 'navigate' && e.url);
  const resolvedSourceUrl = sourceUrl || (firstNavigate ? firstNavigate.url : undefined);

  const pageOrder = [];
  const pagesByAlias = {};
  const pageGuidToAlias = {};
  const popupOpenedBy = {};
  const todoStateByPage = {};

  const ensurePage = (alias) => {
    if (!pagesByAlias[alias]) {
      pagesByAlias[alias] = { alias, steps: [] };
      pageOrder.push(alias);
    }
    return pagesByAlias[alias];
  };

  const ensureTodoState = (alias) => {
    if (!todoStateByPage[alias]) {
      todoStateByPage[alias] = createTodoState();
    }
    return todoStateByPage[alias];
  };

  let stepCounter = 0;

  for (const event of events) {
    const actionName = event.name;
    const pageAlias = event.pageAlias || pageGuidToAlias[event.pageGuid] || 'page';

    if (event.pageGuid && event.pageAlias) {
      pageGuidToAlias[event.pageGuid] = event.pageAlias;
    }

    if (actionName === 'navigate' && event.url) {
      const page = ensurePage(pageAlias);
      page.url = event.url;
      continue;
    }

    if (!actionName || ['openPage', 'closePage'].includes(actionName)) {
      continue;
    }

    const page = ensurePage(pageAlias);
    const todoState = ensureTodoState(pageAlias);
    stepCounter += 1;

    const step = {
      step: stepCounter,
      action: actionName,
      locator: normalizeLocator(event.locator, event.selector),
    };

    if (Array.isArray(event.framePath) && event.framePath.length > 0) {
      step.frame = event.framePath.join(' > ');
    }

    if (actionName === 'fill' && typeof event.text === 'string') {
      step.text = shouldRedactFill(event) ? '[REDACTED]' : event.text;
      if (isTextInputEvent(event)) {
        todoState.pendingText = event.text;
        todoState.lastReferencedText = event.text;
      }
    }

    if (actionName === 'press' && event.key) {
      step.key = formatKeyWithModifiers(event.key, event.modifiers);
      if (event.key === 'Enter' && isTextInputEvent(event) && typeof todoState.pendingText === 'string') {
        todoState.items.push({ text: todoState.pendingText, completed: false });
        todoState.lastReferencedText = todoState.pendingText;
        todoState.pendingText = null;
      }
    }

    if (actionName === 'selectOption') {
      if (event.option !== undefined) {
        step.option = event.option;
      } else if (Array.isArray(event.options) && event.options.length > 0) {
        step.option = event.options.length === 1
          ? event.options[0]
          : { labels: event.options };
      }
    }

    if ((actionName === 'check' || actionName === 'uncheck') && step.locator && step.locator.hasText) {
      const todoIndex = findTodoIndex(todoState.items, step.locator.hasText);
      if (todoIndex >= 0) {
        todoState.items[todoIndex].completed = actionName === 'check';
        todoState.lastReferencedText = todoState.items[todoIndex].text;
      }
    }

    if (actionName === 'click' && step.locator && step.locator.role === 'button' && step.locator.name === 'Clear completed') {
      todoState.items = todoState.items.filter((item) => !item.completed);
    }

    if (actionName === 'assertText' && typeof event.text === 'string') {
      step.text = containsSensitiveHint(event.text) ? '[REDACTED]' : event.text;
      step.assertType = (event.matchSubstring === true || event.isRegex === true) ? 'contains' : 'exact';
      if (todoState.items.some((item) => item.text === event.text)) {
        todoState.lastReferencedText = event.text;
      }
    }

    if (actionName === 'assertChecked') {
      step.checked = event.checked !== false;
    }

    if (actionName === 'assertValue') {
      step.expectedValue = event.value !== undefined ? event.value : event.text;
    }

    if (actionName === 'assertVisible' && step.locator && step.locator.getByText) {
      todoState.lastReferencedText = step.locator.getByText;
    }

    if (actionName === 'assertSnapshot') {
      step.snapshotName = `snapshot-${pageAlias}-step-${stepCounter}`;
    }

    if (actionName === 'click' && step.locator && step.locator.role === 'button' && step.locator.name === 'Delete') {
      const inferredText = chooseDeleteTarget(todoState);
      if (inferredText) {
        step.locator.nearText = inferredText;
        todoState.items = todoState.items.filter((item) => item.text !== inferredText);
      }
    }

    if (Array.isArray(event.signals)) {
      for (const signal of event.signals) {
        if (signal && signal.name === 'popup' && signal.popupAlias) {
          step.popup = signal.popupAlias;
          popupOpenedBy[signal.popupAlias] = { page: pageAlias, step: stepCounter };
        }
      }
    }

    page.steps.push(compactObject(step));
  }

  for (const [alias, openedBy] of Object.entries(popupOpenedBy)) {
    const page = ensurePage(alias);
    page.openedBy = openedBy;
  }

  const structured = compactObject({
    meta: {
      sourceUrl: resolvedSourceUrl,
      generatedAt: new Date().toISOString(),
      browser: firstEvent.browserName,
      headless: firstEvent.launchOptions ? firstEvent.launchOptions.headless : undefined,
    },
    pages: pageOrder.map((alias) => compactObject(pagesByAlias[alias])),
  });

  ensureDir(path.dirname(jsonOutPath));
  fs.writeFileSync(jsonOutPath, `${JSON.stringify(structured, null, 2)}\n`, 'utf8');
  return structured;
}

// Launches "npx playwright codegen" as a child process and saves the recorded JSONL output to disk.
// Uses shell: true to avoid Windows EINVAL spawn errors with npx.
function runCodegen(url, jsonlPath) {
  return new Promise((resolve, reject) => {
    const quoteForShell = (value) => `"${String(value).replace(/"/g, '\\"')}"`;
    const command = [
      'npx playwright codegen',
      '--target=jsonl',
      '--output',
      quoteForShell(jsonlPath),
      quoteForShell(url),
    ].join(' ');

    const child = spawn(command, {
      stdio: 'inherit',
      cwd: PROJECT_ROOT,
      shell: true,
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Playwright codegen exited with code ${code}`));
      }
    });
  });
}

// Main flow for record mode: launches Codegen, waits for it to finish, then prompts to convert and optionally delete the JSONL.
async function recordAndConvert(url, baseName) {
  if (!url) {
    throw new Error('URL is required. Usage: node record-and-convert.js "<url>" [fileName]');
  }

  const finalBaseName = sanitizeName(baseName || deriveNameFromUrl(url));
  const jsonlPath = path.join(TESTS_DIR, `${finalBaseName}.jsonl`);

  ensureDir(TESTS_DIR);
  ensureDir(JSON_DIR);

  console.log(`Starting recorder for: ${url}`);
  console.log(`JSONL output: ${jsonlPath}`);

  await runCodegen(url, jsonlPath);

  if (!fs.existsSync(jsonlPath)) {
    throw new Error(`Recorder finished but JSONL file was not found at ${jsonlPath}`);
  }

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    const shouldSave = await askYesNo(rl, 'Do you want to convert and save JSON?');
    if (!shouldSave) {
      console.log(`Skipped conversion. JSONL kept at: ${jsonlPath}`);
      return;
    }

    const jsonOutPath = createNonConflictingJsonPath(finalBaseName);
    convertJsonlToStructuredJson(jsonlPath, jsonOutPath, url);
    console.log(`Structured JSON saved at: ${jsonOutPath}`);

    const shouldDelete = await askYesNo(rl, 'Do you want to delete the JSONL file?');
    if (shouldDelete) {
      fs.unlinkSync(jsonlPath);
      console.log(`Deleted JSONL: ${jsonlPath}`);
    } else {
      console.log(`Kept JSONL: ${jsonlPath}`);
    }
  } finally {
    rl.close();
  }
}

// Convert-only mode: reads an existing JSONL file and outputs the structured JSON without launching Codegen.
function convertExistingJsonl(inputPath, baseName, sourceUrl) {
  if (!inputPath) {
    throw new Error('Input JSONL path is required for convert mode.');
  }

  const resolvedInputPath = path.isAbsolute(inputPath)
    ? inputPath
    : path.join(PROJECT_ROOT, inputPath);

  if (!fs.existsSync(resolvedInputPath)) {
    throw new Error(`Input JSONL not found: ${resolvedInputPath}`);
  }

  ensureDir(JSON_DIR);
  const finalBaseName = sanitizeName(baseName || path.basename(resolvedInputPath, '.jsonl'));
  const jsonOutPath = createNonConflictingJsonPath(finalBaseName);

  convertJsonlToStructuredJson(resolvedInputPath, jsonOutPath, sourceUrl || null);
  console.log(`Structured JSON saved at: ${jsonOutPath}`);
}

// Entry point: parses CLI arguments and routes to either record+convert mode or convert-only mode.
async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help')) {
    console.log('Usage:');
    console.log('  node record-and-convert.js "<url>" [fileName]');
    console.log('  node record-and-convert.js --convert <jsonlPath> [fileName] [sourceUrl]');
    process.exit(0);
  }

  if (args[0] === '--convert') {
    const inputPath = args[1];
    const baseName = args[2];
    const sourceUrl = args[3];
    convertExistingJsonl(inputPath, baseName, sourceUrl);
    return;
  }

  const url = args[0];
  const baseName = args[1];
  await recordAndConvert(url, baseName);
}

main().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exit(1);
});

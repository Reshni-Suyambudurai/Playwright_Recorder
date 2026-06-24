# What you lose in the current JSON

For example, your Playwright recording contains:

```ts
await page.getByRole('textbox', {
  name: 'Email address or mobile number'
}).fill('Reshni.Suyambudurai@kanini.com');
```

But your JSON stores:

```json
{
  "action": "fill",
  "selector": "textbox[Email address or mobile number]"
}
```

Now the generator has to guess:

```ts
page.getByRole(...)
```

or

```ts
page.locator(...)
```

or

```ts
page.getByLabel(...)
```

The original selector strategy is lost.

# Better JSON format

If your goal is:

```text
Playwright TS
     ↓
JSON
     ↓
Playwright TS
```

with minimal loss, store the selector type explicitly:

```json
{
  "step": 1,
  "action": "fill",
  "selectorType": "getByRole",
  "role": "textbox",
  "name": "Email address or mobile number",
  "value": "Reshni.Suyambudurai@kanini.com"
}
```

Then generation is deterministic:

```ts
await page.getByRole(
  'textbox',
  { name: 'Email address or mobile number' }
).fill('Reshni.Suyambudurai@kanini.com');
```

Even better: Store the original Playwright locator

```json
{
  "step": 1,
  "action": "fill",
  "locator": {
    "type": "getByRole",
    "role": "textbox",
    "name": "Email address or mobile number"
  },
  "value": "Reshni.Suyambudurai@kanini.com"
}
```

or

```json
{
  "step": 2,
  "action": "fill",
  "locator": {
    "type": "css",
    "value": "#i0118"
  },
  "value": "demoo@123"
}
```

Then converting back to .ts is nearly 100% reliable.

# Biggest challenge

The hardest recorded steps are things like:

```ts
page.getByRole('row', {
  name: 'Daily scrum   '
}).locator('#daytxt2').fill('1');
```

Your JSON simplified that to:

```json
{
  "action": "fill",
  "selector": "row2.daytxt2",
  "value": "1"
}
```

This loses:

- row identification logic
- nested locator structure
- Playwright chaining

The regenerated script may not find the same element.

```json
{
  "step": 1,
  "page": "page",
  "frame": [],
  "action": "fill",
  "locator": {
    "type": "role",
    "role": "textbox",
    "name": "What needs to be done?"
  },
  "value": "Hi Resh"
}
```

| Conversion                | Reliability | Complexity |
| ------------------------- | ----------- | ---------- |
| JSONL → Custom JSON       | 98-100%     | Easy       |
| Custom JSON → TS          | 95-99%      | Easy       |
| TS → Custom JSON          | 75-90%      | Medium     |
| TS → JSONL-like structure | 60-80%      | Hard       |

```text
Playwright Codegen
        ↓
      JSONL
        ↓
 JSON Normalizer
        ↓
   Custom JSON
        ↓
  TS Generator
  Java Generator
  Python Generator
```
# AGENTS.md: Agent Entity Checklist

This repository is a list: everything an agent entity needs, in 16 categories, each with a pick. An agent entity is
anything built around an agent: an agent employee, an app, an open-source project or a company. `checklist.json` is
the one source. The block between the `checklist` markers in `README.md`, and all of `PRODUCTS.md`, are rendered
from it by `scripts/render.py`, and CI fails when they drift.

## Read the list

Read `checklist.json`. Its shape, with one of each:

```json
{
  "name": "The agent entity checklist",
  "version": "1.0",
  "read": "2026-09-27",
  "groups": [{"id": "self", "name": "The entity itself", "what": "..."}],
  "categories": [
    {
      "id": "harness", "name": "Harness", "group": "self", "priority": "P0",
      "question": "What is it made of?", "what": "...",
      "components": [
        {
          "id": "harness.memory", "name": "Memory", "what": "...",
          "elements": [
            {
              "id": "harness.memory.long-term", "name": "...", "what": "...",
              "open": "the leading open-source option", "closed": "the leading closed-source option",
              "pick": "the default when nobody chooses", "why": "the reason",
              "links": ["https://... public sources"], "tools": ["product-slug"], "alts": ["runner-up-slug"]
            }
          ]
        }
      ]
    }
  ],
  "tools": {
    "product-slug": {
      "name": "...", "url": "https://...", "read": "2026-09-27",
      "routes": {"remote_mcp": {"v": "yes", "detail": "...", "src": "https://..."}},
      "price": {"tier": "free", "text": "..."}, "adoption": {"tier": "leader", "text": "..."},
      "open": {"tier": "open", "text": "..."}
    }
  },
  "access": {"order": ["remote_mcp", "cli", "skill", "api", "local_mcp", "computer"], "props": ["docs", "setup"]},
  "score": {"weights": {"access": 30, "adoption": 25, "quality": 20, "cost": 15, "openness": 10}}
}
```

- `priority` runs from P0 (from day one, for every entity) to P4 (owning chips, buildings and power); `priorities`
  defines each.
- `tools` and `alts` on an element are slugs into `tools`: the products the pick names, then its runner-up.
- A route verdict `v` is `yes`, `partial`, `no`, `unknown` (not verified, scored as no) or `na` (does not apply).
  Every `yes` and `partial` carries an `https` source. `access.routes` says what each route means and why it ranks
  where it does; `score.rules` says how a product's score is computed.
- `identity`, `notes` and `examples` hold the checklist's explanations: identity in four parts, notes on how the
  categories were drawn, and agent entities on the market.

Examples (`jq` 1.6 or later):

```bash
jq -r '.categories[] | "\(.priority)  \(.name): \(.question)"' checklist.json
jq -r '.categories[] | select(.id == "trust") | .components[].elements[] | "\(.name): \(.pick)"' checklist.json
jq -r '.tools | to_entries[] | select(.value.routes.remote_mcp.v == "yes") | .value.name' checklist.json
```

## Change an entry

1. Edit `checklist.json` only. Never edit `PRODUCTS.md` or the block between the `checklist` markers in
   `README.md` by hand: they are rendered.
2. Render and check: `python3 scripts/render.py && python3 -m unittest discover -s tests -v` (Python 3.10 or later,
   standard library only).
3. Commit `checklist.json`, `README.md` and `PRODUCTS.md` together.

A product verdict belongs here only with a public source you opened yourself, and a product's `read` date is the
day its sources were read.

## Checks

| Command | What it proves |
| --- | --- |
| `python3 scripts/render.py --check` | The record is valid (ids, fields, groups, priorities, product slugs, verdicts, tiers, sources), and `README.md` and `PRODUCTS.md` match it. |
| `python3 -m unittest discover -s tests -v` | The same, plus: the checker catches each fault it promises to catch, the score rescales over the parts it knows, and no internal field or non-`https` link is left in the record (14 tests). |
| `python3 scripts/render.py --stale 90` | Lists the products whose evidence was read more than 90 days ago. |

CI (`.github/workflows/ci.yml`) runs the first two on every push and pull request. Every Monday,
`.github/workflows/stale.yml` runs the check again and lists aged evidence in its run summary. It only reads: a
person decides what changes.

## What not to do

- Do not hand-edit a rendered view, and do not commit `checklist.json` without the views rendered from it.
- Do not add a verdict without a public source, a source behind a sign-in, or a tracking, shortened or `http://`
  link.
- Do not say who uses a pick today. A pick is a default with a reason.
- Do not rename ids, categories or questions without a reason in the pull request: anchors and agents depend on
  them.
- Do not use em or en dashes in the record; the checker rejects them.

## Layout

| Path | What it is |
| --- | --- |
| `checklist.json` | The list, the one source |
| `README.md` | The list for people; the block between the `checklist` markers is rendered |
| `PRODUCTS.md` | Every product a pick names, with each route's verdict and its proof, rendered |
| `scripts/render.py` | Validates the record and renders both views |
| `tests/test_render.py` | Tests for the record, the views and the checker |
| `identity/` | `SOUL.md`, `BRAND.md` and `HEARTBEAT.md`: Atlas, the list's keeper |
| `.github/workflows/ci.yml` | Runs the tests and the check on every push and pull request |
| `.github/workflows/stale.yml` | Every Monday: the check, then the products whose evidence is older than 90 days |
| `llms.txt` | A map of this repository for agents that read first |

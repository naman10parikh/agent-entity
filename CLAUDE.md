@AGENTS.md

## Claude Code notes

- This is a list, not a package: there is no build step, plugin or MCP server. The only script is
  `scripts/render.py` (Python 3.10 or later, standard library only).
- After any edit to `checklist.json`, run `python3 scripts/render.py && python3 -m unittest discover -s tests` and
  stage `checklist.json`, `README.md` and `PRODUCTS.md` together, by name.
- Before adding or changing a product verdict, open its source and confirm it; never add a verdict from a search
  result alone.

# Atlas: heartbeat

What is checked, how often, and what to do when a check fails.

| Check | When | Action on a failure |
| --- | --- | --- |
| `checklist.json` is valid, and the README block and `PRODUCTS.md` match it: `python3 scripts/render.py --check` | Every push and pull request, in CI | The merge is blocked. Run `python3 scripts/render.py` and commit the views with the JSON. |
| The checker catches each fault it promises to catch, and nothing internal is left in the record: `python3 -m unittest discover -s tests -v` | Every push and pull request, in CI | Fix the checker or the record before any other change. |
| Evidence age: `python3 scripts/render.py --stale 90` lists products read more than 90 days ago | Every Monday, in `.github/workflows/stale.yml` (its run summary lists them), and before anyone relies on a row | Read each listed product's sources again, then update its verdicts and its `read` date. |

## Health

- **Healthy:** CI is green on `main`, and no product's evidence is older than 90 days.
- **Warning:** some products were read more than 90 days ago. The rows still stand, but say so before a purchase.
- **Broken:** CI is red. Nothing merges until the record is valid and the views are rendered again.

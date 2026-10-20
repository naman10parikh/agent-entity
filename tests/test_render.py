"""The record is valid, the views are current, the checker catches each fault, and nothing internal is left in it.

python3 -m unittest discover -s tests -v
"""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render  # noqa: E402

REC = json.loads((ROOT / "checklist.json").read_text())


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


class Record(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(render.problems(REC), [])

    def test_shape(self):
        cats = REC["categories"]
        self.assertEqual(len(cats), 16)
        self.assertEqual({c["group"] for c in cats}, {g["id"] for g in REC["groups"]})
        for c in cats:
            self.assertTrue(all(m["elements"] for m in c["components"]), c["id"])

    def test_views_current(self):
        readme = (ROOT / "README.md").read_text()
        body = readme.split(render.START, 1)[1].split(render.END, 1)[0]
        self.assertEqual(body, "\n" + render.readme_block(REC) + "\n", "README.md is stale: run python3 scripts/render.py")
        self.assertEqual((ROOT / "PRODUCTS.md").read_text(), render.products_page(REC), "PRODUCTS.md is stale")

    def test_no_internal_fields(self):
        for key in ("source", "states", "scopes", "stages", "changes", "unverified", "named", "added", "model"):
            self.assertNotIn(key, REC)
        for c in REC["categories"]:
            for m in c["components"]:
                self.assertNotIn("status", m, m["id"])
                for e in m["elements"]:
                    for key in ("status", "scope", "stage", "src"):
                        self.assertNotIn(key, e, e["id"])

    def test_public_links_only(self):
        for s in strings(REC):
            self.assertNotIn("audit/", s)
            for url in re.findall(r"\b\w+://\S+", s):
                if url.startswith(("http://127.0.0.1", "http://localhost")):
                    continue  # a tool's documented local default, not a link anyone follows
                self.assertTrue(url.startswith("https://"), url)


class Checker(unittest.TestCase):
    """Each fault the checker promises to catch, caught on a copy of the record."""

    def broken(self, change):
        rec = copy.deepcopy(REC)
        change(rec)
        return render.problems(rec)

    def first(self, rec):
        return rec["categories"][0]["components"][0]["elements"][0]

    def test_empty_pick(self):
        self.assertTrue(self.broken(lambda r: self.first(r).update(pick="")))

    def test_unknown_product(self):
        self.assertTrue(self.broken(lambda r: self.first(r).update(tools=["no-such-product"])))

    def test_dash(self):
        self.assertTrue(self.broken(lambda r: self.first(r).update(why="one \u2014 two")))

    def test_plain_http_link(self):
        self.assertTrue(self.broken(lambda r: self.first(r).update(links=["http://example.com"])))

    def test_repeated_id(self):
        self.assertTrue(self.broken(lambda r: r["categories"][1].update(id=r["categories"][0]["id"])))

    def test_tick_without_source(self):
        def change(r):
            route = next(iter(r["tools"].values()))["routes"]["api"]
            route.update(v="yes")
            route.pop("src", None)
        self.assertTrue(self.broken(change))

    def test_unknown_tier(self):
        self.assertTrue(self.broken(lambda r: next(iter(r["tools"].values()))["price"].update(tier="cheap")))


class Score(unittest.TestCase):
    def test_weights_rescale_over_known_parts(self):
        t = {"routes": {rid: {"v": "yes", "src": "https://example.com"} for rid in render.cols(REC)},
             "price": {"tier": "free"}, "adoption": {"tier": "leader"}, "open": {"tier": "open"}}
        self.assertEqual(render.score(REC, t), 100)  # quality unknown: left out, never guessed
        t["routes"]["remote_mcp"]["v"] = "no"
        sub = render.subscores(REC, t)
        self.assertEqual(sub["access"], round(100 * (100 - 30) / 100))
        self.assertIsNone(sub["quality"])

    def test_unscored_without_enough_evidence(self):
        t = {"routes": {rid: {"v": "unknown"} for rid in render.cols(REC)},
             "price": {"tier": "unknown"}, "adoption": {"tier": "unknown"}, "open": {"tier": "closed"}}
        self.assertIsNone(render.score(REC, t))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Render the checklist's views from checklist.json, the one source: the block in README.md and all of PRODUCTS.md.

  python3 scripts/render.py             validate checklist.json, then rewrite both views
  python3 scripts/render.py --check     exit 1 if the record is invalid or a view is stale (CI runs this)
  python3 scripts/render.py --stale 90  list products whose evidence was read more than 90 days ago

Standard library only. Edit checklist.json, never the generated text.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD, README, PRODUCTS = ROOT / "checklist.json", ROOT / "README.md", ROOT / "PRODUCTS.md"
START, END = "<!-- checklist:start -->", "<!-- checklist:end -->"
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)*$")
HTTPS = re.compile(r"^https://\S+$")
VERDICTS = {"yes", "partial", "no", "unknown", "na"}
MARK = {"yes": "✓", "partial": "◐", "no": "✗", "unknown": "?", "na": "n/a"}
TIERS = {"price": {"free": 100, "low": 80, "mid": 55, "high": 30, "sales": 15},
         "adoption": {"leader": 100, "strong": 75, "growing": 50, "niche": 25},
         "open": {"open": 100, "source-available": 50, "closed": 20}}
LABEL = {"price": {"free": "Free to start", "low": "Low", "mid": "Mid", "high": "High", "sales": "Sales-led"},
         "adoption": {"leader": "Leader", "strong": "Strong", "growing": "Growing", "niche": "Niche"},
         "open": {"open": "Open source", "source-available": "Source-available", "closed": "Closed"}}
QUALITY = ("tested", "probe", "bench")


def cols(rec):
    return list(rec["access"]["order"]) + list(rec["access"]["props"])


def elements(rec):
    return [(c, m, e) for c in rec["categories"] for m in c["components"] for e in m["elements"]]


def problems(rec):
    """Everything wrong with the record, as plain sentences. An empty list means it is valid."""
    out, seen = [], set()
    for key in ("name", "version", "read", "lead", "levels", "columns", "priorities", "groups", "access", "score",
                "categories", "tools"):
        if not rec.get(key):
            out.append(f"record: no {key}")
    if out:
        return out

    def walk(x, where):
        if isinstance(x, str):
            if "\u2014" in x or "\u2013" in x:
                out.append(f"{where}: an em or en dash")
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{where}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{where}[{i}]")

    walk(rec, "record")
    groups, tools = {g["id"] for g in rec["groups"]}, rec["tools"]

    def ident(value, parent=None):
        if not isinstance(value, str) or not ID.match(value) or value in seen:
            out.append(f"bad or repeated id {value!r}")
        elif parent and not value.startswith(parent + "."):
            out.append(f"id {value} is not under {parent}")
        seen.add(value)

    for c in rec["categories"]:
        ident(c.get("id"))
        if c.get("group") not in groups or c.get("priority") not in rec["priorities"]:
            out.append(f"{c.get('id')}: unknown group or priority")
        if not c.get("components"):
            out.append(f"{c.get('id')}: no components")
        for m in c.get("components") or []:
            ident(m.get("id"), c["id"])
            if not m.get("elements"):
                out.append(f"{m.get('id')}: no elements")
            for e in m.get("elements") or []:
                ident(e.get("id"), m["id"])
                for f in ("name", "what", "open", "closed", "pick", "why"):
                    if not str(e.get(f, "")).strip():
                        out.append(f"{e.get('id')}.{f}: empty")
                out += [f"{e['id']}: link {u!r} is not https" for u in e.get("links", []) if not HTTPS.match(u)]
                out += [f"{e['id']}: names {s!r}, not in tools" for s in e.get("tools", []) + e.get("alts", [])
                        if s not in tools]
        for f in ("name", "question", "what"):
            if not str(c.get(f, "")).strip():
                out.append(f"{c.get('id')}.{f}: empty")
    routes = rec["access"]["routes"]
    if set(cols(rec)) != set(routes) or set(rec["score"]["route_points"]) != set(routes):
        out.append("access and score.route_points must name every route once")
    if set(rec["score"]["weights"]) != {"access", "adoption", "quality", "cost", "openness"}:
        out.append("score.weights: need access, adoption, quality, cost and openness")
    for slug, t in tools.items():
        if not HTTPS.match(t.get("url", "")) or not re.match(r"^\d{4}-\d{2}-\d{2}$", t.get("read", "")):
            out.append(f"tools.{slug}: needs an https url and a read date")
        for rid in cols(rec):
            r = t.get("routes", {}).get(rid, {})
            if r.get("v") not in VERDICTS:
                out.append(f"tools.{slug}.{rid}: verdict must be one of {sorted(VERDICTS)}")
            elif r["v"] in ("yes", "partial") and not HTTPS.match(str(r.get("src", ""))):
                out.append(f"tools.{slug}.{rid}: a tick needs an https source")
        for key, allowed in TIERS.items():
            if (t.get(key) or {}).get("tier") not in set(allowed) | {"unknown"}:
                out.append(f"tools.{slug}.{key}: unknown tier")
    return out


def subscores(rec, t):
    """Each part of the score from 0 to 100, or None when there is no evidence (never guessed)."""
    points, got, total = rec["score"]["route_points"], 0, 0
    for rid in cols(rec):
        v = t["routes"][rid]["v"]
        if v != "na":
            total += points[rid]
            got += points[rid] * {"yes": 1.0, "partial": 0.5}.get(v, 0.0)
    q = [v for k, v in (t.get("quality") or {}).items() if k in QUALITY and isinstance(v, (int, float))]
    quality = None
    if q:
        quality = sum(q) / len(q)
        if all(v in (0, 100) for v in q):
            quality = min(quality, rec["score"]["quality_cap"])
    tier = lambda key: TIERS[key].get((t.get(key) or {}).get("tier"))  # noqa: E731
    return {"access": round(100 * got / total) if total else None, "adoption": tier("adoption"),
            "quality": round(quality) if quality is not None else None, "cost": tier("price"), "openness": tier("open")}


def score(rec, t):
    subs, w = subscores(rec, t), rec["score"]["weights"]
    known = {k: v for k, v in subs.items() if v is not None}
    if subs["access"] is None or len(known) < rec["score"]["min_known"]:
        return None
    return round(sum(w[k] * v for k, v in known.items()) / sum(w[k] for k in known))


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] +
                     ["| " + " | ".join(cell(x) for x in r) + " |" for r in rows])


def anchor(text):
    return re.sub(r"[^a-z0-9 -]", "", text.lower()).strip().replace(" ", "-")


def ordered(rec):
    return [c for g in rec["groups"] for c in rec["categories"] if c["group"] == g["id"]]


def plink(rec, slug):
    t = rec["tools"][slug]
    return f"[{t['name']}]({t['url']})"


def pick_cell(rec, e):
    out = f"**{e['pick']}**. {e['why']}"
    if e.get("tools"):
        out += " Product: " + ", ".join(plink(rec, s) for s in e["tools"]) + "."
    if e.get("alts"):
        out += " Runner-up: " + ", ".join(plink(rec, s) for s in e["alts"]) + "."
    if e.get("links"):
        out += " Sources: " + " ".join(f"[{i}]({u})" for i, u in enumerate(e["links"], 1))
    return out


def readme_block(rec):
    cats, n_comp = ordered(rec), sum(len(c["components"]) for c in rec["categories"])
    groups = {g["id"]: g for g in rec["groups"]}
    acc, sc = rec["access"], rec["score"]
    p = [f"_Generated from [checklist.json](checklist.json) (version {rec['version']}, evidence read {rec['read']}) by "
         f"`python3 scripts/render.py`: {len(cats)} categories, {n_comp} components, {len(elements(rec))} elements, "
         f"{len(rec['tools'])} products. Edit the JSON, never this block._", "", "## The map", "",
         f"The {len(cats)} categories in {len(groups)} layers. Each category is a question every entity must answer; "
         "its components are the things you choose; each row of the checklist is one decision inside them.", ""]
    p.append(table(["#", "Category", "Layer", "The question it answers", "Its components", "Priority"],
                   [[str(n), f"[{c['name']}](#{n}-{anchor(c['name'] + ' ' + c['question'])})",
                     groups[c["group"]]["name"], c["question"], ", ".join(m["name"] for m in c["components"]),
                     c["priority"]] for n, c in enumerate(cats, 1)]))
    p += ["", "## How to read a row", ""] + [f"- **{k.capitalize()}**: {v}" for k, v in rec["levels"].items()]
    p += ["", table(["Column", "Means"], [[k.capitalize() if k == "pick" else f"{k.capitalize()} source", v]
                                         for k, v in rec["columns"].items()])]
    p += ["", table(["Priority", "Means"], [[k, v] for k, v in rec["priorities"].items()]), "", "## The checklist"]
    for n, c in enumerate(cats, 1):
        p += ["", f"### {n}. {c['name']}: {c['question']}", "", f"{c['what']} Priority {c['priority']}.", ""]
        rows = []
        for m in c["components"]:
            for i, e in enumerate(m["elements"]):
                comp = f"**{m['name']}**{' (' + m['priority'] + ')' if m.get('priority') else ''}: {m['what']}" if i == 0 else ""
                rows.append([comp, f"**{e['name']}**: {e['what']}", e["open"], e["closed"], pick_cell(rec, e)])
        p.append(table(["Component", "Element", "Open source", "Closed source", "Pick, and why"], rows))
    ident = rec.get("identity")
    if ident:
        p += ["", "## Identity, in four parts", "", ident["lead"], "",
              table(["Part", "Its home in the checklist", "The question", "What it holds"],
                    [[k["name"], k["where"], k["question"], "; ".join(k["items"])] for k in ident["kinds"]]),
              "", ident["rule"], "", ident["footer"]]
    p += ["", "## How an agent uses a pick", "", acc["lead"], ""]
    p += [f"{i}. **{acc['routes'][r]['name']}**: {acc['routes'][r]['means']} {acc['routes'][r]['why']}"
          for i, r in enumerate(acc["order"], 1)]
    p += ["", "Two properties sit beside the routes:", ""]
    p += [f"- **{acc['routes'][r]['name']}**: {acc['routes'][r]['means']} {acc['routes'][r]['why']}" for r in acc["props"]]
    p += ["", "Every product a pick names, with each route's verdict and its proof, is in [PRODUCTS.md](PRODUCTS.md).",
          "", "## How a product is scored", "",
          table(["Part", "Weight"], [[k.capitalize(), f"{v}%"] for k, v in sc["weights"].items()]), "",
          table(["Route or property", "Points"], [[acc["routes"][r]["name"], str(v)] for r, v in sc["route_points"].items()]),
          ""] + [f"- {x}" for x in sc["rules"]]
    if rec.get("examples"):
        p += ["", "## Entities in the wild", "", "Agent entities on the market, the doors people reach them by, and what "
              "other agents can call.", "",
              table(["Entity", "Maker", "Reached by", "What other agents can call", "Source"],
                    [[x["name"], x["maker"], x["reached_by"], x["exposes"], f"[link]({x['src']})"] for x in rec["examples"]])]
    if rec.get("notes"):
        p += ["", "## Notes", ""] + [f"- {x}" for x in rec["notes"]]
    return "\n".join(p)


def outranked(rec):
    out = []
    for _, _, e in elements(rec):
        slugs = (e.get("tools") or [])[:1] + (e.get("alts") or [])
        if len(slugs) >= 2:
            a = {s: subscores(rec, rec["tools"][s])["access"] or 0 for s in slugs}
            best = max(slugs[1:], key=lambda s: a[s])
            if a[best] > a[slugs[0]]:
                out.append([e["name"], f"{plink(rec, slugs[0])} ({a[slugs[0]]})", f"{plink(rec, best)} ({a[best]})", e["why"]])
    return out


def mark(r):
    m = MARK[r["v"]]
    return f"[{m}]({r['src']})" if r["v"] in ("yes", "partial") else m


def products_page(rec):
    acc = rec["access"]
    tier = lambda t, key: LABEL[key].get((t.get(key) or {}).get("tier"), "Not known")  # noqa: E731
    rows = []
    for slug, t in sorted(rec["tools"].items(), key=lambda kv: kv[1]["name"].lower()):
        s = score(rec, t)
        rows.append([plink(rec, slug)] + [mark(t["routes"][r]) for r in cols(rec)] +
                    [tier(t, "price"), tier(t, "adoption"), tier(t, "open"), "unscored" if s is None else str(s), t["read"]])
    head = ["Product"] + [acc["routes"][r]["name"] for r in cols(rec)] + ["Price", "Adoption", "Openness", "Score", "Read"]
    p = ["# Every product, with its proof", "",
         f"_Generated from [checklist.json](checklist.json) by `python3 scripts/render.py`: {len(rec['tools'])} products. "
         "Edit the JSON, never this file._", "", acc["lead"], "",
         "Marks: ✓ yes and ◐ partial link to the proof · ✗ no · ? not verified (scored as no) · n/a does not apply. "
         "The score and its weights are explained in the [checklist](README.md#how-a-product-is-scored). No product here "
         "has a quality check with a public source yet, so quality is left out of every score and the weights are "
         "rescaled over the rest.", "", table(head, rows)]
    fewer = outranked(rec)
    if fewer:
        p += ["", "## Where the pick has fewer ticks", "",
              "The score compares products; it does not choose. Where a runner-up reaches more routes than the pick, "
              "the pick's reason is shown beside it.", "",
              table(["Element", "Pick (access)", "Runner-up (access)", "Why the pick stands"], fewer)]
    return "\n".join(p + ["", "Back to the [checklist](README.md)."]) + "\n"


def splice(doc, body):
    if doc.count(START) != 1 or doc.count(END) != 1:
        raise SystemExit("README.md needs exactly one checklist:start and one checklist:end marker")
    head, rest = doc.split(START)
    return f"{head}{START}\n{body}\n{END}{rest.split(END, 1)[1]}"


def main(argv):
    if {"-h", "--help"} & set(argv):
        print(__doc__)
        return 0
    rec = json.loads(RECORD.read_text())
    bad = problems(rec)
    if bad:
        print(f"checklist.json has {len(bad)} problem(s):", *[f"  - {x}" for x in bad[:60]], sep="\n")
        return 1
    if "--stale" in argv:
        days = int(argv[argv.index("--stale") + 1])
        old = [(s, t["read"]) for s, t in rec["tools"].items() if (date.today() - date.fromisoformat(t["read"])).days > days]
        print(f"{len(old)} of {len(rec['tools'])} products were read more than {days} days ago", *[f"  {s} {r}" for s, r in old], sep="\n")
        return 0
    views = {README: splice(README.read_text(), readme_block(rec)), PRODUCTS: products_page(rec)}
    stale = [p.name for p, body in views.items() if not p.exists() or p.read_text() != body]
    print(f"checklist.json valid: {len(rec['categories'])} categories, {len(elements(rec))} elements, {len(rec['tools'])} products")
    if "--check" in argv:
        print("stale: " + ", ".join(stale) + " (run python3 scripts/render.py)" if stale else "README.md and PRODUCTS.md are current")
        return 1 if stale else 0
    for p, body in views.items():
        p.write_text(body)
    print("rewrote " + ", ".join(stale) if stale else "already current")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

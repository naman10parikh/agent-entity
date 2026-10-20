# Contributing

Thank you for helping. Pull requests written with an AI agent are welcome, and the same bar applies to every change.

1. For a new category or component, open an issue first, so we agree on where it belongs. Categories are the
   questions every entity must answer, and they change rarely.
2. Read [AGENTS.md](AGENTS.md). It is the one set of instructions for people and coding agents.
3. Edit `checklist.json` only, then run `python3 scripts/render.py && python3 -m unittest discover -s tests -v` and
   commit the rendered `README.md` and `PRODUCTS.md` with it.
4. Every product verdict needs a public source you opened yourself; set the product's `read` date to that day.
5. Keep each change small, and say in the pull request what you verified and how.

A person reviews every change before it is merged.

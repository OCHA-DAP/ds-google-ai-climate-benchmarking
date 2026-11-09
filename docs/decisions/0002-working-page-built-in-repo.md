---
status: accepted
date: 2026-11-09
---

# 0002. The working page is built by repo scripts as inline SVG and published as an artifact

## Context and problem statement

The benchmark's results are read by the team and by Google.org stakeholders on a single
working page: the step-1 coverage check, the proxy check, the per-framework rescores, the
year ledger and the paired answer. Until 9 November 2026 the page builder and its figure
code lived in a Claude session scratchpad; the scratchpad lost its step-1 data file and
helper scripts between sessions, and the page could only be rebuilt from the session
transcript. Where should the page be built, with what, and how is it published?

## Considered options

- Keep the builder in the session scratchpad and commit only the rendered HTML
- A Quarto or marimo book deployed with the team's GitHub Pages convention
- Figures as matplotlib or plotly images embedded in a page
- Repo scripts (`scripts/page/`) rendering inline SVG from the `outputs/` CSVs and JSON,
  published as a Claude artifact

## Decision

Chosen option: repo scripts rendering inline SVG, published as a Claude artifact.

`uv run scripts/page/build.py` aggregates the step-1 outputs, adds the incumbent legs to
the rescore summary, draws every figure from the `outputs/` files and writes
`outputs/page/index.html`; the artifact is published from that file. Every number on the
page is read from a results file, never typed into the template.

Inline SVG was kept because the page's figures are ledgers and dot-and-interval charts
whose cells carry text; they stay crisp, theme-aware and searchable, and need no plotting
dependency or image pipeline. A Quarto book would add a build chain and a second site to
maintain for what is still a working page, not a product; it remains the right move if
the page becomes a published deliverable. Committing rendered HTML without the builder is
what failed.

### Consequences

- Good: the page is reproducible from a clone plus the `outputs/` files; a rerun of any
  script and one build command refreshes every figure and sentence that depends on it.
- Good: no new dependencies; the lint baseline applies, with two rules relaxed for the
  builder (`RUF001` for typographic characters in page text, `SIM115` for one-shot reads).
- Bad: the figure code is hand-written SVG, about 800 lines, which is slower to change
  than a plotting library call.
- Bad: `outputs/` is not in git, so a fresh clone must rerun the data pulls before the
  page builds; the artifact is the shared copy.
- Bad: publishing is a Claude artifact step, not CI; moving to GitHub Pages would make it
  one (see the `pages-site` convention).

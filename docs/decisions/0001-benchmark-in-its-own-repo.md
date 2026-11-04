---
status: accepted
date: 2026-11-04
---

# 0001. The benchmark lives in its own repo

## Context and problem statement

Deliverable 1 of the Google.org grant compares Google's flood model with the models used
in the CERF AA frameworks, portfolio-wide. The team has already done this three times
(Nepal, Nigeria, Somalia), each inside the framework's own repo with its own method, and
the results cannot be stacked. The stock-take was drafted inside the knowledge base. Where
should the benchmark code, data pulls and write-ups live?

## Considered options

- In the knowledge base (`ds-knowledge-base`)
- Inside each framework repo (`ds-aa-nga-flooding`, `ds-aa-som-floods`, ...)
- A separate spoke repo (`ds-google-ai-climate-benchmarking`)

## Decision

Chosen option: a separate spoke repo, decided at the team meeting of 4 November 2026.

The knowledge base is the hub for summaries and cross-links; it holds no analysis code or
data pulls, by its own rules. Framework repos are the right place for a framework's
trigger, not for a comparison that has to apply one protocol across all of them. A
separate repo can hold the shared protocol and import station definitions from the
framework repos, and is what directions B and C of the stock-take imply.

### Consequences

- Good: one place for the scoring code and the protocol rules; comparable numbers across
  frameworks; one place to re-run when a model version changes.
- Good: the knowledge base keeps a summary page and a pointer, as for every other spoke.
- Bad: a second codebase next to the framework repos; station definitions must be kept in
  sync with them, by import rather than by copy.
- Bad: a per-framework trigger change (Deliverable 2) still has to be made in the
  framework's repo, so results flow back across a repo boundary.

## Pros and cons of the options

### In the knowledge base

- Good, because the stock-take and the framework pages are already there.
- Bad, because the KB is documentation; the KB's own `CLAUDE.md` puts code-adjacent depth
  in spokes, and the KB's CI, generators and public visibility are built for prose.

### Inside each framework repo

- Good, because each repo already holds the station, threshold and event definitions.
- Bad, because it reproduces the problem the deliverable exists to fix: three methods,
  three answers, nothing comparable.

### A separate spoke repo

- Good, because the protocol is the thing that can be standard, and one repo can hold it.
- Bad, because of the sync cost with the framework repos, accepted above.

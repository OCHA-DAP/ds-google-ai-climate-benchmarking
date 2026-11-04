# ds-google-ai-climate-benchmarking

Benchmark of Google's AI flood forecasts against the models in the OCHA/CERF AA frameworks
(Google.org grant, Deliverable 1). Read `README.md` first; `docs/grrr-2026-11.md` for the
Google data; `docs/stock-take-2026-11-03.md` for the team's working note.

- **The frameworks live in the knowledge base**, not here. For what a framework triggers
  on, which station, which threshold, which gauge record: read
  `ds-knowledge-base/frameworks/<iso>-flooding/` (the `kb-access` plugin is enabled in
  this repo). Do not restate framework facts here; link to the KB page.
- **Record significant decisions as ADRs** in `docs/decisions/` (MADR, copy
  `template.md`, next zero-padded number). The protocol choices (event matching window,
  return-period method, ensemble rule, impact record) are exactly the kind of decision
  that belongs there.
- **Fail loudly.** A basin with no data, a store that will not open, a country with no
  boundary match: raise or report it as a distinct state. Never fill with a default and
  carry on.
- **Model versions next to every number.** Google's release is
  `distributed_model_2026_11`; the older bucket is `model_id_8583a5c2_v0`; the live API
  may be a third. GloFAS v4 vs v5 likewise.
- **Vocabulary:** reanalysis = historical simulation = retrospective (the model run on
  reconstructed past weather); reforecast = the forecast replayed for past issue dates;
  live forecast = what a trigger fires on. Thresholds come from the reanalysis; triggers
  see the forecast. Keep the distinction in every table and chart.
- Python: `uv` + `ruff` per `ds-knowledge-base/infrastructure/python-tooling.md`.
  `uv run ruff format . && uv run ruff check .` before committing.

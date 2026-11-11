---
status: proposed
date: 2026-11-10
---

# 0003. Mirror the GloFAS v4 reanalysis to the team blob as one sharded (cell, time) Zarr

## Context and problem statement

Every flood framework but Nigeria's runs on GloFAS, and the benchmark, the spokes and any
global test need its reanalysis at arbitrary points over the whole record. The only source is
the Copernicus Early Warning Data Store (EWDS), which serves one request at a time per account,
caps a request at about one year of days, and queues for hours; the spokes' copies stop in
2022 to 2024 and are re-fetched point by point. Probes on 10 November 2026: a 0.3 degree box
for 10 years is refused ("cost limits exceeded"), a whole-country box for one year takes
9 minutes of server time, and the whole globe for one year is accepted, takes 11.5 minutes and
is a 2.4 GB netCDF. So 47 requests cover 1979 to 2025 once. Where and in what layout should
that copy live, and how is it extended each year?

## Considered options

- Keep fetching point boxes from EWDS per spoke (the status quo)
- Mirror the raw yearly netCDFs only
- Zarr with chunks spanning all time (one fetch per point history)
- Zarr with one array per year in a group
- Zarr with one (cell, time) array, five-year time chunks, zarr v3 sharding
- Parquet, long or wide

## Decision

One zarr v3 group on the `global` container, `glofas/v4/reanalysis/q.zarr`, with `q` as a
(cell, time) float32 array over every land cell of the 0.05 degree grid (6,221,926 cells, the
cells where the upstream-area map is finite), time 1979-01-02 to 2026-01-01 as EWDS stamps it,
sharded 4,096 cells by 1,826 days with inner chunks of 64 cells by 1,826 days, zstd. The raw
yearly netCDFs are kept beside it as bronze, the ECMWF auxiliary files as static, and
`cells.parquet` indexes cell to row, column, latitude, longitude, upstream area and downstream
cell. Pathed by version so a v5 mirror is a sibling.

- All land cells, not a river subset: ECMWF states no minimum catchment for the product, the
  difference is about a dollar a month at Cool tier, and a cut would bake our judgment into the
  archive. Upstream area sits beside every cell so the filter is applied at read time.
- Five-year time chunks rather than all-time: all-time chunks cannot be written year by year
  without rewriting the whole store on every append. Five-year chunks make a point history ten
  fetches of about 150 KB and a yearly append a rewrite of one shard column (about 15 GB of
  in-region traffic), never the store.
- One array rather than per-year arrays: per-year arrays append cleanly and load in parallel,
  but every reader has to concatenate 47 arrays, and without sharding a year is a million
  blobs. Sharding gives the same object count either way, so the single array wins on the
  reader's side.
- Zarr rather than parquet for the daily archive: measured on the year 2000, parquet needs
  either a 17,000-column wide table or a 5-billion-row long one, and the point-history query
  reads 2 MB to 270 MB per year against 20 KB from the (cell, time) Zarr. Parquet is the right
  home for what is derived from the archive (annual maxima, return-period levels, events).
- Time stays as EWDS stamps it (end of the 24 h window) with the convention in the attributes,
  because three spokes shift it and one does not; a mirror that chose one would silently
  disagree with the other.
- Loading runs in Azure on the single-node job policy. From a laptop the uploads crawl
  (0.8 MB/s measured) and the per-account EWDS queue is the same either way.
- One pass per year (`run`): request, stream to bronze, load, mark, each step skipped when its
  ledger says it is done (EWDS request id and attempt count per year, the bronze file, a marker
  blob per loaded year). A stopped or frozen run is started again with the same years; a year
  interrupted mid-load has no marker and is rewritten in place. The raw yearly file is kept
  because it is what makes a store rebuild possible without EWDS, which the first evening needed.
- The product's last year is accepted short, but only when asked. The consolidated product ends
  at the 31 December 2024 stamp, so the 2024 file is one day shorter than every other year's and
  the loader's calendar check refused it (11 November 2026). `--allow-short-last-year` accepts a
  file that stops early, writes the days present and records `complete: false` in the year's
  marker; a year marked incomplete is the one to re-request when the product extends. The
  default stays strict so a truncated file for any other year is still an error.
- Shard index at the start of each shard (`index_location="start"`). Azure Blob serves no
  suffix byte ranges and adlfs passes them through, so with zarr's default (index at the end)
  every partial shard read from blob fails with "Required Content-Range response header is
  missing". Verified 10 November 2026 on two small arrays, same code and credentials: index at
  the end fails, index at the start reads. Unsharded Zarr (the team's IMERG and CMA stores) is
  not affected. This is a rule for any sharded Zarr v3 on the team's blob.

### Consequences

- Good: any point's full history is a sub-second read; the spokes can stop re-fetching; the
  global test and every future framework design read one store. About 107 GB, under $1.50 a
  month including bronze in the Archive tier.
- Good: every invariant is enforced while loading (NaN mask equals the land mask on every day,
  file coordinates equal the index, consecutive days inside the axis) and recorded per year in
  the array attributes, so a bad year cannot be half-written.
- Bad: a yearly append rewrites one shard column; concurrent loads of years in the same column
  must not run (the loader processes years sequentially).
- Seen in the backfill (10 to 11 November 2026, 44 years in four runs, about 12 cluster hours):
  the loader must read the yearly file from the node's disk, not from memory, and make one copy
  per band, or it sits at 7.7 GB resident beside the Spark driver on the 14 GB node and the
  driver is killed; EWDS drops a 2.4 GB download now and then, so the stream is retried from
  scratch and a zero-byte bronze blob (what an aborted staged upload leaves) does not count as
  present; the per-year memory and time are in each year's marker.
- Bad: the EWDS requests share the team key's queue with the daily Nigeria and Somalia runs; the
  backfill should run off-season or on a second key.
- Bad: the code lives in the benchmark repo for now (public repo creation is blocked for the
  agent); it should move to its own pipeline repo when it becomes a scheduled job, and get a KB
  pipeline page.

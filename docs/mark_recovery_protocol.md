# Missing Mark Source Recovery Protocol

Registered: 2026-11-17. Data recovery only; no signals, returns, fitting or trading.
Existing source/canonical data and prior failed gates remain unchanged.

## Frozen target and expectations

Target the 33,240 exact interior mark symbol-hours enumerated in the completed
audit (1,167 ranges, longest 96 hours). Revalidate the 534 staged source candidates
before reuse; do not treat their presence as evidence of historical tradability.
Expect most requests to be recoverable given the bounded controls, but do not
assume universal recovery. Trade gaps, funding gaps and boundary-only omissions
are outside this segment.

## Recovery rules

- Freeze source-audit/candidate digests and per-range monthly-source SHA-256,
  two observed boundary rows, symbol, requested interval and exact target keys.
- A request includes the original contiguous gap plus both boundary hours, at
  most 98 rows. Use the official public markPriceKlines endpoint, at most two
  workers and a global minimum 0.25-second request spacing. No automatic retry
  loop; persist errors and permit explicit resume. Maximum 1,167 API requests
  per invocation, reduced by fully verified seed/cached ranges.
- Require positive finite ordered OHLC, exact timestamps/hourly closes, complete
  requested row set and exact decimal agreement at both original boundaries.
  Check all seed overlaps. Quarantine conflicting keys; never average sources,
  interpolate, substitute traded prices or fill absent responses with zero.
- Save HTTP payloads/provenance separately, hash-check cached evidence on resume,
  and prohibit concurrent writers. Successful checkpoints can be reused.
- Keep current product labels, last-positive-trade diagnostics and known lifecycle
  events as explicit audit context. Do not infer causal eligibility or restart a
  delisted contract because marks can be recovered.

## Validation and deliverables

First run a two-range validation including at least one range without a complete
seed; then re-run those ranges and require no new requests and identical accepted
keys/prices. Unit-test shifted/partial responses, source conflicts, cache tampering
and contextual lifecycle flags before full execution.

Produce a resumable plan, response manifests, exact-key-only JSONL recovery
overlay and remaining/conflict lists. Complete recovery requires 33,240 unique
target keys with zero unresolved keys and zero source conflicts. Partial recovery
must report its limits with a nonzero exit. Candidate/source retrieval can succeed
while historical eligibility remains false.

Export only a NEW versioned overlay Parquet plus schema/provenance manifest after
validation; do not overwrite or silently merge old canonical datasets. Preserve
raw decimal strings alongside numeric price fields. No existing data are deleted.
Record tests, measured outcome, reproducible commands and next task in the report
and project handoff. Long execution may be handed to the user after small validation.

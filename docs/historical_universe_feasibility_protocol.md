# Historical USD-M Universe Feasibility Protocol

Registered: 2026-11-17. Data-only study; no strategy signals, returns, rankings,
parameter selection, or performance inspection. This is separate from strategy
Experiment 001, which remains unregistered.

## Scope and expectation

Assess whether Binance public archives can support a broader, survivorship-aware
USDT perpetual universe for a later momentum study. Expect archive roots to retain
some discontinued symbols, while current exchange metadata alone cannot establish
historical contract status, rules, or exact listing/delisting times.

Window: 2021-01 through 2026-10 inclusive. Census the complete monthly root listings
for USD-M trade klines, mark klines, funding, and spot klines. Retain raw responses,
pagination evidence, source URLs, retrieval times, byte sizes, and SHA-256 hashes.
Archive directory presence is not proof of perpetual type or historical eligibility.

## Bounded pilot

Inspect BTCUSDT and ETHUSDT controls plus LUNAUSDT, LUNCUSDT, FTTUSDT, and
WAVESUSDT as lifecycle/name-change/data-availability probes. These are not an
investable candidate list and do not presume discontinued status. For each symbol,
inspect monthly file metadata for trade 1h, mark 1h, funding, and spot 1h. Report
missing months inside observed endpoints and overlap; do not require survival to
the end of the window. Do not merge renamed symbols automatically.

Only small public metadata responses are acquired at this stage. Do not download
market ZIP datasets or start a full backfill. Any errors stay explicit.

## Decision rules fixed before execution

1. Discovery passes only if all four archive roots finish pagination without
   errors, cycles, or missing continuation tokens.
2. Controls pass metadata feasibility only if both have trade, mark, and funding
   archives with checksums in the study window.
3. Lifecycle recovery is provisionally supported if at least two pilot symbols
   have trade, mark, and funding overlap and their trade monthly archive ends
   before 2026-10. Label these archive-ended, not proven delisted.
4. These passes permit a metadata-only all-symbol coverage census and bounded
   row-quality pilot. They do NOT establish a complete historical universe,
   historical tradability, row integrity, strategy feasibility, or live readiness.
5. Full-universe acquisition remains conditional on contract-type classification,
   explicit treatment of incomplete histories and terminal events, row-level
   validation, and a quantified download plan. Exact lifecycle facts require
   separate official evidence; archive endpoint inference remains labeled.

## Deliverables

Reusable bounded discovery script, small synthetic parsing tests, ignored raw
metadata/JSON summary, a committed feasibility report and project status handoff.
Record unresolved sources, requested network bytes, existing infrastructure reuse,
and next acquisition steps. No secrets or datasets enter Git.

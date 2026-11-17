# Lifecycle and tradability evidence review

As of 2026-11-17. This is a PARTIAL evidence review, not a validated historical
trading universe. All 924 archived identifiers are covered by a ledger; zero have
complete lifetime/specification/cashflow verification. No selection rule is chosen.

Curated inputs: `config/lifecycle_facts.json`. Rebuild/read saved official sources:
`python3 scripts/run_research_data.py review`. Output is ignored under
`data/interim/usdm_universe/lifecycle_review_20261117/`:
`sources/*.raw` (official CMS response), source metadata/hash, extracted text,
`events.json`, `identity_ledger.json`, `summary.json`. Cache response hashes and
curated evidence terms are checked. Text-term checks support reproducibility;
they do not replace human interpretation of futures scope/time/underlying.

21 official sources support 47 events for 25 identifiers. Priority union = 61
identifiers (seven remaining-mark cases, 54 funding-after-activity cases, four
funding-month cases with overlaps); 23 have some official event evidence, 38 have
none in this pass. Even those 23 remain only partially verified. The ledger records
all priorities and unknowns; never substitute current exchangeInfo delivery/onboard
fields or last observed volume for authoritative historical episode boundaries.

All captured pages are CURRENT versions. CMS release metadata and retrieval hashes
do not prove the same content was visible at a historical decision time. Every event
has `causal_available_at=null` and `fact_interpretation=ex_post_only`. Announcement
updates, actual publication/receipt latency and historical versions remain unresolved.

## Identifier reuse

- LIT: legacy Litentry contract settled 2025-01-31 09:00 UTC; later launch on
  2025-12-23 17:30 UTC is Lighter Protocol. Sources:
  [legacy futures settlement](https://www.binance.com/en/support/announcement/detail/2a9feaa556f74dcdaa2192366f0e247c),
  [new underlying](https://www.binance.com/en/support/announcement/detail/6a33be00231c4539b3a4a625538e4d1e).
- PUMP: April 12 2025 14:30 UTC launch was PumpBTC; July 10 2025 07:30 UTC launch
  was Pump.fun pre-market. The intervening closure remains unresolved. Sources:
  [PumpBTC](https://www.binance.com/en/support/announcement/detail/4a4bb43f865a4348828de4facfc9eee4),
  [Pump.fun](https://www.binance.com/en/support/announcement/detail/4bc8b483d10d4619babb2015066b2d89).
- MDT: legacy contract settled May 16 2024 09:00 UTC; October 21 2026 09:20 UTC
  launch tracks Medtronic equity. Current nonCOIN cannot retrospectively label the
  entire legacy history. Sources:
  [legacy futures settlement](https://www.binance.com/en/support/announcement/detail/cb525a5fbb954935afc77630fc5bd0cc),
  [equity launch](https://www.binance.com/en/support/announcement/detail/29e4e52d711946c88762f0ba2259de2e).

Never join these as one return series. Same-underlying relistings also need separate
contract episodes: CTK/CVC/SLP have supported earlier settlements and later launches.
No scale adjustment or renamed-token return continuity is assumed.

## Remaining 72 mark keys: timing context

| Symbol | Missing keys | Official latest launch UTC | Before launch hour / in launch hour |
| --- | ---: | --- | --- |
| AERGO | 11 | 2025-04-16 11:00 | 11 / 0 |
| CTK | 11 | 2025-04-30 10:15 | 10 / 1 |
| CVC | 9 | 2025-05-16 08:30 | 8 / 1 |
| CVX | 9 | 2025-07-23 11:30 | 9 / 0 |
| LIT | 16 | 2025-12-23 17:30 | 16 / 0 |
| PUMP | 7 | 2025-07-10 07:30 | 7 / 0 |
| SLP | 9 | 2025-07-23 11:45 | 9 / 0 |

Launch sources: [AERGO](https://www.binance.com/en/support/announcement/detail/82f730b7ef444a38b323ab7a2e56b757),
[CTK](https://www.binance.com/en/support/announcement/detail/63155163bce541f5856d416efa71c6e8),
[CVC](https://www.binance.com/en/support/announcement/detail/bbe829426ad844b9b9dac62f878d1e67),
[CVX/SLP](https://www.binance.com/en/support/announcement/detail/b7b3a116013145569a9850f197c8cbe4);
LIT/PUMP linked above. 70 keys precede the stated launch hour; two fall inside
fractional launch hours. This supports investigating lifecycle boundaries instead
of blindly filling gaps, but does NOT prove all archive activity obeyed these
announcements. CVX/SLP archived mark observations resume at 09:00, and LIT at 16:00,
before times in the captured CURRENT announcements. Historical page versions,
pre-market/early observations and trading semantics need reconciliation.
All 72 missing keys stay in the original mask. No rows were created or gaps waived.

## Other findings and unresolved work

Supported events include WAVES, legacy LIT, AGIX/OCEAN, BTCST, ANT/DGB/CTK,
FOOTBALL/BLUEBIRD, KEY/REN, XEM/ORBS/LOOM, IDEX/SLP/GLMR/MDT/AUDIO and CVC.
Where verified, new-position restrictions are distinct from automatic-settlement
instants. A source settlement time does not establish its settlement price or the
cashflows on coincident funding observations. Spot removal times are not substituted.

BNT has a supported August 2023 launch, but its older archive/funding-month history
is unresolved. BTCST March 2021 closure does not resolve every later episode or the
January 2022 funding gap. LIT and MDT funding-month gaps overlap identity/episode
changes; absent funding cannot be zero-filled or bridged across them. The 424
trade-hour gaps, 1,913 zero-volume constant-trade files and inactive funding rows
remain diagnostic evidence, not automatically accepted/rejected trading intervals.

Before portfolio research: resolve the selected universe's episode starts/ends,
identity, partial-hour handling, contemporaneously knowable membership, terminal
pricing/funding and historical specifications. Prioritize the 38 unsourced priority
identifiers and the launch/archive timing conflicts. The stage-3 discussion must
separately freeze strategy hypothesis, permissible data/latency, fit/retraining,
chronological development/validation/final OOS protocol, leakage controls and costs.
No dates, strategy parameters or performance acceptance thresholds are chosen here.
# Remaining early identities: registered protocol

Registered before implementation or source acquisition, 2026-11-19.
Baseline: main 3a4d867, unified v20261119_003, 81 identifiers processed,
40 with price-history candidate weeks, 22 of those identity-corroborated.

## Scope and expectation

Prepare one bounded source/assertion plan for the remaining 18 history candidates:
ALGO, ZIL, KNC, ZRX, COMP, OMG, DOGE, SXP, BAND, KAVA, RLC, MKR, SNX,
WAVES, DOT, BTC, BCH, ETC (all USDT instruments). Expect some identity gaps to
close; no minimum pass count is imposed. All 81 identifiers remain in reports.
Do not extend to the other 924 identifiers or repeat eight-case runners.

## Fixed acceptance gates

- Exactly 18 additional cases; at most 64 registered public URLs, HTTPS host
  allowlist, maximum 32 MiB per response. No keys, purchases, crawling, or
  automatic alternate-source discovery. Freeze terminal failures and respect
  access pauses; never retry the previously failed futures-overview URL.
- Require historical snapshot numeric ID/name/symbol agreement, current provider
  numeric ID plus prospective name/symbol aliases, official venue full-name and
  perpetual-contract evidence, and an explicit token/native classification.
  ERC20 cases need an exact Ethereum address corroborated independently of CMC.
  Explorer evidence, when used, must also assert the token's name/symbol.
- KNC's 2020 ID1982/legacy address must not be replaced by ID9444/new KNC.
  A current-provider symbol alias needs a separate mandatory migration assertion;
  historical symbols stay unchanged. SXP's old Swipe token and later Solar phase
  require separate evidence. Current identity pages are not historical features.
- DOT scope begins with the superseding August22 announcement, not August20.
  BAND may use the official August market report with an explicitly conservative
  August4 scope, not an invented exact launch time. BCH scope still ends
  2020-11-15 12:00 UTC exclusively. No price splice, cap rescaling, or native-phase
  claims from retrospective rebranding notices.
- Replace BTC/BCH/ETC only by explicit predecessor rule hashes and reasons;
  preserve superseded rules/provenance. Failed assertions remain pending.
- Pilot must prune additional cases AND their source dependencies before HTTP.
  Validate shared historical inputs once and reproduce old frozen rules exactly.
  Test alias/wrong-ID rejection, scope boundaries, pilot pruning, and replacements.
  Export unique-ID JSON/CSV, proof checks, missing evidence, and report hashes.

## Execution and stopping point

Implement and run a small pilot only; hand the full bounded acquisition to the
user as one CLI invocation with summary/log paths. Expected success means the
processing and audit contract pass, not all 18 identity cases pass. Do not weaken
gates after seeing results. Any changed source or assertion requires a new plan
and output version. No canonical joins, labels, fit, performance, or OOS access.
Size publication vintage, contract specifications and paid funding remain open.

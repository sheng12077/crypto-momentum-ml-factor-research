# Early Size identity verification

Registered on main at `144143f`, implemented on `research/early-size-identities`.
Review date: 2026-11-19. Scope: 2020 metadata identities only. No canonical
joins, factors, labels, model fitting, PnL or OOS performance were produced.

## Evidence and decisions

The fixed 11-source plan captured eight sources, including one previously
verified LEND announcement. Ten new HTTP requests retrieved 2,897,992 total
stored bytes including reused evidence. Three Binance pages returned HTTP 202:
`iota_project`, `iota_units`, and `uni_project`. These terminal failures remain
frozen; `source_capture_complete=false`. A completed review is not a successful
source capture or a dataset eligibility approval.

All 54 historical CMC snapshots were checked against their raw/parsed hashes.
Current CMC numeric IDs were verified separately; a current URL, slug or name
cannot replace a historical numeric identity. The captured `/aave/` identity is
7278, whereas historical Aave/LEND rows use 2239, despite sharing that slug.

| Instrument | Historical CMC ID | Decision for this review |
| --- | --- | --- |
| IOTAUSDT | 1720, IOTA / MIOTA | Proposed alias remains blocked: local official project/unit evidence missing. All 29 named missing candidate asset-weeks remain unresolved. |
| UNIUSDT | 7083, Uniswap | Reject 4113 (UNI COIN). CMC and the project agree on the original Ethereum address, but the registered Binance project source is missing and a futures-specific 2020 link/launch remains unverified. Automatic join blocked. |
| LENDUSDT | 2239, Aave / LEND | Identity-only rule covers the review window from 2020-01-01 until settlement at 2020-10-10 00:00 UTC, exclusive. This lower bound is the review scope, not a verified listing date. |
| AAVEUSDT | 7278, Aave / AAVE | Separate identity-only rule starts 2020-10-16 07:00 UTC, ending 2021-01-01 exclusive. |

The official [Binance settlement and launch notice](https://www.binance.com/en/support/announcement/detail/17595222999545348c8acdd5dc41c00a)
establishes the LEND settlement and AAVE futures launch boundaries. The
[Aave migration documentation](https://github.com/aave/aavenomics) describes
100 LEND per AAVE; this does not authorize joining futures price histories.

The [Uniswap introduction](https://blog.uniswap.org/uni) provides the original
Ethereum token address `0x1f9840a85d5af5bf1d1762f925bdaddc4201f984`, matching
captured CMC 7083. A spot listing does not establish a futures launch date.
The exported UNI scope starts at the spot notice time only as an unapproved
candidate boundary; the resolver cannot use it while the rule is blocked.

Web-reviewed [Binance IOTA project material](https://www.binance.com/en/research/projects/iota)
and the [old trading-unit notice](https://www.binance.com/en/support/announcement/detail/115002193731)
support the proposed alias, but the local downloader received HTTP 202 for
both. Browser-readable evidence is not substituted for the missing hash-bound
captures. A USD market cap stays in USD, with scale 1; no multiplication by a
million is permitted. A spot unit statement would not verify all futures specs.

## Reproducibility and limits

Tool: `scripts/verify_early_size_identities.py`; fixed source contract:
`config/early_size_identity_20261119.json`; preregistration:
`docs/early_size_identity_protocol.md`.

Ignored evidence root: `data/interim/early_size_identity_20261119/`.
`capture_summary.json` retains failures and retrieval metadata;
`review_001/{provider_identities,proof_checks,mapping_decisions,summary}.json`
contains the decisions. Configuration, tool/dependency hashes and all historical
snapshot hashes are bound by the run configuration. Resume verifies cached
evidence and performs zero new HTTP requests; failures are not silently retried.

Seven new tests cover provider ID rejection, exact Ethereum addresses/platforms,
IOTA unit clauses, missing evidence, episode bounds, blocked UNI joins and
prohibited rescaling/splicing. Full suite: 171 passed; new files pass Ruff lint
and formatting checks. Cached resume was also checked.

Only two identity rules pass; no canonical joins were materialized. The other
833 literal cap leads have not been independently approved. Historical Size
publication/vintage, full contract specifications, funding cashflows and strict
historical eligibility remain unproven. Existing releases, split dates and
training permissions are unchanged.

Next task: decide whether to obtain the missing official source captures and
futures-specific UNI evidence, or explicitly exclude those cases in a separately
registered, versioned hypothetical Size join. Neither path establishes historical
publication vintage; no data purchase is implied by this review.

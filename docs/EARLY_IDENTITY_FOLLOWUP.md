# Targeted IOTA and UNI evidence supplement

Registered on main at `dff917a`, implemented on `research/early-identity-followup`.
Review date: 2026-11-19. This supplement leaves all prior failed capture/review
results intact. Scope is identity metadata for2020,not trading eligibility.

## Supported findings

**IOTA's proposed alias now passes this review's identity gates.** All54 captured
historical CMC snapshots identify1720 as IOTA/MIOTA. The hash-bound official
[Binance unit notice](https://www.binance.com/en/support/announcement/detail/115002193731)
states that its trading unit equates IOTA with MIOTA. The captured
[IOTA Foundation denomination explanation](https://blog.iota.org/stardust-upgrade-iota-tokenomics/)
independently explains the nomenclature. The latter is2023 retrospective
identity evidence,not a2020 publication timestamp or permission to apply later
supply changes backward.

This resolves the identity cause of the29 named missing price-history candidate
asset-weeks. They have not been materialized into canonical Size joins. USD
market cap retains scale1;no multiplication by a million or history splicing.
IOTA's rule starts at the2020 review boundary,not a verified futures listing time.
Its exact futures specifications and strict historical eligibility remain unknown.

**UNI futures launch time is now locally verified:** the official
[Binance UNI futures notice](https://www.binance.com/en/support/announcement/detail/300bf39679ee4110b440ee79185bc898)
specifies2020-09-18 07:00UTC and USDT collateral. This supersedes the previous
missing-launch finding,but does not turn a spot date into a futures date.
CMC7083's original Ethereum address agrees with the project introduction;
CMC4113 UNI COIN remains rejected. The earlier captured spot announcement names
Uniswap(UNI). However,the separately required Binance monthly cross-reference
returned HTTP202. UNI's combined-evidence identity rule remains blocked under
the preregistered acceptance gates;no gate was removed after capture.

LEND2239 and AAVE7278 retain their previously verified separate boundaries.
There are now three passing2020 identity rules:IOTA,LEND,AAVE. This is not a
count of fully eligible assets,and it does not approve the other833 literal leads.

## Capture, parser revision and checks

Fixed four public sources:three HTTP200 captures,one frozen HTTP202 failure.
Four new HTTP requests,96,469 stored raw bytes. The successful IOTA unit source
is the ordinary public CMS representation of the exact official article on the
same host,as explicitly registered. No alternate hosts,cookies or denial bypass.

Outputs: `data/interim/early_identity_followup_20261119_v002/` (ignored).
`capture_summary.json` retains the failed monthly source. `review_001` preserves
the initial HTML parsing failure; `review_002` contains the corrected proof,
clause,decision and summary files. Newer CMS articles contain serialized text
trees;the old2017 article instead contains HTML. The new parser checks the exact
article code before either format,and searches only its body,not related articles.
The original capture tool binding is preserved;the revised review separately
binds its tool,dependencies,source hashes and original capture contract.

An earlier output namespace,`early_identity_followup_20261119`,contains only a
pre-capture configuration binding. Its first run stopped because a Windows Git
checkout had converted the frozen prior tool to CRLF. Restoring the exact LF
bytes recovered the original recorded hash;no code logic or threshold changed.
The new capture namespace preserves that stop. `.gitattributes` now specifies LF
for research scripts and JSON configurations to keep byte hashes stable.

Tool:`scripts/followup_early_identities.py`;source plan:
`config/early_identity_followup_20261119.json`;acceptance registration:
`docs/early_identity_followup_protocol.md`.
Log:`reports/acquisition/early_identity_followup_20261119_v002.log`.

Full suite178 passed(seven new tests);changed-file Ruff lint/format pass.
Coverage includes missing evidence,exact article identities,spot-vs-futures
clauses,HTML body parsing,related-article rejection,launch interval boundaries,
preserved LEND/AAVE rules and terminal-failure integrity/no-retry behavior.
Frozen capture replay performs zero new HTTP. No canonical data,labels,factors,
models,PnL or OOS performance produced. Historical Size publication/vintage,
funding cashflows and full contract specifications remain unproven.

## Next bounded work

Review the remaining literal identity leads using the existing per-asset queue,
prioritizing qualified asset-weeks,without selecting from future survival or
returns. Retain unresolved cases and raw observations. The missing UNI monthly
evidence remains a named gate;do not silently retry it or drop it for approval.
Only after identity review should a separately registered hypothetical-lag Size
join measure actual usable breadth. This review does not justify buying data.

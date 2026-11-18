# Contract identity evidence review

Review date: 2026-11-18. Preregistered on main at ef41192, based on70e06ef.
Scope:27 priority identifiers (nine multi-ID, three reused,16 scaled flags with
overlap). All27 now have curated evidence assertions and proposed episode records.
This is a completed first evidence-review segment, not approval of historical joins.

## Result and artifacts

- 39 official Binance announcement captures verified, including nine reused
  lifecycle captures and30 new HTTP requests across two bounded capture passes.
  Cached raw total2,365,948 bytes;no access errors, credentials or payments.
- 41 curated assertions pass source-term checks, yielding35 proposed episodes;
  25 episodes have a vendor-ID proposal. Source-term checks validate the cited
  text, not the semantic truth of every inference. Human inference and unresolved
  items are recorded explicitly in the configuration.
- All506 no-literal-candidate identifiers retain an unresolved absence reason.
  Diagnostic leads include236 current noncoin annotations,15 scaled-contract
  flags and16 priority cases with evidence in this review; these groups overlap.
  None proves historical noncrypto membership or a below-top-200 absence reason.
  251 have at least one diagnostic lead;255 have none. These are triage counts,
  not resolved cause classifications.
- No factor, own return, label, fit, backtest, OOS performance, price conversion,
  cap conversion, episode stitch or revised source partition was produced.

Curated assertions: config/contract_identity_evidence_20261118.json.
Tool: scripts/review_contract_identity.py.
Ignored evidence root: data/interim/contract_identity_review_20261118/.
Final derived version: review_002/ with sources.json, proposed_episode_map.json,
missing_candidate_classification.json, summary.json and run_config.json.
An initial review/ build is retained; review_002 adds final boundary/unit/ID
validation and records CMS publishDate/lastUpdateTime fields. No source was changed.

## Multi-ID and reused identities

All times below are UTC. Unknown starts/ends are null, not infinite intervals.
Vendor IDs are proposals corroborated by captured CMC identity labels, not
verified chain/contract mappings. The same ID can also have changing labels.

| Contract | Supported evidence and proposed association | Remaining limitation |
| --- | --- | --- |
| BNXUSDT | Old candidate9891 closes2023-02-11 04:00; new candidate23635 relaunches2023-02-22 14:45 and closes2025-03-17 09:00. [Swap](https://www.binance.com/en/support/announcement/detail/4d23ada51a2e4fa182835c77d51ba1a9), [relaunch](https://www.binance.com/en/support/announcement/detail/940d0e48493e4627889c3f46371df70b), [FORM change](https://www.binance.com/en/support/announcement/detail/2f963977c7274e0583f16f2e26987b61). | Old contract becomes BNXUSDTSETTLED; historical API routes differ. No free position roll or mechanical Size multiplication. |
| BTCSTUSDT | Old candidate8210 closes2021-03-12 02:00; spot redenomination is1:10. New candidate8891 kept separate. [Notice](https://www.binance.com/en/support/announcement/detail/2c08ba9e1a1b409fb6a4a2cb2f5ed58b). | Futures relisting boundary for the new candidate remains unknown; spot reopening is insufficient. |
| BTTUSDT | Old candidate3718 closes2022-01-14 02:00. New candidate16086 is considered under separate1000BTTCUSDT. [Notice](https://www.binance.com/en/support/announcement/detail/2722e6da4f5141dd9b2fb07b5b1f3f75). | Do not apply the new token's Size series to the old contract. |
| DYDXUSDT | Original launch2021-09-10 03:30; candidates11156 Ethereum-era and28324 native-chain remain separate. [Launch](https://www.binance.com/en/support/announcement/detail/e90bc8a7484f4467812a0f71f34b53ca), [mainnet deposits](https://www.binance.com/en/support/announcement/detail/5e2f6ff0dc0548669e51abcef524f5ad). | A deposit-integration date does not establish futures index handover. |
| KNCUSDT | Candidates1982 legacy and9444 v2; official spot notice identifies KNCL versus the new contract. [Swap](https://www.binance.com/en/support/announcement/detail/46398ed8e121442a8f7502369540c0fe). | Futures migration timestamp and unit convention remain unknown. |
| LUNAUSDT | Original candidate4172 closes2022-05-12 15:30. New Terra candidate20314 is not accepted as continuation; the later USDT product is LUNA2USDT. [Closure](https://www.binance.com/en/support/announcement/detail/ef3ce76d5c2d45ee9b6dc3f281cde744), [LUNA2 launch](https://www.binance.com/en/support/announcement/detail/3b7184c80d544586993045a0e6e36e57). | LUNA2USDT requires separate identity/lifecycle review; no same-ticker splice. |
| STRKUSDT | Launch2024-02-20 17:00 explicitly tracks Starknet; proposed ID22691. Reject unrelated Strike ID8911. [Launch](https://www.binance.com/en/support/announcement/detail/2bfb6f8dccf447ada57165b7e6a4cf1b). | Chain/contract vendor crosscheck, full lifecycle and historical vintage still needed. |
| SUNUSDT | Candidates6990 old and10529 new. Spot migration identifies SUNOLD and a1:1,000 redenomination. [Plan](https://www.binance.com/en/support/announcement/detail/f923f2e4056843a9a9b87beb2aaa2f31), [completion](https://www.binance.com/en/support/announcement/detail/bf95a72b803247ea86904ac16e13087d). | No futures transition timestamp inferred from spot withdrawal/trading events. |
| LITUSDT | Litentry candidate6833 closes2025-01-31 09:00. Lighter candidate39125 launches2025-12-23 17:30 in pre-market mode. [Closure](https://www.binance.com/en/support/announcement/detail/2a9feaa556f74dcdaa2192366f0e247c), [new launch](https://www.binance.com/en/support/announcement/detail/6a33be00231c4539b3a4a625538e4d1e). | Different projects; pre-market to regular transition and old archive/launch conflicts remain unresolved. |
| PUMPUSDT | PumpBTC launches2025-04-12 14:30, closes2025-06-13 09:00. Pump.fun candidate36507 launches2025-07-10 07:30 in pre-market mode. [First launch](https://www.binance.com/en/support/announcement/detail/4a4bb43f865a4348828de4facfc9eee4), [closure](https://www.binance.com/en/support/announcement/detail/38a74ee47cdc43ebbc672e1dc6968358), [new launch](https://www.binance.com/en/support/announcement/detail/4bc8b483d10d4619babb2015066b2d89). | PumpBTC vendor ID absent from sampled pages; never backfill it with Pump.fun's Size. |
| MDTUSDT | Old MDT closes2024-05-16 09:00. New launch2026-10-21 09:20 explicitly tracks Medtronic ordinary shares. [Closure](https://www.binance.com/en/support/announcement/detail/cb525a5fbb954935afc77630fc5bd0cc), [equity launch](https://www.binance.com/en/support/announcement/detail/29e4e52d711946c88762f0ba2259de2e). | Legacy token identity needs further proof; crypto market cap is not applicable to the equity episode. |

BNX's ex-post trade/mark archive spans2022-04..2026-10, extending past the
captured2025 closure. That is a conflict to reconcile, not proof that the closure
is false, every later row invalid, or the same instrument continuously tradable.
The current plan contains BNXUSDT, not a certified legacy BNXUSDTSETTLED release.
No additional legacy-history download or automatic data exclusion was performed.

## Scaled-contract review

Official launch evidence for every flagged contract is captured. Underlying names
below may still be inferred from abbreviated labels; see per-record caveats.
Null vendor proposals mean unresolved ID/coverage, not zero market cap.

| Contract | Launch UTC | Proposed CMC ID | Official source |
| --- | --- | ---: | --- |
| 1000000BOBUSDT | 2025-06-05 08:30 | unknown | [Build On BNB](https://www.binance.com/en/support/announcement/detail/9d12cbfb72bb46e6835313471b6b3c85) |
| 1000000MOGUSDT | 2024-11-07 12:30 | 27659 | [Mog Coin](https://www.binance.com/en/support/announcement/detail/209355888f0042f788899dd1a04a0052) |
| 1000BONKUSDT | 2023-11-22 14:00 | 23095 | [Launch](https://www.binance.com/en/support/announcement/detail/7b3f500e0eec40f380023b4ff0ccca18) |
| 1000BTTCUSDT | 2022-01-26 03:30 | 16086 | [Launch](https://www.binance.com/en/support/announcement/detail/93cbeb51eed54bb9a9da8f8b3dfa20a2) |
| 1000CATUSDT | 2024-10-21 12:30 | unknown | [Simon's Cat](https://www.binance.com/en/support/announcement/detail/ed43b9b4d8f8471087b6d200bffcb4ff) |
| 1000CHEEMSUSDT | 2024-11-25 11:45 | 33280 | [Cheems](https://www.binance.com/en/support/announcement/detail/3dd2c1e3f5f040ac9f7a94c6597ef842) |
| 1000FLOKIUSDT | 2023-05-06 16:30 | 10804 | [Launch](https://www.binance.com/en/support/announcement/detail/cb89820730db4065b1d406350f6c0d9d) |
| 1000LUNCUSDT | 2022-09-09 13:00 | 4172 | [Launch, revised timing](https://www.binance.com/en/support/announcement/detail/5b9bc7ef56834de895cf829af859207e) |
| 1000PEPEUSDT | 2023-05-05 16:30 | 24478 | [Launch](https://www.binance.com/en/support/announcement/detail/41993e3389654713946bcb6b9b032eaf) |
| 1000RATSUSDT | 2023-12-15 14:00 | unknown | [Launch](https://www.binance.com/en/support/announcement/detail/c6eb2557f7a94f8db24ffda21ef0346e) |
| 1000SATSUSDT | 2023-12-12 14:00 | unresolved28194/28683 | [Launch](https://www.binance.com/en/support/announcement/detail/a86323c8ac774e85ba77a497f8f88e7f) |
| 1000SHIBUSDT | 2021-05-10 13:00 | 5994 | [Launch and units](https://www.binance.com/en/support/announcement/detail/fa934b93fea6494fb7361d45ca7cc98a) |
| 1000WHYUSDT | 2024-11-25 11:30 | unknown | [Why](https://www.binance.com/en/support/announcement/detail/3dd2c1e3f5f040ac9f7a94c6597ef842) |
| 1000XECUSDT | 2021-09-17 03:30 | 10791 | [Launch](https://www.binance.com/en/support/announcement/detail/974acd319e2343a094a9485d99fd5049) |
| 1000XUSDT | 2024-11-13 12:30 | unknown | [X Empire](https://www.binance.com/en/support/announcement/detail/220339ba12bd451c8362ad8501ea87e9) |
| 1MBABYDOGEUSDT | 2024-09-16 11:35 | unknown | [Baby Doge Coin](https://www.binance.com/en/support/announcement/detail/7fc53c11624b4d788fa97521a3480cda) |

1000BTTCUSDT also has an official closure2022-04-11 09:00, recorded independently
of the BTT spot migration. [Closure notice](https://www.binance.com/en/support/announcement/detail/4baf8d70485c46e38637bd063c58c4d8).

Only SHIB has an explicit futures launch statement defining1,000 underlying SHIB
and the index multiplier. SATS's spot notice explicitly defines the thousand-token
bundle, corroborating the futures label; candidate28194 uses raw symbol SATS and
candidate28683 uses1000SATS in captured CMC pages, so identity/denomination review
remains open. [SATS denomination](https://www.binance.com/en/support/announcement/detail/67d516a4ecec4c3ca17760d9afe04570).
Baby Doge's spot notice clarifies the million-token label, but the futures unit
field remains null pending historical specification reconciliation. [Clarification](https://www.binance.com/en/support/announcement/detail/4336ae4908154736acff8302509f7a05).
Other prefix-derived scales remain explicitly unverified, not executable specs.
No price-bundle multiplier is applied to an asset's total USD market cap.

## Reproduce and remaining gates

```bash
conda activate funding-strategy
python scripts/review_contract_identity.py build
```

The local cache and build are already completed; the user need not run this.
`capture` is for deliberate reconstruction on a new checkout with no evidence
cache. It reuses verified prior lifecycle captures, otherwise fetches sequentially
with bounded response/storage/source counts and stops on access errors. Final
build verifies article code, raw hashes, evidence terms, ID scope, UTC boundary
assertions, units and provable overlaps; it never makes automatic approvals.
84 unit tests pass, including seven new tests for evidence rejection, wrong vendor
IDs, UTC/event-time mismatch, interval overlap, unit assertions, article identity,
source-count budget, offline build/resume and raw corruption. New script/tests
Ruff lint and formatting pass. Native Python3.11 validation; configured runtime
remains3.13. Existing unrelated native full-tree import-order lint remains noted.
Original publication vintages remain unproven despite CMS publishDate and
lastUpdateTime being retained separately from retrieval/effective times.

Next: resolve vendor chain/contract IDs and denomination ambiguities, old BNX
archive routing, and futures-specific KNC/SUN/DYDX transition evidence. Then
reconcile unexplained observations outside captured episodes and point-in-time
membership before measuring usable Size coverage. Paid data is still undecided.
Historical joins approved=0; eligibility/PIT=false; OOS remains sealed.

# Historical extension and funding input inventory

Registered before implementation,2026-11-18. User authorized extending toward
2019 and including related funding inputs. Data engineering only;no strategy
performance,labels,fit,PnL or final OOS performance inspection. Existing releases,
registered stage0 calendar and approved OOS dates remain unchanged.

## Scope and order

1. Reparse all frozen924-symbol/2772-job official archive listing evidence after
   verifying source hashes,URLs,prefixes and pagination. Inventory monthly trade
   and mark1h plus funding files for2019-01 through2020-12. This start is a search
   bound,not a claim of contracts existing before the2019 platform launch.
2. Preserve all archived identifiers,including discontinued/Unicode names. Do
   not restrict to today's markets. Report first/last file months,checksum gaps,
   bytes and per-month three-series overlap as raw metadata,not tradability.
3. Produce an independently bound new raw-download plan,with no changes to old
   census/download/canonical outputs. Reuse verified raw caches where available.
4. Export a review queue comparing funding against trade/mark archive months
   over2019-01..2026-10. Mismatches are not proven unpaid/missing settlements:
   post-close artifacts,listing boundaries and identity episodes require review.
5. Funding completeness includes observed event timestamps/rates/intervals,
   sign/unit/quantity rules,settlement-time mark price and terminal events.
   Hourly mark closes are not exact funding-event prices. Current fundingInfo
   caps/intervals are not historical schedules. Public funding archives are not
   private account payment ledgers. Index/premium histories are optional later
   diagnostics,not prerequisites to download everything indiscriminately.

The funding-history API documents event time,rate and associated markPrice;
historical availability still requires a bounded probe. Preserve prior failed
REST evidence;no repeated broad retries or access-limit bypass. Existing rates
must not be called forecast-known or proven paid. No OI/long-short-ratio/news
expansion. Historical Size and identity mapping remain a separate required
extension before claiming four-component coverage in the earlier period.

## Fixed engineering acceptance

- All924 identifiers and2772 cached jobs verified;incomplete/corrupted evidence
  fails closed. Zero metadata HTTP requests during inventory.
- Every selected file has an exact safe key and valid month/size. Report absent
  checksums;full acquisition readiness is false if any are absent. No zeros/fills
  for absent funding or reconstructed prelisting trading histories.
- Do not prescribe an available file count before inventory. Export exact counts
  and byte totals from evidence,including explicit zero coverage if2019 absent.
- Small real pilot:BTCUSDT andETHUSDT,earliest available month for each of the
  three series,at most6 files and4MiB compressed. Actual available count reported,
  never invented to meet six. Require official SHA/size/CSV validation,then
  verified resume with zero new ZIP downloads. Network failure remains failure.
- Full download is an explicit-budget,resumable WSL handoff after pilot. Preserve
  acquisition errors and keep readiness false;completion means RAW success only.
- Synthetic checks cover2019 filtering,exact paths,checksums,missing series,
  provenance/pagination corruption and pilot selection. Existing tests continue
  passing;reusable tooling lives in repository. No old frozen tool dependencies
  modified. Extending training or weekly derived layers requires a separately
  versioned protocol amendment before performance,not overwriting current rules.

Official documentation checked2026-11-18:
[public archive](https://github.com/binance/binance-public-data),
[funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History).

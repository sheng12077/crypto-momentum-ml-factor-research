# Targeted early-history source recovery and episode review

Registered2026-11-19 before implementation. User authorized QTUM February funding
check plus DEFI/LEND lifecycle review. Data/evidence only,no model/returns/PnL or
OOS performance. Existing releases,policies,calendar and training dates unchanged.

Frozen sources/config:`config/early_cases_20261119.json`,four official URLs.
Reuse bounded capture helper (at most3 transport/5xx attempts per URL;stop on
access/rate restrictions,retain terminal failures). Preserve raw responses and
hashes. No alternative-host or unbounded lookup fallback. Source capture failure
must stay visible;missing evidence is not approval.

QTUM query covers2020-02-01 inclusive through2020-03-01 00:00 UTC inclusive,
limit1000. Require correct symbol,bounds,strictly ordered unique millisecond
timestamps,finite rate/positive nonempty markPrice;reject a saturated page as
incomplete. Export February observations separately;no fabricated interval8h,
zero-funding fill or silent canonical insertion. Classify any observations before
the independently supported launch as prelaunch evidence,not payments. Verify
the March1 overlap against the checksum-verified March archive using Decimal
rate equality;report mismatch or missing overlap explicitly. No predetermined
recovery count;sample spacing and endpoint completeness are not payable proof.

Capture DEFI/LEND CMS articles and verify exact dated clauses/product identity.
Record DEFI composite-index classification and its launch;do not map it to a
same-ticker standalone token. Preserve/quarantine prelaunch observations.
Record LEND perpetual settlement and later AAVE perpetual launch separately;
spot token-swap ratio does not authorize contract-price splicing. Restrict new
decisions to the early research window through2021-01-01;existing releases need
explicit later integration. Publication/revision vintage remains unproven.

Acceptance:input/source hashes bound,finite/ordered/no-duplicate validation,
March overlap checked,unsupported assertions flagged,verified resume makes zero
new source HTTP requests. Synthetic tests for rate precision,bounds,duplicates,
truncation,missing mark/interval,overlap mismatch and article-clause verification.
No strategy eligibility/funding-cashflow upgrade even on technical success.

# Official Daily-Archive Fallback

Registered: 2026-11-17, after the primary API recovery completed. Its result is
32,808 verified rows, 432 unresolved hours in 19 ranges, zero conflicts; the
33,240-hour completion gate failed and is not revised. Some saved API replies
are empty or partial, not transport errors. This is data engineering, not a
blind strategy experiment.

## Fixed extension

Use only exact keys from the primary unresolved list and their original frozen
range boundaries. Try official Binance daily markPriceKlines ZIPs for UTC days
covering those ranges plus both observed boundary hours. No alternative prices,
venue substitution, imputation, parameter changes or additional strategy tests.

- Deduplicate symbol/day requests; at most 200 daily ZIPs plus CHECKSUM requests.
- At most 2 MiB per ZIP, 50 MiB combined ZIP payload, one worker and minimum
  0.25-second global spacing between HTTP requests. No automatic retry loop.
- Verify official checksum, one expected CSV, decompression budget, exact UTC
  date/hour stamps and hourly close time. Retain raw responses and provenance.
- Combine daily source rows only when the complete original range and both
  boundaries exist and decimal OHLC agrees with the monthly boundary observations
  and all previously accepted overlaps. Quarantine conflicts, never average them.
- Cache/resume must revalidate saved source hashes and checksums. Missing archives
  and incomplete ranges remain unresolved; preserve the original primary result.

## Unchanged acceptance

Complete recovery still requires 33,240 distinct exact target keys, zero unresolved
keys and zero conflicts. If source data remain unavailable, report partial recovery
with a nonzero exit; do not invent rows to satisfy the gate. A separately versioned
partial overlay may be exported ONLY with explicit `allow-partial`, zero source
conflicts, exact verified-key counts and a manifest stating recovery_complete=false
and unresolved counts. This storage option does not change any pass threshold.
Eligibility remains false and no existing RAW/canonical dataset is overwritten.

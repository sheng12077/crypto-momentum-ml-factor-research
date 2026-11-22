# Contract identity evidence review protocol

Registered 2026-11-18 before new source acquisition/implementation, following
70e06ef. Metadata review only; no strategy experiments, returns, fits or OOS.

Fixed scope: nine multi-ID identifiers, three known reused identifiers and
16 possible scaled contracts from identity audit002 (27 distinct identifiers).
Also classify the existing506 no-literal-candidate cases into evidence-backed
leads and unresolved groups; do not require all506 to be manually resolved here.

Expectation: some apparent gaps reflect scaled contracts, old/new vendor IDs,
renames or unrelated same-ticker assets. Ticker stripping is insufficient.

Acceptance:

- Review each priority ID; preserve unknown boundaries, multipliers and vendor
  identities. Separate effective event times from source publication/retrieval.
- Use official exchange/vendor/project sources, save bounded raw bytes and
  retrieval hashes in ignored data. Reuse prior hashed official captures.
  No keys, paid subscriptions, bypass, parallel retry storms or bulk market data.
  Sequential new fetches >=2 seconds apart, <=60 sources/64MiB total new raw,
  <=2MiB each; stop acquisition on401/402/403/429; <=3 transport/5xx attempts.
- Curated assertions must name exact source evidence terms and explicitly state
  what is inferred. Spot migration facts do not certify futures rollover, trading
  continuity, cashflows or historical contract specs.
- Produce a separate evidence-backed proposed episode map with UTC boundaries
  where proven, exact vendor IDs, unit conventions where proven, and unresolved
  items. Identity evidence alone cannot approve a strategy-ready Size join.
  No unit conversions of cap, price or supply, no episode stitching or filling.
- Verify source hashes/evidence assertions, unique records, UTC interval ordering,
  no accidental cross-identity overlap and tests rejecting missing evidence and
  malformed boundaries. Preserve acquisition/audit/canonical artifacts.
- Summarize supported versus unresolved conclusions; source publication vintages,
  historical eligibility and OOS remain unverified/sealed. No paid-data decision
  based merely on the current noncoin annotation or full-period availability.

Review may support an underlying/vendor candidate without proving complete
effective intervals or historical availability. Such partial evidence must remain
explicit and unusable for automatic historical joins until those gates pass.

# Approved chronological split

User approved these calendar windows on 2026-11-18, before strategy performance
inspection. All boundaries are UTC; start inclusive, end exclusive.

| Development round | Training window | Validation window |
| --- | --- | --- |
| 1 | 2021-01-01 to 2023-01-01 | 2023-01-01 to 2024-01-01 |
| 2 | 2021-01-01 to 2024-01-01 | 2024-01-01 to 2025-01-01 |

Final sealed OOS: **2025-01-01 to 2026-11-01** (January 2025 through October
2026 inclusive). Development validation is used for choices and is not the final
untouched test. No random row split is authorized.

Historical observations before a validation/OOS boundary may supply trailing
features, provided they were available by the decision time, remain in the same
episode and meet history checks. A 120-day return needs 121 valid endpoint-inclusive
daily closes. The calendar windows do not waive the initial feature warm-up.

Training examples whose future-return labels reach the validation/OOS period
must be excluded. Exact usable sample endpoints and any additional gap depend on
the still-unselected label horizon, execution timing and availability rules.
Preprocessing and model fitting must respect each training boundary.

Weekly horizon and weekly baseline schedule subsequently approved in
[WEEKLY_RESEARCH_SEQUENCE.md](WEEKLY_RESEARCH_SEQUENCE.md).
Stage0 subsequently fixes target/clock assumptions in
[WEEKLY_BASELINE_STAGE0.md](WEEKLY_BASELINE_STAGE0.md).
Still undecided: holdings, buffer thresholds,
model selection, refit schedule (including within final OOS), costs and acceptance
criteria. The windows do not authorize a particular OOS refit policy. Freeze the
complete protocol and preregister experiment expectations/thresholds before
implementation or performance experiments. Final OOS performance stays sealed
until the final version is frozen; paper/live discussion follows OOS review.

Data-quality/coverage inspection is permitted without strategy-performance
inspection. Do not choose a historical universe using full-period membership or
future availability. The seven-day Size availability assumption does not prove
publication/vintage; strict eligibility remains unresolved regardless of split.

User-reported full daily build: success, zero errors, 223.383 seconds;924 IDs,
1,968,120 rows,66,893 source partitions,244 legacy BNX hours. Ever-passing
diagnostics:787 price/funding,338 assumed-Size four-factor (also338 class-review
clear),0 strict. These are not simultaneous tradable universe counts. Summary
prints the earlier pilot first and full manifest second; this is expected.

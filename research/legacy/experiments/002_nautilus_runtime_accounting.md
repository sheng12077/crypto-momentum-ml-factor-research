# Experiment002: Nautilus runtime and deterministic accounting

Registered2026-11-20 before implementation/execution. User authorized starting
the backtest work. This segment establishes the actual simulator runtime and
hand-verifiable execution/accounting before attaching a learned2021–2022strategy.

## Scope

- Isolated project runtime:CPython3.13,official PyPI NautilusTrader1.231.0stable.
  Pin resolved dependencies before executing scenarios. No modification of the
  borrowed funding-strategy environment. Use the stable version's actual APIs,
  not incompatible2.x documentation examples. No production/paper/live connection.
- Use syntheticBTCUSDTlinear-perpetual data and tiny fixed market orders with
  sufficient cash/margin. No learning,parameter search or performance-based
  selection. No2023/2024strategy results or sealed2025–2026OOSaccess.
- Fee profile:VIP0reference,noBNBdiscount,maker0.0002/taker0.0005;explicitly
  current-cost research assumptions,not authenticated/historical account fees.
- Exercise market fills,fee deductions and adverse slippage. Require an actual
  Nautilus venue/account/order/fill/position path,not a parallel portfolio engine.
  Additional cost stress remains0/2/5/10bpsperfill;the base spread is explicit.
- Inspect stable runtime's funding path and test native funding if supported.
  A missing/unsupported funding path is an explicit failed readiness check,
  not permission to omit funding from strategy results. Any adapter implementation
  must use the documented simulator/accounting extension points and be tested.

## Expected known-answer checks

- One-unit buy10000/sell10100,takerfees5and5.05:net89.95USDT. Two fills,flat
  final position. Fee on notional,not margin. Charge both open and close.
- Flat-price roundtrip10000with zero added slippage:fees10,net-10USDT.
- Adverse slippage at fixed pre-stress anchors must worsen buy/sell fill prices,
  never improve them;calculate fees on resulting actual fill notional. Avoid
  charging the implicit price effect twice as another cash debit.
- If funding supported:positive rate debits long and credits short at the same
  boundary;flat positions have no funding charge. Preserve timestamp semantics,
  test exact-boundary and non-exact-boundary source timestamps before real data.
- Monetary reconciliation tolerance:at most0.01USDT(the reporting quantum),with
  exact fill count/side/quantity and flatness assertions. RejectNaN/missing fees.
- Deterministic reruns must produce identical normalized reports/hashes. Runtime
  version,scenario definitions and source/config hashes accompany every report.

## Stopping point and next phase

Deliver pinned runtime,reusable smoke runner,known-answer reports and readiness
status. Do not label synthetic scenarios a2021–2022strategy result. This is
engineering validation,not evidence of profitability. Full strategy run still
requires executable universe/feature/model/portfolio/funding/fill rules;routine
defaults can be concretized for review without pretending proposals were approved.

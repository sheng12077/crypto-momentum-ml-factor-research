# Experiment 001: weekly baseline, stage 0 preregistration

Registered before implementation and before performance inspection. Stage 0 is
only a temporal-contract and development-coverage check. This does not register
a complete trading experiment or authorize performance/model selection. The
weekly/buffer/sizing sequence and approved calendar splits remain unchanged.

## Fixed target and timeline

Machine-readable contract: `config/weekly_baseline_v1.json`, all UTC.
Every Monday use observations strictly before00:00, decide at01:00 (one-hour
assumed publication/processing lag), and proxy execution over01:00--02:00. The
proxy price is this complete hour's quote volume divided by base volume, for
both entry and the following Monday's corresponding exit window. Neither its
volume nor its price is available to the signal at01:00. It is not a claim that
an actual order would fill at hourly VWAP or that this latency is verified.

Primary prediction label: simple proxy-price return over seven calendar days,
before fees, slippage and funding. Predictive target excludes funding; later
portfolio evaluation must include payable signed funding separately. Label
availability is assumed no earlier than exit-window end plus one hour. Exact
source publication/vintage remains unverified. No label values are computed by
stage 0; missing prices, episode changes and terminal events cannot later be
resolved by filling prices or dropping losses silently.

Features use the preceding UTC daily sidecar (Sunday data day, Monday00:00
reference). Rank/transform features at decision time, not by future membership.
Model fitting/preprocessing only uses labels whose assumed availability is
strictly before the fitting boundary. Warm-up history may precede that boundary.
Calendar eligibility is not sufficient for valid price labels or trading.

## Hypotheses and acceptance thresholds for stage 0

Expectation: build an auditable deterministic weekly calendar and show whether
the development data can support diversified weekly cross-sectional research.
No expected sign or profitability is asserted at this stage.

Engineering acceptance, all mandatory:

1. Exactly209 Monday decisions in [2021-01-01,2025-01-01), with seven-day label
   horizons and strictly ordered cutoff/decision/fill/label-availability times.
2. Zero train labels available at or beyond each training boundary; zero usable
   validation labels available at or beyond its end. Boundary-crossing samples
   are explicitly labelled purge rows, not silently included or evaluated.
3. No2025+ observations materialized by the coverage reader; no price, target,
   return, model fit or PnL output. Final OOS remains sealed.
4. Every input daily sidecar matches its existing SHA and index counts/identity;
   run binds config, script/helper hashes, source manifest and all input indices.
   Conflicting/corrupted/incomplete inputs fail; never overwrite a bound run.
5. Report each decision date's price/funding, assumed-Size four-factor and strict
   counts, plus min/median/max and fraction with at least20 names. The20-name
   indicator is a fixed diversification diagnostic, not a portfolio-size choice
   or acceptance criterion for economic profitability. No minimum coverage
   fraction is imposed after seeing results; poor coverage is reported as such.

Readiness for strategy experiments requires separately registered holdings,
weights/exposures, model/baselines/refit, fees/slippage, funded PnL and terminal
accounting, statistical/performance gates and treatment of unresolved Size
vintage. These remain pending; do not silently upgrade diagnostic eligibility.

## Bounded implementation and checks

Implement contract validation, weekly calendar/split-safe fitting permissions,
and integrity-checked projected daily coverage with no label values. Synthetic
tests cover exact boundaries, timezone handling, OOS guards, corrupt inputs and
missing/duplicate decision rows. Run a small real three-identifier coverage
pilot plus verified resume, then hand off the full924-ID development coverage
scan if substantial. Never implement buffer or sizing in this stage.

Artifacts are ignored under `data/interim/weekly_baseline_stage0_20261118/`.
No datasets/secrets in Git. Preserve this registered protocol and report any
deviation; do not revise thresholds after observing outcomes.

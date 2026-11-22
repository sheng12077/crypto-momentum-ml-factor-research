# Experiment006: benchmark asset-class correction

Registered2026-11-21after the first fundedBTCperpetual benchmark failed and
before any valid strategy performance was inspected. Preserve the failed run
and diagnostics;do not change model/features/cohort/weights/execution/cost grid.

The funded-perpetual buy-and-hold is not a spot benchmark. Its modeled2021–2022
funding cost is16632.7478USDTperBTC;with the initially purchased quantity it
produces nonpositive NAV inNovember2022. Do not cap the loss, omit funding or
change leverage/allocations to make that benchmark pass. Keep it as a failed
diagnostic, separate from the user's originally requested BTC/ETHspot hold.

Fetch official spot1hmonthly ZIP+CHECKSUM forBTCUSDTandETHUSDT,2021–2022only:
48archives/96requests,max128requests,1sminimumspacing,2MiBperZIP,64MiBtotal,
10MiBdecompressed,40stimeout. Verifychecksum/member/uniquealignedhourtimes/
OHLC/positivevolume and all required entry/exit/valuation hours;403/418/429stop.
No old sources overwritten;successful cached requests are revalidated/reused.

Spotbenchmark is a passive fixed-unit accounting identity, not another strategy
backtester or a claimed Nautilusspot-exchange simulation. Atfirstday02UTC spend
100000USDTinclusivefeesusing prior01–02hourspotVWAPand5bpsadverseprice;units=
budget/(fillprice*(1+0.001)). Quote-notional budget is fixed before fill;no leverage,
funding or resizing. Valueatdaily00UTCusinglatestcompletedspotclose. Final sell
allunits2022-12-30at23UTCusing22–23hourVWAPminus5bps,taker0.001,noBNB. Standard
current-cost reference,nothistoricalpromotions/account-exactfees. Entry/exit
commissions are included once;initialNAVcash100000;matchedcalendarwithstrategy.

Replace only the primary report's benchmark columns with these genuine spot-price
hold series, label the implementation/fees explicitly. Preserve both source and
passive-benchmark ledgers. Reuse the already-fitted frozen model and its existing
SHAP after verifying training rows,predictions,parameters and additivity;do not
refit/tune because of this benchmark failure. OriginalExperiment005strategy
rules/acceptance/replay remain unchanged. No2023/OOS values or performance.

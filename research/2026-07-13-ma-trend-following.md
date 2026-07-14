# Research notes — MA trend-following (session 2026-07-13)

## Sources
1. Faber, M. (2007), "A Quantitative Approach to Tactical Asset Allocation,"
   J. Wealth Management. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461
   10-month SMA timing on US equities: equity-like returns, bond-like drawdowns.
2. Zakamulin, V. (2014), "The real-life performance of market timing with moving
   average and time-series momentum rules," J. Asset Management 15(4).
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2242795
   With realistic costs + true out-of-sample, edge is mostly RISK REDUCTION, not return.
3. Zakamulin, V. (2018), "Revisiting the Profitability of Market Timing with Moving
   Averages," Int. Review of Finance. https://onlinelibrary.wiley.com/doi/abs/10.1111/irfi.12132
   Strong data-mining-bias warnings; prefer robust parameter neighborhoods.
4. Alpha Architect summary of Zakamulin's MA research:
   https://alphaarchitect.com/the-moving-average-research-king-valeriy-zakamulin/

## Takeaways applied
- Hysteresis band around the SMA to cut whipsaw/cost drag (daily signals).
- Selection by *neighborhood-average* in-sample Sharpe, not the single best cell.
- Expectation set by literature: trend filter should LAG B&H in bull decades
  (our 2010-2019 IS confirms) and earn its keep in bear/vol regimes (2020, 2022).

## Negative/contextual findings this session
- Band=0 (raw daily crossover) is dominated at every window by banded variants
  in-sample — cost drag from ~3-9 trades/yr is material at 0.1%/side.
- Short windows (50d) are noise-dominated: IS Sharpe 0.24-0.63, unstable across band.

## Data environment (important)
Sandbox proxy blocks Yahoo/Stooq/AlphaVantage/FRED; only github.com is reachable.
Adopted SteelCerberus/us-market-data (SPY total-return proxy, 1885 -> 2025-12-19,
committed snapshot in data/cache/). Multi-asset universe (QQQ/DIA/IWM/sectors/
TLT/GLD, Mag-7) NOT yet available -> top roadmap item.

# M3 — When does v2 ever leave the index? (exposure-profile memo)
Session 16, 2026-07-21. Zero configs burned; analysis of the FROZEN champion only.

Prompted by a direct question from Mr. Menéndez: "Why is the $1,000 still only
in the S&P — why has it not bought anything yet?"

## The design answer
Champion v2 = vol_target(0.18, lb20) × SMA200/3%-band trend gate, traded on SPY
with a T-bill cash sleeve. Its instrument universe IS the S&P 500 ETF. It never
"buys things"; the entire edge claim is WHEN to hold the index vs cash:
- Trend gate ON (price > SMA200 +3% band) and 20d vol < 18% → 100% SPY.
- Vol above target → scale exposure down proportionally (partial cash).
- Trend gate OFF (price < SMA200 −3% band) → 100% cash earning T-bill yield.
Multi-asset alternatives (dual momentum, GTAA, risk parity, CTA, VAA, sector
rotation…) were all tested E3–E25 and none passed the significance gate; v2
remains champion. Stock-picking was never in scope (G4 caps single stocks anyway).

## Historical exposure profile (2000-01 → 2026-07-20, 6,654 trading days)
- Fully invested: 64.6% of days
- Partially de-risked (vol scaling): 8.5%
- Fully in cash: 26.9%
- Average exposure: 0.716

## Major de-risk episodes (≥10 days below 0.5 exposure)
| Window | Days | SPY move while out |
|---|---|---|
| 2000-10 → 2003-04 (dot-com bust) | 628 | −29.8% avoided |
| 2007-11 → 2009-06 (GFC) | 382 | −31.8% avoided |
| 2022-04 → 2023-01 (rate bear) | 191 | −4.3% avoided |
| 2020-03 → 2020-06 (COVID) | 59 | +7.4% missed (late re-entry) |
| 8 further whipsaws (2004…2025) | 24–109 | +5% to +12% missed each |

## Honest read
The gate's value is concentrated in the three long bears; the cost is ~8
whipsaws where SPY rallied 5–12% without us. Net-net this is exactly why v2's
backtest beats SPY on Sharpe/drawdown ($8,382 vs $6,775 per $1k since 2000,
worst DD −20.5% vs −55.2%) while trailing in strong bull stretches.
The live book was last below full exposure on 2026-07-07 (vol scaling);
since then close > band (742.09 vs 714.66) and 20d vol 11.7% < 18% → 100% SPY
is the correct, confirmed position. When the tape breaks, the same rule that
holds SPY today is the one that steps aside.

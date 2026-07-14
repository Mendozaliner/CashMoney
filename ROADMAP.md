# ROADMAP (reprioritized 2026-07-14 s4)

1. **Dual momentum (Antonacci) — NEW SLEEVE.** Multi-asset data now live
   (28 tickers). SPY/QQQ/DIA vs TLT/IEF absolute+relative momentum, 12-1 skip.
   Own pre-registration, own $1k paper sub-portfolio if it clears its bar.
   Cross-sectional momentum is the desk's main remaining diversification source.
2. **Drawdown kill-switch overlay on v2** (Phase-2-legal risk overlay):
   go-to-cash at -12%/-15% portfolio DD with re-entry rule; LTCM/Niederhoffer
   guardrail lessons. Pre-register with skeptical prior (whipsaw cost).
3. **Criterion-1 significance gap:** v2-minus-SPY bootstrap over full 2000-2025
   walk-forward (not just 2020+); revisit after a second sleeve enables an
   ensemble test.
4. Cross-sectional sector momentum (XL* universe) — after item 1.
5. Position sizing: fractional Kelly on champion (Phase-3 material).
6. VIX term-structure data acquisition (spot VIX exits FAILED E2; literature
   says the signal, if any, is in the term structure — needs futures data the
   pipeline doesn't carry yet).

## Negative results (do NOT re-test)
- Raw daily SMA crossover (band=0); 50d SMA windows (noise).
- Vol targets <=0.12 on trend-gated SPY (over-delever; Sharpe 0.69-0.76).
- Wider vol targets 0.21-0.30: flat surface, no gain over v2 (E1, 2026-07-14).
- Spot-VIX percentile de-risking overlays on v2, scale {0.5, 0}, pct {70,80,90}:
  failed DD/DSR/CI bars (E2, 2026-07-14). High VIX precedes high returns.

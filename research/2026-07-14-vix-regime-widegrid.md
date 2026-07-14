# Research notes — 2026-07-14: VIX regime filters & vol-target robustness

## Sources (web pass)
1. QuantPedia — "Time-Varying Equity Premia with a High-VIX Threshold": most of the
   equity premium is realized in the ~20% of days FOLLOWING the highest VIX values
   (≈80th pct+). Implication: de-risking on high VIX sells exactly when expected
   returns are highest. https://quantpedia.com/time-varying-equity-premia-with-a-high-vix-threshold/
2. MDPI JRFM — "VIX Futures as a Market Timing Indicator": support is for the VIX
   TERM STRUCTURE (backwardation/contango) as a CONTRARIAN signal, not spot-VIX
   level exits. We hold only spot ^VIX. https://www.mdpi.com/1911-8074/12/3/113
3. Hartford Funds — "When Fear Runs High, Time to Buy?": post-spike forward returns
   historically above average. https://www.hartfordfunds.com/practice-management/client-conversations/managing-volatility/when-fear-runs-high-time-to-buy.html
4. Volatility Box — regime detection survey (threshold rules, 200d VIX MA, HMMs);
   thresholds are the crudest tier. https://volatilitybox.com/research/volatility-regime-detection/
5. Tandfonline FAJ — "Conditional Volatility Targeting": vol targeting helps mainly
   in high-vol REGIMES; unconditional scaling churns. https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1790853
6. Alpha Architect — vol targeting improves risk-adjusted returns for risk assets;
   Sharpe gains NOT sensitive to vol-estimator choice. https://alphaarchitect.com/volatility-targeting-improves-risk-adjusted-returns/
7. arXiv 2603.01298 — adaptive vol control: performance varies smoothly over the
   parameter space (plateau expectation for E1). https://arxiv.org/html/2603.01298

Synthesis: skeptical prior for spot-VIX de-risking overlays (they fight the
post-spike premium); supportive prior for realized-vol scaling already in v2,
with an expected FLAT parameter surface. Both priors were confirmed by E1/E2.

## Experiments (pre-registered; see hypotheses.jsonl)
- E1 (25d3eaf2fb): wider vol-target grid tv {0.21-0.30} × lb {20,60,120}, 12 configs.
  RESULT: hypothesis PASSED — v2 mean WF Sharpe 0.844; best wider config 0.844
  (tv0.24/lb20); no artifact. Surface nearly flat (0.81-0.84), so vol scaling's
  edge over the bare trend gate is real but small. No change adopted.
- E2 (d5c820392c): VIX rolling-3y-percentile overlay on v2, 6 configs.
  RESULT: FAILED its bar — best (p90/scale0.5) improves worst-fold DD only
  1.27pts (<2 required), DSR 0.9455 (<0.95), diff-vs-SPY CI straddles zero
  (lo −0.55). Hard de-risking (scale 0) was worst in every fold. DISCARDED.

## Also established this session (real-data re-baseline, 0.15% costs, holdout locked)
Walk-forward folds 2000-09 / 2010-19 / 2020-2025H:
- SPY B&H Sharpe: 0.088 / 0.919 / 0.736 (DD −55 / −19 / −34)
- v1 trend: 0.865 / 0.769 / 0.842 (worst DD −20.6)
- v2 (champion): 0.859 / 0.784 / 0.889 (worst DD −20.5)
- v2 vs SPY 2020-2025H: Sharpe +0.15 point estimate but bootstrap CI [−0.56, +0.89]
  — NOT yet statistically distinguishable from SPY. Criterion-1 check: point-pass,
  significance-fail. This is the honest gap to close (longer window or ensemble).
- After-tax do-nothing check (trend-gate episodes 2020-2025H, 35% ST / 15% LT):
  buy-and-hold $1.920 vs strategy $1.564 per $1 — DOING NOTHING WON after tax.

"""Pre-registration harness (added 2026-07-14).

Forces the desk to commit to a hypothesis and a pass/fail bar BEFORE seeing
results, and caps how many configurations a single idea may burn. This is the
antidote to running a huge grid and telling a story around whichever cell won.

Workflow each experiment:
    reg = preregister(
        hypothesis="VIX>30 regime filter cuts drawdown without killing CAGR",
        success_criteria="OOS deflated-Sharpe >= 0.95 AND diff-vs-SPY CI clears 0 "
                         "AND MaxDD not worse than champion by >10%",
        grid_size=9,                 # e.g. 3 thresholds x 3 lookbacks
        primary_metric="sharpe",
    )
    ... run <= reg.max_configs experiments ...
    record_outcome(reg.id, verdict="discarded",
                   evidence={"deflated_sharpe": 0.71, "diff_ci_lo": -0.1})

Records live in research/hypotheses.jsonl (append-only; never rewritten).
"""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(__file__).resolve().parent / "hypotheses.jsonl"

# Hard cap: no single idea may evaluate more than this many configurations.
# More configs = more selection bias = a higher deflation penalty you can't win.
MAX_CONFIGS_PER_IDEA = 12


class ConfigCapExceeded(ValueError):
    pass


@dataclass
class Registration:
    id: str
    ts_utc: str
    hypothesis: str
    success_criteria: str
    grid_size: int
    max_configs: int
    primary_metric: str

    @property
    def cap_ok(self) -> bool:
        return self.grid_size <= self.max_configs


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def preregister(hypothesis: str, success_criteria: str, grid_size: int,
                primary_metric: str = "sharpe",
                max_configs: int = MAX_CONFIGS_PER_IDEA,
                enforce: bool = True) -> Registration:
    """Record a hypothesis + success bar before running. Raises if the grid
    exceeds the config cap (set enforce=False to only warn)."""
    if grid_size > max_configs:
        msg = (f"grid_size={grid_size} exceeds MAX_CONFIGS_PER_IDEA={max_configs}. "
               "Shrink the grid or split into separately-registered ideas.")
        if enforce:
            raise ConfigCapExceeded(msg)
        print("WARNING:", msg)
    ts = _now()
    rid = hashlib.sha1(f"{ts}|{hypothesis}".encode()).hexdigest()[:10]
    reg = Registration(rid, ts, hypothesis.strip(), success_criteria.strip(),
                       int(grid_size), int(max_configs), primary_metric)
    _append({"kind": "registration", **asdict(reg)})
    return reg


def record_outcome(reg_id: str, verdict: str, evidence: dict | None = None,
                   notes: str = "") -> None:
    """Log the result of a pre-registered idea. verdict in
    {'adopted','discarded','inconclusive'}."""
    verdict = verdict.lower()
    if verdict not in {"adopted", "discarded", "inconclusive"}:
        raise ValueError("verdict must be adopted/discarded/inconclusive")
    _append({"kind": "outcome", "id": reg_id, "ts_utc": _now(),
             "verdict": verdict, "evidence": evidence or {}, "notes": notes})


def trials_this_period(since_iso: str | None = None) -> int:
    """How many configurations have ever been registered (optionally since a
    date). Use to raise the deflation bar as cumulative testing grows."""
    if not LOG.exists():
        return 0
    total = 0
    for line in LOG.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("kind") != "registration":
            continue
        if since_iso and rec["ts_utc"] < since_iso:
            continue
        total += rec.get("grid_size", 0)
    return total


def _append(record: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(record) + "\n")

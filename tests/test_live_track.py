"""Tests for backtest.live_track — synthetic data only (no cache dependency)."""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import live_track as lt


def _port(hist):
    return {"history": hist}


def _h(date, mark_date, value):
    return {"date": date, "mark_date": mark_date, "value": value}


def test_daily_marks_dedupes_carried_marks_last_wins():
    p = _port([
        _h("2026-01-02", "2026-01-01", 1000.0),
        _h("2026-01-03", "2026-01-01", 1001.0),  # carried/corrected mark, same day
        _h("2026-01-04", "2026-01-03", 1010.0),
    ])
    m = lt.daily_marks(p)
    assert list(m) == ["2026-01-01", "2026-01-03"]
    assert m["2026-01-01"] == 1001.0


def test_monthly_checkpoints_excludes_in_progress_month():
    p = _port([
        _h("a", "2026-01-31", 1000.0),
        _h("b", "2026-02-27", 1020.0),
        _h("c", "2026-03-31", 1030.0),
        _h("d", "2026-04-10", 1035.0),  # April in progress
    ])
    spy = {"2026-01-31": 100.0, "2026-02-27": 101.0, "2026-03-31": 103.0,
           "2026-04-10": 104.0}
    cps = lt.monthly_checkpoints(p, spy, baseline_date="2026-01-31")
    months = [c["month"] for c in cps]
    assert months == ["2026-02", "2026-03"]
    feb = cps[0]
    assert math.isclose(feb["port_ret"], 0.02)
    assert math.isclose(feb["spy_ret"], 0.01)
    assert feb["beat"] is True


def test_consecutive_beats_counts_from_end():
    cps = [{"beat": True}, {"beat": False}, {"beat": True}, {"beat": True}]
    assert lt.consecutive_beats(cps) == 2
    assert lt.consecutive_beats([{"beat": False}]) == 0
    assert lt.consecutive_beats([]) == 0


def test_worst_drawdown():
    p = _port([
        _h("a", "2026-01-01", 1000.0),
        _h("b", "2026-01-02", 1100.0),
        _h("c", "2026-01-03", 990.0),   # -10% from 1100 peak
        _h("d", "2026-01-04", 1200.0),
    ])
    dd = lt.worst_drawdown(p, baseline_date="2026-01-01")
    assert math.isclose(dd, 990.0 / 1100.0 - 1.0, rel_tol=1e-9)


def test_min_trl_infinite_when_no_edge():
    # zero-mean alternating returns -> SR <= 0 -> infinite requirement
    rets = [0.01, -0.01] * 30
    assert lt.min_track_record_length(rets) == float("inf")


def test_min_trl_finite_and_shrinks_with_stronger_edge():
    import random
    random.seed(7)
    weak = [random.gauss(0.0004, 0.01) for _ in range(500)]
    strong = [random.gauss(0.002, 0.01) for _ in range(500)]
    m_weak = lt.min_track_record_length(weak)
    m_strong = lt.min_track_record_length(strong)
    assert m_strong < m_weak
    assert m_strong > 1


def test_min_trl_matches_normal_case_formula():
    # For near-normal returns with known SR, compare against the closed form
    # with g3=0, g4=3: MinTRL = 1 + (1 + SR^2/2) (z/SR)^2
    import random
    random.seed(11)
    xs = [random.gauss(0.001, 0.01) for _ in range(5000)]
    n = len(xs)
    mu = sum(xs) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))
    sr = mu / sd
    z = 1.6449  # 95%
    expected = 1 + (1 + sr * sr / 2) * (z / sr) ** 2
    got = lt.min_track_record_length(xs)
    assert abs(got - expected) / expected < 0.10  # loose: skew/kurt noise


def test_summary_scoreboard_shape_and_criteria():
    p = _port([
        _h("a", "2026-01-31", 1000.0),
        _h("b", "2026-02-27", 1020.0),
        _h("c", "2026-03-31", 1050.0),
        _h("d", "2026-04-30", 1080.0),
        _h("e", "2026-05-15", 1090.0),
    ])
    spy = {"2026-01-31": 100.0, "2026-02-27": 101.0, "2026-03-31": 102.0,
           "2026-04-30": 103.0, "2026-05-15": 104.0}
    s = lt.summary(p, spy, baseline_date="2026-01-31", required_months=3)
    assert s["completed_months"] == 3
    assert s["consecutive_beat_months"] == 3
    assert s["criterion2_pass"] is True
    assert s["criterion3_pass"] is True  # monotone up, dd = 0 > -0.20
    assert s["live_obs"] == 5

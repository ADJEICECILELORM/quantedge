# backtest/validation.py
"""
Statistical validation suite: is the backtest's Sharpe real, and what
does the trade sequence look like under re-sampling?

- probabilistic_sharpe_ratio: probability that observed SR > SR* given
  sample size, skew and kurtosis (Bailey & Lopez de Prado, 2012).
- deflated_sharpe_ratio: PSR against the expected maximum Sharpe from
  N strategy trials, which accounts for multiple-testing bias.
- bootstrap_trade_outcomes: Monte Carlo re-sampling of the trade PnL
  sequence to build a max-drawdown / ruin distribution.
"""
import math
from statistics import NormalDist

import numpy as np

_EULER_GAMMA = 0.5772156649015329


def _as_finite_float_array(values):
    arr = np.asarray(list(values), dtype=float)
    return arr[np.isfinite(arr)]


def probabilistic_sharpe_ratio(returns, sr_benchmark: float = 0.0) -> float:
    """
    PSR(SR*) in [0, 1]: probability the true per-period Sharpe exceeds
    sr_benchmark, correcting for estimator variance from skew/kurtosis.
    """
    r = _as_finite_float_array(returns)
    n = len(r)
    if n < 3:
        return float("nan")
    std = float(r.std(ddof=1))
    if std == 0:
        return float("nan")
    sr = float(r.mean() / std)

    skew = float(np.mean(((r - r.mean()) / std) ** 3))
    kurt = float(np.mean(((r - r.mean()) / std) ** 4))
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 0:
        return 1.0 if sr > sr_benchmark else 0.0
    z = (sr - sr_benchmark) * math.sqrt(n - 1) / math.sqrt(denom)
    return float(NormalDist().cdf(z))


def expected_max_sharpe(n_trials: int, sr_std: float) -> float:
    """
    Expected maximum per-period Sharpe among n_trials independent
    strategies whose SR estimates have std sr_std (Extreme Value Theory
    approximation from Bailey & Lopez de Prado, 2014).
    """
    if n_trials < 2 or sr_std <= 0:
        return 0.0
    nd = NormalDist()
    term1 = (1.0 - _EULER_GAMMA) * nd.inv_cdf(1.0 - 1.0 / n_trials)
    term2 = _EULER_GAMMA * nd.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return float(sr_std * (term1 + term2))


def deflated_sharpe_ratio(returns, sr_trials=None, n_trials: int = None, sr_std: float = 0.0) -> float:
    """
    DSR: PSR evaluated against the expected Sharpe of the best of N
    candidate strategies. Supply either the per-trial Sharpe estimates
    (sr_trials, from walk-forward/backtest runs of each variant) or the
    number of trials plus their SR standard deviation. With n_trials=1
    (single strategy, no selection bias) the benchmark is zero and DSR
    equals the plain PSR.
    """
    if sr_trials is not None:
        trials = _as_finite_float_array(sr_trials)
        if len(trials) < 2:
            raise ValueError("sr_trials needs at least 2 Sharpe estimates")
        n_trials = len(trials)
        sr_std = float(trials.std(ddof=1))
    elif n_trials is None:
        raise ValueError("Provide sr_trials or n_trials")

    benchmark = expected_max_sharpe(n_trials, sr_std)
    return probabilistic_sharpe_ratio(returns, sr_benchmark=benchmark)


def bootstrap_trade_outcomes(
    trades_df,
    initial_equity: float,
    n_paths: int = 10000,
    ruin_drawdown_pct: float = 50.0,
    seed=None,
) -> dict:
    """
    IID bootstrap of the trade PnL sequence. Returns the distribution of
    max drawdown and terminal equity across n_paths re-sampled paths.
    """
    pnl = np.asarray(trades_df["pnl_usd"], dtype=float)
    pnl = pnl[np.isfinite(pnl)]
    if len(pnl) == 0:
        return {}

    rng = np.random.default_rng(seed)
    sample = rng.choice(pnl, size=(n_paths, len(pnl)), replace=True)
    paths = initial_equity + np.cumsum(sample, axis=1)
    peaks = np.maximum.accumulate(paths, axis=1)
    drawdown_frac = (paths - peaks) / np.maximum(peaks, 1e-12)
    max_dd_pct = np.abs(drawdown_frac.min(axis=1)) * 100.0
    final = paths[:, -1]

    return {
        "n_paths": int(n_paths),
        "n_trades_resampled": int(len(pnl)),
        "max_dd_p50": float(np.percentile(max_dd_pct, 50)),
        "max_dd_p90": float(np.percentile(max_dd_pct, 90)),
        "max_dd_p95": float(np.percentile(max_dd_pct, 95)),
        "max_dd_p99": float(np.percentile(max_dd_pct, 99)),
        "prob_maxdd_exceeds_20pct": float((max_dd_pct >= 20.0).mean()),
        "prob_ruin": float((max_dd_pct >= ruin_drawdown_pct).mean()),
        "end_equity_p05": float(np.percentile(final, 5)),
        "end_equity_p50": float(np.percentile(final, 50)),
        "prob_profit": float((final > initial_equity).mean()),
    }


def robustness_report(
    trades_df,
    initial_equity: float,
    returns=None,
    n_paths: int = 10000,
    ruin_drawdown_pct: float = 50.0,
    sr_trials=None,
    seed=None,
) -> dict:
    report = bootstrap_trade_outcomes(
        trades_df,
        initial_equity,
        n_paths=n_paths,
        ruin_drawdown_pct=ruin_drawdown_pct,
        seed=seed,
    )
    if report:
        if returns is not None:
            report["psr"] = probabilistic_sharpe_ratio(returns)
        if sr_trials is not None:
            report["dsr"] = deflated_sharpe_ratio(returns, sr_trials=sr_trials)
    return report


def format_robustness_report(report: dict, symbol: str = "") -> str:
    header = f"{'='*50}\nROBUSTNESS REPORT {symbol}\n{'='*50}"
    if not report:
        return f"{header}\nNo trades to validate.\n"
    lines = [header, "  Monte Carlo bootstrap of trade sequence:"]
    rows = [
        ("max_dd_p50", "  Max drawdown p50", "{:.2f}%"),
        ("max_dd_p90", "  Max drawdown p90", "{:.2f}%"),
        ("max_dd_p95", "  Max drawdown p95", "{:.2f}%"),
        ("max_dd_p99", "  Max drawdown p99", "{:.2f}%"),
        ("prob_maxdd_exceeds_20pct", "  P(DD > 20%)", "{:.1%}"),
        ("prob_ruin", "  P(ruin: DD > ruin level)", "{:.1%}"),
        ("end_equity_p05", "  End equity p05", "${:.2f}"),
        ("end_equity_p50", "  End equity median", "${:.2f}"),
        ("prob_profit", "  P(profitable)", "{:.1%}"),
    ]
    for key, label, fmt in rows:
        if key in report:
            lines.append(f"{label:<28}: {fmt.format(report[key])}")
    if "psr" in report and report["psr"] == report["psr"]:
        lines.append(f"  {'Probabilistic Sharpe (PSR)':<28}: {report['psr']:.1%}")
        verdict = "real edge" if report["psr"] >= 0.95 else "NOT distinguishable from luck"
        lines.append(f"  {'PSR verdict (>=95%)':<28}: {verdict}")
    if "dsr" in report and report["dsr"] == report["dsr"]:
        lines.append(f"  {'Deflated Sharpe (multi-trial)':<28}: {report['dsr']:.1%}")
    lines.append("=" * 50)
    return "\n".join(lines)

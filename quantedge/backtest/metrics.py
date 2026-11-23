# backtest/metrics.py
import numpy as np
import pandas as pd


def max_drawdown_pct(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    return float(abs(drawdown.min()) * 100)


def compute_metrics(equity: pd.Series, trades: pd.DataFrame, bars_per_year: int = 28800) -> dict:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return {}

    returns = equity.pct_change().dropna()
    total_return_pct = float((equity.iloc[-1] / equity.iloc[0] - 1) * 100)

    mean_r = float(returns.mean())
    std_r = float(returns.std())

    sharpe = 0.0
    if std_r > 0:
        sharpe = float(mean_r / std_r * np.sqrt(bars_per_year))

    downside = returns[returns < 0]
    downside_std = float(downside.std()) if len(downside) > 0 else 0.0
    sortino = 0.0
    if downside_std > 0:
        sortino = float(mean_r / downside_std * np.sqrt(bars_per_year))

    metrics = {
        "start_equity": float(equity.iloc[0]),
        "end_equity": float(equity.iloc[-1]),
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown_pct(equity),
        "sharpe": sharpe,
        "sortino": sortino,
        "n_trades": int(len(trades)),
    }

    if len(trades) > 0:
        pnl = trades["pnl_usd"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl <= 0]
        metrics["win_rate_pct"] = float(len(wins) / len(pnl) * 100)
        metrics["avg_trade_pnl_usd"] = float(pnl.mean())
        total_win = float(wins.sum())
        total_loss = float(abs(losses.sum()))
        metrics["profit_factor"] = (total_win / total_loss) if total_loss > 0 else float("inf")
    else:
        metrics["win_rate_pct"] = 0.0
        metrics["avg_trade_pnl_usd"] = 0.0
        metrics["profit_factor"] = 0.0

    return metrics


def format_report(metrics: dict, symbol: str = "") -> str:
    header = f"{'='*50}\nBACKTEST REPORT {symbol}\n{'='*50}"
    if not metrics:
        return f"{header}\nNo results.\n"
    lines = [header]
    key_labels = [
        ("start_equity", "Start equity", "${:.2f}"),
        ("end_equity", "End equity", "${:.2f}"),
        ("total_return_pct", "Total return", "{:+.2f}%"),
        ("max_drawdown_pct", "Max drawdown", "{:.2f}%"),
        ("sharpe", "Sharpe (annualized)", "{:.2f}"),
        ("sortino", "Sortino (annualized)", "{:.2f}"),
        ("n_trades", "Trades", "{:d}"),
        ("win_rate_pct", "Win rate", "{:.1f}%"),
        ("avg_trade_pnl_usd", "Avg trade P&L", "${:.2f}"),
        ("profit_factor", "Profit factor", "{:.2f}"),
    ]
    for key, label, fmt in key_labels:
        if key in metrics:
            value = metrics[key]
            if key == "profit_factor" and value == float("inf"):
                lines.append(f"  {label:<22}: inf")
            else:
                lines.append(f"  {label:<22}: {fmt.format(value)}")
    lines.append("=" * 50)
    return "\n".join(lines)

# run_backtest.py
import argparse
import os
import sys
from datetime import datetime

from utils.config import load_config, resolve_timeframe
from backtest.data_loader import load_csv_history, load_mt5_history
from backtest.engine import BacktestEngine
from backtest.metrics import format_report


def parse_args():
    parser = argparse.ArgumentParser(description="QuantEdge backtest runner")
    parser.add_argument("--config", default=None, help="Path to config.json")
    parser.add_argument("--symbol", default=None, help="MT5 base symbol (requires --mt5)")
    parser.add_argument("--mt5", action="store_true", help="Fetch data from a running MT5 terminal")
    parser.add_argument("--csv", default=None, help="Path to CSV with time/open/high/low/close/tick_volume")
    parser.add_argument("--mt5-symbol", default=None, help="Override resolved MT5 symbol name")
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD (mt5 mode)")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD (mt5 mode)")
    parser.add_argument("--equity", type=float, default=None, help="Starting equity override")
    parser.add_argument("--save-trades", default=None, help="Optional CSV path to save trade list")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)

    if args.mt5:
        from utils.mt5_connector import MT5Connector

        symbol = args.symbol or (config["symbols"]["forex"] + config["symbols"]["metals"])[0]
        connector = MT5Connector()
        if not connector.connect():
            sys.exit("MT5 connection failed")
        resolved = args.mt5_symbol or connector.resolve_symbol(symbol) or symbol
        timeframe = resolve_timeframe(config["timeframe"])
        start = datetime.fromisoformat(args.start) if args.start else datetime(2020, 1, 1)
        end = datetime.fromisoformat(args.end) if args.end else datetime.now()
        df = load_mt5_history(connector, resolved, timeframe, start, end)
        symbol_name = resolved
    elif args.csv:
        df = load_csv_history(args.csv)
        symbol_name = os.path.splitext(os.path.basename(args.csv))[0]
    else:
        sys.exit("Provide either --csv PATH or --mt5 --symbol SYMBOL")

    engine = BacktestEngine(df, symbol=symbol_name, config=config, initial_equity=args.equity)
    result = engine.run()
    print(format_report(result.metrics, symbol_name))

    if result.trades is not None and len(result.trades) > 0:
        from backtest.validation import format_robustness_report, robustness_report
        bt_cfg = config["backtest"]
        returns = result.equity_curve.pct_change().dropna()
        report = robustness_report(
            result.trades,
            engine.initial_equity,
            returns=returns,
            n_paths=int(bt_cfg.get("mc_paths", 10000)),
            ruin_drawdown_pct=float(bt_cfg.get("ruin_drawdown_pct", 50.0)),
            seed=7,
        )
        print(format_robustness_report(report, symbol_name))

    if args.save_trades and result.trades is not None and len(result.trades) > 0:
        result.trades.to_csv(args.save_trades, index=False)
        print(f"Trades saved to {args.save_trades}")

    if result.metrics.get("max_drawdown_pct", 999) > 20:
        print("\n⚠️  Max drawdown exceeds 20% - do not deploy this strategy as configured")


if __name__ == "__main__":
    main()

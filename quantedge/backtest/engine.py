# backtest/engine.py
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from features.feature_engineer import FeatureEngineer
from risk.drawdown_guard import DrawdownGuard
from utils.config import load_config
from backtest.metrics import compute_metrics, infer_bars_per_year

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    entry_bar: int
    exit_bar: Optional[int]
    entry_price: float
    exit_price: Optional[float]
    direction: int
    stop_loss: float
    take_profit: float
    units: float
    pnl_usd: float = 0.0
    status: str = "open"


@dataclass
class BacktestResult:
    equity_curve: pd.Series = None
    trades: pd.DataFrame = None
    metrics: dict = field(default_factory=dict)
    initial_equity: float = 0.0


class BacktestEngine:
    """
    Bar-by-bar backtest that reuses the live trading code paths.

    Features are computed once with FeatureEngineer (all indicators are
    causal: rolling/shift/ewm on past data only), and one row at a time is
    fed to the same InferencePipeline used live. Fills are modeled with
    spread, slippage and per-lot commission. Entries happen at the NEXT
    bar's open so no bar trades on its own close. Longs buy at ask
    (open + spread + slippage) and shorts sell at bid (open - spread -
    slippage); stop and take-profit checks are direction-aware.

    Notional model: position_size_usd of risk per trade, converted to asset
    units of (risk_amount / sl_distance). PnL = units * (exit - entry) *
    direction.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        symbol: str = "SYNTH",
        config: dict = None,
        inference=None,
        initial_equity: float = None,
    ):
        self.config = config or load_config()
        self.bt_cfg = self.config["backtest"]
        self.symbol = symbol
        self.df = df.sort_values("time").reset_index(drop=True).copy()
        self.inference = inference
        self.initial_equity = (
            initial_equity
            if initial_equity is not None
            else float(self.config["account"]["balance"])
        )

        self.warmup_bars = int(self.bt_cfg["warmup_bars"])
        self.spread_fraction = float(self.bt_cfg["spread_fraction"])
        self.slippage_fraction = float(self.bt_cfg["slippage_fraction"])
        self.commission_per_lot = float(self.bt_cfg["commission_per_lot_usd"])
        self.atr_sl_multiple = float(self.bt_cfg["atr_sl_multiple"])
        self.atr_tp_multiple = float(self.bt_cfg["atr_tp_multiple"])
        self.risk_per_trade = float(self.config["account"]["risk_per_trade"])
        self.min_confidence = float(self.bt_cfg.get("min_confidence", 0.55))
        # Optional regime gate: 0 disables (default), else require ADX >= value
        self.min_adx = float(self.bt_cfg.get("min_adx", 0.0))

    def _get_inference(self):
        if self.inference is not None:
            return self.inference
        from pipeline.inference_pipeline import InferencePipeline
        try:
            pipeline = InferencePipeline()
        except Exception as e:
            logger.warning(f"No trained models found ({e}) - engine runs with a neutral stub (no trades)")
            return None
        if not getattr(pipeline, "models", None):
            logger.warning("InferencePipeline has no models - engine runs with a neutral stub (no trades)")
            return None
        return pipeline

    @staticmethod
    def _stub_predict(row_df):
        return {"direction": 0, "confidence": 0.5, "model_votes": {}}

    def run(self) -> BacktestResult:
        fe = FeatureEngineer()
        features = fe.create_features(self.df)
        if len(features) == 0:
            raise ValueError("Feature generation produced an empty DataFrame")
        features = features.reset_index(drop=True)

        n = len(features)
        if n <= self.warmup_bars + 2:
            raise ValueError(
                f"Not enough bars: {n} available, need >{self.warmup_bars + 2}"
            )

        inference = self._get_inference()
        if inference is None:
            logger.warning("No trained models found - engine runs with a neutral stub (no trades)")

        predict = inference.predict if inference is not None else self._stub_predict
        guard = DrawdownGuard(self.initial_equity, self.bt_cfg.get("max_daily_loss_percent", 5.0))

        equity = self.initial_equity
        equity_curve = np.full(n, np.nan)
        equity_curve[: self.warmup_bars] = equity
        open_trade: Optional[Trade] = None
        trades: list = []
        stopped = False
        current_day = None

        for i in range(self.warmup_bars, n - 1):
            bar = features.iloc[i]
            next_bar = features.iloc[i + 1]

            bar_day = bar["time"].date() if "time" in features.columns else None
            if bar_day is not None and bar_day != current_day:
                current_day = bar_day
                if stopped:
                    stopped = False
                guard.reset_daily(equity)

            equity_curve[i] = equity + self._unrealized_pnl(open_trade, i, bar)

            if open_trade is not None:
                exited, exit_price, exit_kind = self._check_exit(open_trade, bar)
                if exited:
                    open_trade.exit_bar = i
                    open_trade.exit_price = exit_price
                    open_trade.pnl_usd = self._pnl(open_trade)
                    open_trade.status = exit_kind
                    equity += open_trade.pnl_usd
                    trades.append(open_trade)
                    open_trade = None

            if not stopped and guard.check_status(equity):
                logger.warning(f"Kill switch triggered at bar {i} - backtest stops trading")
                stopped = True

            if open_trade is None and not stopped:
                prediction = predict(features.iloc[[i]])
                direction = prediction.get("direction", 0)
                confidence = float(prediction.get("confidence", 0.5))

                if direction == 0 or confidence < self.min_confidence:
                    continue

                atr = bar.get("atr_14")
                if atr is None or not np.isfinite(atr) or atr <= 0:
                    continue

                if self.min_adx > 0:
                    adx = bar.get("adx")
                    if adx is None or not np.isfinite(adx) or adx < self.min_adx:
                        continue

                raw_price = float(next_bar["open"])
                spread = self.spread_fraction * raw_price
                slip = self.slippage_fraction * raw_price
                if direction == 1:
                    entry_price = raw_price + spread + slip
                else:
                    entry_price = raw_price - spread - slip

                sl_distance = atr * self.atr_sl_multiple
                units = (equity * self.risk_per_trade) / sl_distance

                commission = self.commission_per_lot * (units / 100000.0)
                equity -= commission

                open_trade = Trade(
                    entry_bar=i + 1,
                    exit_bar=None,
                    entry_price=entry_price,
                    exit_price=None,
                    direction=int(direction),
                    stop_loss=(
                        entry_price - sl_distance
                        if direction == 1
                        else entry_price + sl_distance
                    ),
                    take_profit=(
                        entry_price + atr * self.atr_tp_multiple
                        if direction == 1
                        else entry_price - atr * self.atr_tp_multiple
                    ),
                    units=units,
                )

        if open_trade is not None:
            open_trade.exit_bar = n - 1
            open_trade.exit_price = float(features.iloc[-1]["close"])
            open_trade.pnl_usd = self._pnl(open_trade)
            open_trade.status = "eod"
            equity += open_trade.pnl_usd
            trades.append(open_trade)

        equity_curve[n - 1] = equity

        trades_df = pd.DataFrame([t.__dict__ for t in trades])
        equity_series = pd.Series(equity_curve, index=features["time"][:n])

        return BacktestResult(
            equity_curve=equity_series,
            trades=trades_df,
            metrics=compute_metrics(
                equity_series,
                trades_df,
                infer_bars_per_year(features["time"]),
            ),
            initial_equity=self.initial_equity,
        )

    @staticmethod
    def _check_exit(trade: Trade, bar) -> tuple:
        low = float(bar["low"])
        high = float(bar["high"])
        if trade.direction == 1:
            if low <= trade.stop_loss:
                return True, trade.stop_loss, "sl"
            if high >= trade.take_profit:
                return True, trade.take_profit, "tp"
        else:
            if high >= trade.stop_loss:
                return True, trade.stop_loss, "sl"
            if low <= trade.take_profit:
                return True, trade.take_profit, "tp"
        return False, None, ""

    @staticmethod
    def _unrealized_pnl(trade: Optional[Trade], bar_index: int, bar) -> float:
        if trade is None or bar_index < trade.entry_bar:
            return 0.0
        close = float(bar["close"])
        return float(trade.units * (close - trade.entry_price) * trade.direction)

    def _pnl(self, trade: Trade) -> float:
        if trade.exit_price is None:
            return 0.0
        return float(trade.units * (trade.exit_price - trade.entry_price) * trade.direction)

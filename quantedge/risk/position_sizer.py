# risk/position_sizer.py
import MetaTrader5 as mt5


class QuantPositionSizer:
    def __init__(self, account_balance, risk_per_trade=0.02, max_lot_cap=1.0):
        self.balance = account_balance
        self.risk_per_trade = risk_per_trade
        self.max_lot_cap = max_lot_cap

    def refresh_balance(self, live_balance: float = None):
        """
        Sync sizing with live account equity.

        Pass the balance explicitly, or if called while connected to MT5 with
        no argument, reads live equity from the terminal. Keeps a stale
        snapshot from manipulating position sizes after wins/losses.
        """
        if live_balance is None:
            info = mt5.account_info()
            if info is None:
                return self.balance
            live_balance = info.equity
        if live_balance and live_balance > 0:
            self.balance = float(live_balance)
        return self.balance

    def calculate_lot_size(self, symbol, entry_price, stop_loss_price, current_atr, use_live_equity: bool = True):
        if use_live_equity:
            self.refresh_balance()

        price_diff = abs(entry_price - stop_loss_price)
        if price_diff == 0: return 0.01

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None: return 0.01

        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        lot_step = symbol_info.volume_step
        min_lot = symbol_info.volume_min
        max_lot = symbol_info.volume_max

        point_value = tick_value / tick_size
        risk_amount = self.balance * self.risk_per_trade

        # Volatility Scaling
        current_vol = (current_atr / entry_price)
        target_vol = 0.0015
        vol_scalar = target_vol / current_vol if current_vol > 0 else 1.0
        vol_scalar = min(max(vol_scalar, 0.5), 2.0)

        adjusted_risk = risk_amount * vol_scalar
        lot_size = adjusted_risk / (price_diff * point_value)

        lot_size = round(lot_size / lot_step) * lot_step

        if lot_size > self.max_lot_cap:
            print(f"⚠️ Safety Cap Triggered. Calculated {lot_size}, reduced to {self.max_lot_cap}")
            lot_size = self.max_lot_cap

        if lot_size < min_lot:
            lot_size = min_lot
        if lot_size > max_lot:
            lot_size = max_lot

        return lot_size

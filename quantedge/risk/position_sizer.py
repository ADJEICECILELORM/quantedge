# risk/position_sizer.py
import MetaTrader5 as mt5

class QuantPositionSizer:
    def __init__(self, account_balance, risk_per_trade=0.02):
        self.balance = account_balance
        self.risk_per_trade = risk_per_trade

    def calculate_lot_size(self, symbol, entry_price, stop_loss_price, current_atr):
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
        
        # ---------------------------------------------------------
        # SAFETY CAP (PREVENTS HUGE GOLD TRADES)
        # ---------------------------------------------------------
        max_lot_cap = 1.0 # Never trade more than 1.0 Lot
        if lot_size > max_lot_cap:
            print(f"⚠️ Safety Cap Triggered. Calculated {lot_size}, reduced to {max_lot_cap}")
            lot_size = max_lot_cap
        # ---------------------------------------------------------

        if lot_size < min_lot:
            lot_size = min_lot
        if lot_size > max_lot:
            lot_size = max_lot
            
        return lot_size
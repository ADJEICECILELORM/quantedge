# missing_modules_fix.py
import os

# 1. Create Folders and Markers
folders = ["risk", "pipeline"]
for f in folders:
    if not os.path.exists(f):
        os.makedirs(f)
    with open(f"{f}/__init__.py", "w") as file:
        file.write("")
print("✅ Folders and markers created.")

# 2. Create risk/position_sizer.py
with open("risk/position_sizer.py", "w") as f:
    f.write("""
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
        if lot_size < min_lot: lot_size = min_lot
        if lot_size > max_lot: lot_size = max_lot
        return lot_size
""")
print("✅ Created risk/position_sizer.py")

# 3. Create utils/order_executor.py
with open("utils/order_executor.py", "w") as f:
    f.write("""
import MetaTrader5 as mt5

class OrderExecutor:
    def __init__(self):
        if not mt5.initialize(): print("Order Executor: Init Failed")

    def send_order(self, symbol, signal, lot, sl, tp):
        if lot <= 0: return False
        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None: return False
        price = symbol_info.ask if signal == 1 else symbol_info.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol, "volume": lot,
            "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL,
            "price": price, "sl": sl, "tp": tp, "deviation": 20,
            "magic": 234000, "comment": "QuantEdge V2",
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Order Failed: {result.retcode}")
            return False
        return True
""")
print("✅ Created utils/order_executor.py")

# 4. Create pipeline/inference_pipeline.py
# This loads the RF, XGB, LR models we just trained
with open("pipeline/inference_pipeline.py", "w") as f:
    f.write("""
import joblib
import pandas as pd
import numpy as np

class InferencePipeline:
    def __init__(self):
        print("Loading Models...")
        self.scaler = joblib.load("models/saved/scaler.pkl")
        self.models = {
            'rf': joblib.load("models/saved/rf_model.pkl"),
            'xgb': joblib.load("models/saved/xgb_model.pkl"),
            'lr': joblib.load("models/saved/lr_model.pkl")
        }
        print("Models Loaded.")
        self.weights = {'rf': 0.40, 'xgb': 0.47, 'lr': 0.13}

    def predict(self, latest_features_df):
        exclude_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'target', 'regime_label']
        feature_cols = [c for c in latest_features_df.columns if c not in exclude_cols]
        X = latest_features_df[feature_cols]
        
        try:
            X_scaled = self.scaler.transform(X)
        except Exception as e:
            print(f"Scaling Error: {e}")
            return {'direction': 0, 'confidence': 0.5}

        predictions = {}
        for name, model in self.models.items():
            try:
                proba = model.predict_proba(X_scaled)[0]
                predictions[name] = {
                    'prob_long': proba[1],
                    'vote': 1 if proba[1] > 0.5 else -1,
                    'confidence': max(proba)
                }
            except: predictions[name] = {'vote': 0, 'confidence': 0.5} 
        
        score_long = sum(p['prob_long'] * p['confidence'] * self.weights[name] for name, p in predictions.items() if p['vote'] == 1)
        score_short = sum((1 - p['prob_long']) * p['confidence'] * self.weights[name] for name, p in predictions.items() if p['vote'] == -1)
        
        total_weight = sum(self.weights.values())
        if score_long > score_short:
            return {'direction': 1, 'confidence': score_long / total_weight}
        else:
            return {'direction': -1, 'confidence': score_short / total_weight}
""")
print("✅ Created pipeline/inference_pipeline.py")

print("\n🔧 All missing modules installed!")
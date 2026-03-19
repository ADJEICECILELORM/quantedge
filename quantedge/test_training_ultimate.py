# test_training_ultimate.py
import sys
sys.path.append('.')
from utils.mt5_connector import MT5Connector
from features.feature_engineer import FeatureEngineer
from features.label_generator import LabelGenerator
from models.model_trainer import ModelTrainer
import MetaTrader5 as mt5

print("--- QuantEdge Ultimate V2.0 Training (Robust) ---")

# 1. Connect
mt5_conn = MT5Connector()
mt5_conn.connect()

# 2. Fetch Data (Robust Mode: Try everything, accept what works)
print("Fetching Data...")
df_eur = mt5_conn.get_historical_data("EURUSD", mt5.TIMEFRAME_M5, bars=5000)
df_btc = mt5_conn.get_historical_data("BTCUSD", mt5.TIMEFRAME_M5, bars=5000)
df_eth = mt5_conn.get_historical_data("ETHUSD", mt5.TIMEFRAME_M5, bars=5000)
df_gold = mt5_conn.get_historical_data("XAUUSD", mt5.TIMEFRAME_M5, bars=5000)

# 3. Validate Main Data
if df_eur is None:
    print("❌ CRITICAL: Could not fetch EURUSD. Check MT5 connection.")
    exit()

# 4. Log Sentiment Status
if df_btc is None: print("⚠️  BTCUSD not found. Training without Crypto Sentiment.")
else: print("✅ BTCUSD Loaded.")

if df_eth is None: print("⚠️  ETHUSD not found. Training without ETH Sentiment.")
else: print("✅ ETHUSD Loaded.")

if df_gold is None: print("⚠️  XAUUSD not found. Training without Macro Gold.")
else: print("✅ XAUUSD Loaded.")

# 5. Engineer Features (All-in-One)
# We pass all data. FeatureEngineer handles 'None' gracefully.
print("Engineering Ultimate Features...")
fe = FeatureEngineer()
df = fe.create_features(df_eur, df_crypto=df_btc, df_eth=df_eth, df_gold=df_gold)

# 6. Labels
lg = LabelGenerator(forward_bars=5, vol_multiple=0.5)
df = lg.create_labels(df)
print(f"Final Dataset Size: {len(df)}")

# 7. Train
trainer = ModelTrainer(df)
trainer.train_models()
trainer.save_models()

mt5_conn.shutdown()
print("--- Training Complete ---")
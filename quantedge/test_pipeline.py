# test_training.py
import sys
sys.path.append('.')
from utils.mt5_connector import MT5Connector
from features.feature_engineer import FeatureEngineer
from features.label_generator import LabelGenerator
from models.model_trainer import ModelTrainer
import MetaTrader5 as mt5

print("--- Starting Training Pipeline ---")

# 1. Get Data
mt5_conn = MT5Connector()
mt5_conn.connect()
df = mt5_conn.get_historical_data("EURUSD", mt5.TIMEFRAME_M5, bars=5000)

if df is not None:
    # 2. Engineer Features
    fe = FeatureEngineer()
    df = fe.create_features(df)
    
    # 3. Generate Labels
    lg = LabelGenerator(forward_bars=5, vol_multiple=0.5)
    df = lg.create_labels(df)
    
    # 4. Train Models
    trainer = ModelTrainer(df)
    trainer.train_models()
    
    # 5. Save Models
    trainer.save_models()

mt5_conn.shutdown()
print("--- Training Complete ---")
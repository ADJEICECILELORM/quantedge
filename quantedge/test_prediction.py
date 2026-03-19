# test_prediction.py
import sys
sys.path.append('.')
from utils.mt5_connector import MT5Connector
from features.feature_engineer import FeatureEngineer
from pipeline.inference_pipeline import InferencePipeline
import MetaTrader5 as mt5

print("--- Starting Live Prediction ---")

# 1. Initialize the Brain
inference = InferencePipeline()

# 2. Get Live Data
mt5_conn = MT5Connector()
mt5_conn.connect()

# We need ~200 bars to calculate indicators (like SMA50, ATR)
print("Fetching latest bars...")
df = mt5_conn.get_latest_bars("EURUSD", mt5.TIMEFRAME_M5, count=200)

if df is not None and len(df) > 50:
    # 3. Engineer Features
    print("Calculating features...")
    fe = FeatureEngineer()
    df_features = fe.create_features(df)
    
    # Get the LAST row (Current Candle)
    current_data = df_features.iloc[[-1]]
    
    print(f"Current Time: {current_data['time'].values[0]}")
    print(f"Current Price: {current_data['close'].values[0]}")
    
    # 4. PREDICT
    result = inference.predict(current_data)
    
    # 5. Print Result
    print("\n" + "="*30)
    print(f"   SIGNAL: {result['direction']}")
    print(f"CONFIDENCE: {result['confidence']:.2f}")
    print("="*30)
    
    if result['direction'] == 1:
        print("DECISION: 🚀 OPEN BUY")
    elif result['direction'] == -1:
        print("DECISION: 🔻 OPEN SELL")
    else:
        print("DECISION: ⏸️ HOLD (Low Confidence)")

else:
    print("Not enough data to predict.")

mt5_conn.shutdown()
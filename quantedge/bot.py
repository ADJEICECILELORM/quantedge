# bot.py
import sys
sys.path.append('.')
import time
import MetaTrader5 as mt5
from utils.mt5_connector import MT5Connector
from features.feature_engineer import FeatureEngineer
from pipeline.inference_pipeline import InferencePipeline
from risk.position_sizer import QuantPositionSizer
from utils.order_executor import OrderExecutor

class QuantEdgeBot:
    def __init__(self):
        self.mt5 = MT5Connector()
        self.fe = FeatureEngineer()
        self.brain = InferencePipeline()
        self.sizer = QuantPositionSizer(account_balance=10000, risk_per_trade=0.02)
        self.hands = OrderExecutor()
        
        # Configuration
        self.symbol = "EURUSD"
        self.timeframe = mt5.TIMEFRAME_M5
        self.atr_multiplier = 1.5 # SL is 1.5x ATR

    def run(self):
        print("🚀 QuantEdge Bot Started. Press Ctrl+C to stop.")
        
        while True:
            try:
                # 1. Get Data
                df = self.mt5.get_latest_bars(self.symbol, self.timeframe, count=200)
                
                if df is not None and len(df) > 50:
                    # 2. Engineer Features
                    df_feat = self.fe.create_features(df)
                    current_bar = df_feat.iloc[[-1]]
                    current_price = current_bar['close'].values[0]
                    current_atr = current_bar['atr_14'].values[0]
                    
                    # 3. Make Prediction
                    result = self.brain.predict(current_bar)
                    signal = result['direction']
                    confidence = result['confidence']
                    
                    print(f"\n[Time: {current_bar['time'].values[0]}] Price: {current_price:.5f} | Signal: {signal} ({confidence:.2f})")

                    # 4. Check if we should trade (High Confidence)
                    if signal != 0 and confidence >= 0.60:
                        
                        # 5. Calculate Stop Loss
                        sl_price = 0
                        if signal == 1: # Buy
                            sl_price = current_price - (current_atr * self.atr_multiplier)
                        else: # Sell
                            sl_price = current_price + (current_atr * self.atr_multiplier)
                            
                        # 6. Calculate Lot Size (Quant Math)
                        lot_size = self.sizer.calculate_lot_size(
                            self.symbol, 
                            current_price, 
                            sl_price, 
                            current_atr
                        )
                        
                        # 7. EXECUTE
                        # Simple TP: 1.5x Risk (Reward)
                        tp_distance = abs(sl_price - current_price) * 1.5
                        tp_price = (current_price + tp_distance) if signal == 1 else (current_price - tp_distance)

                        print(f"🔌 Executing Trade: {signal} Lot: {lot_size} SL: {sl_price}")
                        
                        # WARNING: This will place REAL trades!
                        # Uncomment the line below to enable live trading:
                        # self.hands.send_order(self.symbol, signal, lot_size, sl_price, tp_price)
                        print("🚫 Paper Trading Mode (Safe)")

                else:
                    print("Waiting for data...")
                
                # Wait for next M5 candle (approx 60 seconds check loop)
                time.sleep(60)

            except KeyboardInterrupt:
                print("\n🛑 Bot Stopped by User.")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = QuantEdgeBot()
    bot.run()
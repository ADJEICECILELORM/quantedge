# bot_ultimate.py (Allocator V3.2: Sniper & Relative Strength)
import sys
sys.path.append('.')
import time
import MetaTrader5 as mt5
from utils.mt5_connector import MT5Connector
from features.feature_engineer import FeatureEngineer
from pipeline.inference_pipeline import InferencePipeline
from risk.position_sizer import QuantPositionSizer
from risk.drawdown_guard import DrawdownGuard
from utils.order_executor import OrderExecutor
from utils.position_manager import PositionManager

class QuantEdgeBotAllocator:
    def __init__(self):
        # MANUAL OVERRIDE: Fix Equity Glitch (Force $10k)
        self.account_balance = 10000
        
        self.mt5 = MT5Connector()
        self.fe = FeatureEngineer()
        self.brain = InferencePipeline()
        self.sizer = QuantPositionSizer(account_balance=self.account_balance, risk_per_trade=0.02)
        self.hands = OrderExecutor()
        self.manager = PositionManager() # Manages Breakevens/Trailing
        
        # Drawdown Guard using Manual Override
        self.guard = DrawdownGuard(account_balance=self.account_balance, max_daily_loss_percent=2.0)
        
        # Configuration
        self.watchlist = ["EURUSD", "XAUUSD"]  # Stick to Exness MT5 for now
        self.timeframe = mt5.TIMEFRAME_M5
        self.atr_multiplier = 1.5 

    def get_account_equity(self):
        """Fetch current account equity OR use Manual Override"""
        # acc_info = mt5.account_info()
        # if acc_info: return acc_info.equity
        
        # MANUAL OVERRIDE (Fix Glitch):
        return self.account_balance

    def analyze_asset(self, symbol, df_main, df_sentiment):
        """
        Runs prediction pipeline for a single asset.
        df_main: Data of the asset we are trading (e.g., EURUSD).
        df_sentiment: Data of the 'other' asset (for Macro features).
        """
        # 1. Engineer Features (Using df_sentiment for Macro Strength)
        df_feat = self.fe.create_features(df_main, df_crypto=None, df_eth=None, df_gold=df_sentiment)
        
        # Get LAST row (Current Candle)
        if len(df_feat) == 0: return None
        
        current_bar = df_feat.iloc[[-1]]
        current_price = current_bar['close'].values[0]
        current_atr = current_bar['atr_14'].values[0]
        
        # 2. Make Prediction
        result = self.brain.predict(current_bar)
        signal = result['direction']
        confidence = result['confidence']
        
        return {
            'symbol': symbol,
            'price': current_price,
            'atr': current_atr,
            'signal': signal,
            'confidence': confidence,
            'bar': current_bar
        }

    def run(self):
        print("🚀 QuantEdge Allocator V3.2 (Sniper & Relative Strength) Started.")
        print(f"🛡️ Drawdown Guard Active: Max Loss -{self.guard.max_loss}% of ${self.account_balance}")
        print(f"Assets: {self.watchlist}")
        
        while True:
            try:
                # 0. CHECK DRAWDOWN FIRST (The Safety Valve)
                current_eq = self.get_account_equity()
                self.guard.print_status(current_eq)
                
                if self.guard.check_status(current_eq):
                    # STOP THE BOT
                    print("🛑 Bot Stopped by Drawdown Guard.")
                    break
                
                print(f"\n--- Scanning Market ({time.strftime('%H:%M:%S')}) ---")
                
                # ---------------------------------------------------------
                # 0.5 SNIPER MODE: Check for Triangle Breakout (High Volatility)
                # ---------------------------------------------------------
                print("🔭 Scanning for Triangles...")
                df_eur_sniper = self.mt5.get_latest_bars("EURUSD", self.timeframe, count=50)
                
                is_eur_triangle = False
                if df_eur_sniper is not None:
                    is_eur_triangle = self.fe.detect_triangle(df_eur_sniper)
                
                # If Triangle found, try to Force Trade (Simulated)
                if is_eur_triangle:
                    print("🔺 TRIANGLE DETECTED ON EURUSD!")
                    print("🔺 SNIPER MODE: Waiting for Breakout...")
                    
                    # Simple breakout logic: Is current close > recent high?
                    recent_high = df_eur_sniper['high'].max()
                    current_price_eur = df_eur_sniper['close'].iloc[-1]
                    
                    if current_price_eur > recent_high * 1.0005: # Small breakout
                        print("🚀 BREAKOUT SPOTTED! FORCING SNIPER TRADE.")
                        
                        # We could execute here, but for now we just log.
                        # The Allocator loop will handle the normal trading logic below.
                # ---------------------------------------------------------

                # 1. Fetch Data for ALL assets
                print("Fetching EURUSD...")
                df_eur = self.mt5.get_latest_bars("EURUSD", self.timeframe, count=200)
                print("Fetching XAUUSD (Gold)...")
                df_gold = self.mt5.get_latest_bars("XAUUSD", self.timeframe, count=200)
                
                candidates = []

                # 2. Analyze EURUSD
                if df_eur is not None:
                    # We pass df_gold as sentiment for EURUSD (Macro USD Strength)
                    eur_analysis = self.analyze_asset("EURUSD", df_eur, df_gold)
                    if eur_analysis:
                        candidates.append(eur_analysis)

                # 3. Analyze XAUUSD (Gold)
                if df_gold is not None:
                    # We pass df_eur as sentiment for Gold
                    gold_analysis = self.analyze_asset("XAUUSD", df_gold, df_eur)
                    if gold_analysis:
                        candidates.append(gold_analysis)

                # 4. THE "RELATIVE STRENGTH" LOGIC
                # ---------------------------------------------------------
                if len(candidates) == 2:
                    # PAIRS MODE: Compare Candidates
                    cand1 = candidates[0] # EURUSD
                    cand2 = candidates[1] # XAUUSD
                    
                    print(f"⚖️ Analyzing Pair: {cand1['symbol']} vs {cand2['symbol']}")
                    
                    # Calculate Divergence
                    diff_confidence = cand1['confidence'] - cand2['confidence']
                    diff_signal = cand1['signal'] - cand2['signal'] # If 2, both buy. If -2, both sell.
                    
                    print(f"    Diff Confidence: {diff_confidence:+.2f} | Diff Signal: {diff_signal}")
                    
                    # STRATEGY: Fade the Weak / Ride the Strong
                    # If EUR is Buy (1) and Gold is Neutral/Sell (0/-1), Buy EUR vs Gold
                    
                    if abs(diff_confidence) > 0.10 and abs(diff_signal) > 0:
                        # Strong Divergence Found!
                        # We trade the Stronger one
                        if diff_confidence > 0:
                            # EUR is stronger
                            best_candidate = cand1
                            print(f"✅ PAIRS TRADE: Long {cand1['symbol']} / Short {cand2['symbol']} (Relative Strength)")
                        else:
                            # Gold is stronger (or EUR is weaker)
                            # We might invert, but for safety, we just pick best one
                            best_candidate = cand2
                            print(f"✅ PAIRS TRADE: Long {cand2['symbol']} / Short {cand1['symbol']}")
                            
                elif len(candidates) == 1:
                    # STANDARD MODE: Single Asset
                    best_candidate = candidates[0]
                    print(f"Standard Mode: Trading Single Asset {best_candidate['symbol']}")
                else:
                    print("❌ No data fetched.")
                    continue
                # ---------------------------------------------------------

                # 5. Check Threshold
                if best_candidate['confidence'] >= 0.55:
                    
                    # 6. Calculate Order Details
                    signal = best_candidate['signal']
                    entry = best_candidate['price']
                    atr = best_candidate['atr']
                    sym = best_candidate['symbol']
                    
                    # Stop Loss
                    sl = entry - (atr * self.atr_multiplier) if signal == 1 else entry + (atr * self.atr_multiplier)
                    
                    # Lot Sizing
                    lot = self.sizer.calculate_lot_size(sym, entry, sl, atr)
                    
                    # Take Profit
                    tp_dist = abs(sl - entry) * 1.5
                    tp = entry + tp_dist if signal == 1 else entry - tp_dist

                    print(f"🔌 EXECUTING: {signal} {sym} | Lot: {lot} | SL: {sl}")
                    
                    # PAPER MODE (Safe) - Simulation
                    print("🚫 Paper Trading Mode (Safe)")
                    # UNCOMMENT BELOW FOR LIVE TRADING:
                    # ticket = self.hands.send_order(sym, signal, lot, sl, tp)
                    # if ticket:
                    #     self.manager.add_trade(ticket, sym, entry, sl, tp, signal)
                    
                    # SIMULATION (Allows Manager to print Breakeven logic):
                    fake_ticket = 99999
                    self.manager.add_trade(fake_ticket, sym, entry, sl, tp, signal)
                else:
                    print("⏸️ Confidence < 55%. Holding.")
                
                # 7. MANAGE OPEN TRADES (Breakeven / Trailing)
                # Note: In Paper mode with fake tickets, the manager will calculate logic
                # but actual mt5.order_send() inside manager might fail on fake tickets.
                # That's okay, we just want to see the LOGIC printed.
                self.manager.manage_trades()
                
                time.sleep(60) # Wait 1 minute

            except KeyboardInterrupt:
                print("\n🛑 Bot Stopped by User.")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = QuantEdgeBotAllocator()
    bot.run()
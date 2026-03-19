# bot_v4_ultimate.py - QuantEdge V4: The Ultimate Trading System
"""
QuantEdge V4 - Integrated Advanced Features:
✅ Genetic Algorithm Optimization
✅ Time Machine (Session Filter)
✅ Sniper Mode (High Volatility + News Arbitrage)
✅ NLP Sentiment (BTC-ETH Correlation)
✅ Relim Shield (Dynamic Confidence)
✅ Dynamic Stop Loss (Multi-Strategy)
"""

import sys
sys.path.append('.')
import time
import MetaTrader5 as mt5
from datetime import datetime, timezone

# Core Components
from utils.mt5_connector import MT5Connector
from features.feature_engineer import FeatureEngineer
from pipeline.inference_pipeline import InferencePipeline
from risk.position_sizer import QuantPositionSizer
from risk.drawdown_guard import DrawdownGuard
from utils.order_executor import OrderExecutor
from utils.position_manager import PositionManager

# V4 Features
from time_machine import TimeMachine
from utils.sniper_mode import SniperMode
from features.nlp_sentiment import NLPSentimentAnalyzer
from utils.relim_shield import RelimShield
from utils.dynamic_stop_loss import DynamicStopLoss


class QuantEdgeV4:
    def __init__(self, account_balance=10000, use_manual_balance=False):
        print("🚀 QuantEdge V4 Ultimate - Initializing...")

        self.account_balance = account_balance
        self.use_manual_balance = use_manual_balance

        # Core systems
        self.mt5 = MT5Connector()
        self.fe = FeatureEngineer()
        self.brain = InferencePipeline()
        self.sizer = QuantPositionSizer(account_balance=account_balance, risk_per_trade=0.02)
        self.hands = OrderExecutor()
        self.manager = PositionManager()
        self.guard = DrawdownGuard(account_balance=account_balance, max_daily_loss_percent=2.0)

        # V4 Advanced Systems
        self.time_machine = TimeMachine()
        self.sniper = SniperMode(lookback=50, squeeze_threshold=0.8)
        self.nlp = NLPSentimentAnalyzer()
        # Lower initial threshold to 0.50 for more trades
        self.shield = RelimShield(initial_threshold=0.50, min_threshold=0.45, max_threshold=0.75)
        self.stop_loss_manager = DynamicStopLoss(base_atr_multiplier=1.5)

        # Configuration
        self.forex_pairs = ["EURUSD", "XAUUSD"]  # Forex/Gold (closed on weekends)
        self.crypto_pairs = []  # Crypto pairs (if available in MT5)

        # Auto-detect available crypto symbols
        if self.mt5.connect():
            for crypto_symbol in ["BTCUSD", "ETHUSD", "BTC/USD", "ETH/USD"]:
                if mt5.symbol_info(crypto_symbol) is not None:
                    self.crypto_pairs.append(crypto_symbol)
                    print(f"✅ Crypto pair found: {crypto_symbol}")

        if not self.crypto_pairs:
            print("⚠️ No crypto pairs available in MT5 - using forex only")

        self.watchlist = self.forex_pairs + self.crypto_pairs  # All available pairs
        self.timeframe = mt5.TIMEFRAME_M5

        # Tracking
        self.trades_today = 0
        self.max_trades_per_day = 10

        print("✅ V4 System Initialized Successfully")

    def get_account_equity(self):
        """Get current equity from MT5"""
        if self.use_manual_balance:
            return self.account_balance

        acc_info = mt5.account_info()
        if acc_info and acc_info.equity > 0:
            return acc_info.equity
        # Fallback to manual value
        print(f"⚠️ Using manual balance: ${self.account_balance}")
        return self.account_balance

    def fetch_crypto_data(self):
        """Fetch BTC and ETH data for NLP analysis"""
        df_btc = self.mt5.get_latest_bars("BTCUSD", self.timeframe, count=50)
        df_eth = self.mt5.get_latest_bars("ETHUSD", self.timeframe, count=50)
        return df_btc, df_eth

    def is_crypto_pair(self, symbol: str) -> bool:
        """Check if symbol is a crypto pair"""
        return symbol in self.crypto_pairs

    def analyze_market(self, symbol: str, current_time: datetime):
        """
        Complete market analysis using all V4 features.
        """
        # 1. Fetch data
        df_main = self.mt5.get_latest_bars(symbol, self.timeframe, count=200)
        if df_main is None or len(df_main) < 50:
            return None

        # 2. Time Machine Check (skip for crypto - they trade 24/7)
        is_crypto = self.is_crypto_pair(symbol)
        if not is_crypto and not self.time_machine.is_trading_allowed(current_time):
            print(f"⏰ Time Machine: Trading NOT allowed for {symbol} at {current_time.strftime('%H:%M')} (Weekend/Off-hours)")
            return None

        if is_crypto:
            print(f"🟢 {symbol} is crypto - 24/7 trading enabled")

        # 3. Sniper Mode Check
        sniper_signal = self.sniper.get_sniper_signal(df_main, current_time)

        # 4. Fetch Crypto for NLP
        df_btc, df_eth = self.fetch_crypto_data()
        nlp_analysis = self.nlp.analyze_btc_eth_correlation(df_btc, df_eth)

        # 5. Feature Engineering
        df_feat = self.fe.create_features(df_main)
        if len(df_feat) == 0:
            return None

        current_bar = df_feat.iloc[[-1]]
        current_price = current_bar['close'].values[0]
        current_atr = current_bar['atr_14'].values[0]

        # 6. Brain Prediction
        result = self.brain.predict(current_bar)
        signal = result['direction']
        confidence = result['confidence']

        # 7. Apply Relim Shield
        shield_approved = self.shield.should_trade(confidence)

        return {
            'symbol': symbol,
            'price': current_price,
            'atr': current_atr,
            'signal': signal,
            'confidence': confidence,
            'shield_approved': shield_approved,
            'sniper_signal': sniper_signal,
            'nlp_analysis': nlp_analysis,
            'time_machine_session': self.time_machine.get_current_session(current_time),
            'bar': current_bar
        }

    def execute_trade(self, analysis: dict, current_time: datetime):
        """
        Execute trade with V4 enhancements.
        """
        symbol = analysis['symbol']
        signal = analysis['signal']
        confidence = analysis['confidence']
        entry = analysis['price']
        atr = analysis['atr']

        print(f"\n💹 === TRADE EXECUTION: {symbol} ===")
        print(f"   Signal: {signal} | Confidence: {confidence:.2f}")
        print(f"   Shield Threshold: {self.shield.get_threshold():.2f}")
        print(f"   Session: {analysis['time_machine_session']}")
        print(f"   Sniper Mode: {analysis['sniper_signal']['reason']}")
        print(f"   NLP Signal: {analysis['nlp_analysis']['signal']}")

        # Calculate Dynamic Stop Loss
        current_vol = atr / entry
        target_vol = 0.0015

        stop_loss_result = self.stop_loss_manager.get_optimal_stop(
            entry_price=entry,
            atr=atr,
            current_vol=current_vol,
            target_vol=target_vol,
            direction=signal,
            bars_held=0,
            df=analysis['bar'],
            strategy='hybrid'
        )

        sl = stop_loss_result['final_stop']

        # Calculate Lot Size
        lot = self.sizer.calculate_lot_size(symbol, entry, sl, atr)

        # Calculate Take Profit
        tp_distance = abs(sl - entry) * 1.5
        tp = entry + tp_distance if signal == 1 else entry - tp_distance

        print(f"   Entry: {entry:.5f} | SL: {sl:.5f} | TP: {tp:.5f}")
        print(f"   Lot Size: {lot}")
        print(f"   Stop Strategy: {stop_loss_result['strategy_used']}")

        # LIVE TRADING MODE (Demo/Live Account)
        print("   ✅ LIVE TRADING MODE - Sending Order to MT5")

        ticket = self.hands.send_order(symbol, signal, lot, sl, tp)
        if ticket:
            self.manager.add_trade(ticket, symbol, entry, sl, tp, signal)
            self.trades_today += 1
            print(f"   ✅ Order Sent! Ticket: {ticket}")
        else:
            print("   ❌ Order Failed - Check MT5 connection")

        print("=" * 40)

    def run(self):
        """
        Main trading loop with all V4 features.
        """
        print("\n" + "=" * 50)
        print("🚀 QUANTEDGE V4 ULTIMATE - STARTED")
        print("=" * 50)
        print(f"💰 Account Balance: ${self.account_balance}")
        print(f"🛡️ Drawdown Guard: {self.guard.max_loss}% max loss")
        print(f"⏰ Time Machine: ACTIVE")
        print(f"🎯 Sniper Mode: ACTIVE")
        print(f"🤖 NLP Sentiment: ACTIVE")
        print(f"🛡️ Relim Shield: ACTIVE (Threshold: {self.shield.get_threshold():.2f})")
        print(f"📊 Assets: {self.watchlist}")
        print("=" * 50 + "\n")

        while True:
            try:
                current_time = datetime.now(timezone.utc)

                # 0. Drawdown Check
                current_eq = self.get_account_equity()
                self.guard.print_status(current_eq)

                if self.guard.check_status(current_eq):
                    print("🛑 Bot Stopped by Drawdown Guard.")
                    break

                # Check max trades
                if self.trades_today >= self.max_trades_per_day:
                    print(f"⏸️ Max trades per day reached ({self.max_trades_per_day}). Monitoring only.")
                    time.sleep(60)
                    continue

                print(f"\n{'='*50}")
                print(f"🔍 Scanning Market - {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                print(f"{'='*50}")

                # 1. Time Machine Status
                self.time_machine.print_status(current_time)

                # 2. Shield Status
                self.shield.print_status()

                # 3. Analyze Each Asset
                candidates = []

                for symbol in self.watchlist:
                    print(f"\n📊 Analyzing {symbol}...")
                    analysis = self.analyze_market(symbol, current_time)

                    if analysis is not None:
                        candidates.append(analysis)

                # 4. Select Best Candidate
                if len(candidates) == 0:
                    print("❌ No valid signals found.")
                else:
                    # Sort by confidence
                    candidates.sort(key=lambda x: x['confidence'], reverse=True)
                    best = candidates[0]

                    print(f"\n✨ Best Candidate: {best['symbol']} (Confidence: {best['confidence']:.2f})")

                    # Check all conditions (lowered threshold to 0.50 for more trades)
                    if (best['shield_approved'] and
                        best['signal'] != 0 and
                        best['confidence'] >= 0.50):

                        # Additional boost from sniper or NLP
                        sniper_boost = best['sniper_signal']['should_trade']
                        nlp_boost = abs(best['nlp_analysis']['confidence']) > 0.3

                        if sniper_boost or nlp_boost:
                            print(f"🚀 BOOSTED SIGNAL!")
                            if sniper_boost:
                                print(f"   └─ Sniper: {best['sniper_signal']['reason']}")
                            if nlp_boost:
                                print(f"   └─ NLP: {best['nlp_analysis']['signal']}")

                        self.execute_trade(best, current_time)
                    else:
                        print("⏸️ Trade conditions not met.")
                        if not best['shield_approved']:
                            print(f"   └─ Shield blocked (conf {best['confidence']:.2f} < threshold {self.shield.get_threshold():.2f})")

                # 5. Manage Open Positions
                print("\n📈 Managing Open Positions...")
                self.manager.manage_trades()

                # Sleep
                print(f"\n💤 Sleeping 60 seconds...\n")
                time.sleep(60)

            except KeyboardInterrupt:
                print("\n🛑 Bot Stopped by User.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)


if __name__ == "__main__":
    # Set use_manual_balance=True to bypass MT5 account info (good for testing)
    bot = QuantEdgeV4(account_balance=10000, use_manual_balance=True)
    bot.run()

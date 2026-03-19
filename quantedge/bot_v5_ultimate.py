# bot_v5_ultimate.py - QuantEdge V5: The Ultimate Quantitative Trading System
"""
QuantEdge V5 - Institutional-Grade Features:
✅ Multi-Timeframe Analysis (4 timeframes)
✅ Kelly Criterion Position Sizing
✅ Correlation Filter
✅ Economic Calendar
✅ LSTM Deep Learning
✅ Advanced Quant Metrics (20+ metrics)
✅ Genetic Algorithm
✅ Time Machine
✅ Sniper Mode
✅ NLP Sentiment
✅ Relim Shield
✅ Dynamic Stop Loss
"""

import sys
sys.path.append('.')
import time
import MetaTrader5 as mt5
from datetime import datetime, timezone
import json
import os

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

# V5 Features
from utils.multi_timeframe import MultiTimeframeAnalyzer
from utils.kelly_criterion import KellyCriterion
from utils.correlation_filter import CorrelationFilter
from utils.economic_calendar import EconomicCalendar
from utils.advanced_news_arbitrage import AdvancedNewsArbitrage
from utils.lead_lag_detector import LeadLagDetector
from utils.probability_window import ProbabilityWindow
from utils.latency_monitor import LatencyMonitor
from dashboard.quant_metrics import QuantMetrics


class QuantEdgeV5:
    def __init__(self, account_balance=10000, use_manual_balance=True):
        print("=" * 60)
        print("🚀 QUANTEDGE V5 ULTIMATE - INITIALIZING")
        print("=" * 60)

        self.account_balance = account_balance
        self.use_manual_balance = use_manual_balance
        self.start_balance = account_balance

        # Core systems
        print("Loading core systems...")
        self.mt5 = MT5Connector()
        self.fe = FeatureEngineer()
        self.brain = InferencePipeline()
        self.hands = OrderExecutor()
        self.manager = PositionManager()
        self.guard = DrawdownGuard(account_balance=account_balance, max_daily_loss_percent=2.0)

        # V4 Advanced Systems
        print("Loading V4 features...")
        self.time_machine = TimeMachine()
        self.sniper = SniperMode(lookback=50, squeeze_threshold=0.8)
        self.nlp = NLPSentimentAnalyzer()
        self.shield = RelimShield(initial_threshold=0.50, min_threshold=0.45, max_threshold=0.75)
        self.stop_loss_manager = DynamicStopLoss(base_atr_multiplier=1.5)

        # V5 Features
        print("Loading V5 features...")
        self.mtf = MultiTimeframeAnalyzer()
        self.kelly = KellyCriterion(lookback=50, fraction=0.25)
        self.correlation = CorrelationFilter(max_correlation=0.7)
        self.calendar = EconomicCalendar()
        self.news_arbitrage = AdvancedNewsArbitrage()
        self.lead_lag = LeadLagDetector(max_lag_periods=20, lookback_periods=200)
        self.prob_window = ProbabilityWindow(lookback_days=90)
        self.latency_monitor = LatencyMonitor(warning_threshold_ms=1000.0)

        # Load news events from API
        print("Loading real-time news events...")
        if not self.news_arbitrage.load_events_from_cache():
            self.news_arbitrage.load_events_from_api()
            self.news_arbitrage.save_events_to_cache()

        # Load probability window data
        print("Loading probability window data...")
        self.prob_window.load_from_file()

        # Load latency monitor data
        print("Loading latency monitor data...")
        self.latency_monitor.load_from_file()

        # Position sizer (will be updated with Kelly later)
        self.sizer = QuantPositionSizer(account_balance=account_balance, risk_per_trade=0.02)

        # Configuration - Base symbols (will be auto-resolved)
        self.base_symbols = {
            'forex': ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
            'metals': ["XAUUSD", "XAGUSD"],
            'crypto': ["BTCUSD", "ETHUSD"]
        }

        # Auto-resolve and enable all symbols in MT5
        print("\n" + "="*60)
        print("🔍 AUTO-DETECTING & ENABLING TRADING SYMBOLS")
        print("="*60)

        self.forex_pairs = []
        self.metal_pairs = []
        self.crypto_pairs = []
        self.symbol_map = {}  # Maps base -> resolved symbol

        if self.mt5.connect():
            # Enable and resolve forex pairs
            print("\n📊 FOREX PAIRS:")
            forex_results = self.mt5.enable_multiple_symbols(self.base_symbols['forex'])
            for base, resolved in forex_results.items():
                if resolved:
                    self.forex_pairs.append(resolved)
                    self.symbol_map[base] = resolved

            # Enable and resolve metal pairs
            print("\n🥇 METAL PAIRS:")
            metal_results = self.mt5.enable_multiple_symbols(self.base_symbols['metals'])
            for base, resolved in metal_results.items():
                if resolved:
                    self.metal_pairs.append(resolved)
                    self.symbol_map[base] = resolved

            # Enable and resolve crypto pairs
            print("\n₿ CRYPTO PAIRS:")
            crypto_results = self.mt5.enable_multiple_symbols(self.base_symbols['crypto'])
            for base, resolved in crypto_results.items():
                if resolved:
                    self.crypto_pairs.append(resolved)
                    self.symbol_map[base] = resolved

        # Combine all enabled symbols
        self.watchlist = self.forex_pairs + self.metal_pairs + self.crypto_pairs
        self.timeframe = mt5.TIMEFRAME_M5

        # Summary
        print(f"\n{'='*60}")
        print(f"✅ SYMBOL DETECTION COMPLETE")
        print(f"{'='*60}")
        print(f"   Forex: {len(self.forex_pairs)} pairs - {self.forex_pairs}")
        print(f"   Metals: {len(self.metal_pairs)} pairs - {self.metal_pairs}")
        print(f"   Crypto: {len(self.crypto_pairs)} pairs - {self.crypto_pairs}")
        print(f"   TOTAL WATCHLIST: {len(self.watchlist)} symbols")
        print(f"{'='*60}\n")

        if not self.watchlist:
            print("⚠️ WARNING: No symbols available - check MT5 connection and broker symbols")
        else:
            print(f"✅ All {len(self.watchlist)} symbols are now enabled in MT5 Market Watch!")

        # Update correlation matrix and lead-lag relationships
        print("Calculating correlation matrix...")
        self.correlation.update_correlation_matrix(self.mt5, self.watchlist)

        print("Analyzing lead-lag relationships...")
        self.lead_lag.update_relationships(self.mt5, self.watchlist)
        self.lead_lag.print_relationships_summary()

        # Tracking
        self.trades_today = 0
        self.max_trades_per_day = 10
        self.trade_history = []  # For quant metrics
        self.returns_history = []

        print("✅ V5 System Initialized Successfully")
        print("=" * 60)

    def get_account_equity(self):
        """Get current equity from MT5"""
        if self.use_manual_balance:
            return self.account_balance

        acc_info = mt5.account_info()
        if acc_info and acc_info.equity > 0:
            return acc_info.equity

        print(f"⚠️ Using manual balance: ${self.account_balance}")
        return self.account_balance

    def is_crypto_pair(self, symbol: str) -> bool:
        """Check if symbol is a crypto pair"""
        # Check if it's in crypto_pairs or contains crypto keywords
        return symbol in self.crypto_pairs or any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'BITCOIN', 'ETHEREUM'])

    def analyze_market_v5(self, symbol: str, current_time: datetime):
        """
        V5 Complete market analysis with all features.
        """
        # Start overall timing
        overall_start = time.time()
        module_timings = {}

        print(f"\n{'='*50}")
        print(f"📊 ANALYZING {symbol}")
        print(f"{'='*50}")

        # 1. Fetch data
        self.latency_monitor.start_timing('data_fetch')
        df_main = self.mt5.get_latest_bars(symbol, self.timeframe, count=200)
        module_timings['data_fetch'] = self.latency_monitor.end_timing('data_fetch')

        if df_main is None or len(df_main) < 50:
            print(f"❌ Not enough data for {symbol}")
            return None

        # 2. Time Machine Check (skip for crypto)
        is_crypto = self.is_crypto_pair(symbol)
        if not is_crypto and not self.time_machine.is_trading_allowed(current_time):
            print(f"⏰ Time Machine: Trading blocked (Weekend/Off-hours)")
            return None

        if is_crypto:
            print(f"🟢 Crypto - 24/7 trading enabled")

        # 3. Advanced News Arbitrage Check
        news_phase = self.news_arbitrage.get_news_phase(current_time, symbol)

        print(f"📰 News Phase: {news_phase['phase'].upper()} | Strategy: {news_phase['strategy']}")

        if news_phase['strategy'] == 'avoid':
            if news_phase.get('minutes_to_news'):
                print(f"⏰ High-impact news in {news_phase['minutes_to_news']:.1f} minutes - avoiding trade")
            else:
                print(f"⏰ News event in progress ({news_phase.get('minutes_since_news', 0):.1f} min ago) - avoiding trade")
            return None

        # Detect volatility spike
        volatility_spike = self.news_arbitrage.detect_volatility_spike(df_main)
        if volatility_spike['spike_detected']:
            print(f"⚡ Volatility spike detected! ATR: {volatility_spike['current_atr']:.5f} "
                  f"(+{(volatility_spike['atr_ratio']-1)*100:.1f}%)")

        # 4. Multi-Timeframe Analysis
        print("📊 Multi-Timeframe Analysis...")
        self.latency_monitor.start_timing('mtf_analysis')
        mtf_results = self.mtf.analyze_symbol(self.mt5, symbol)
        alignment = self.mtf.get_alignment_score(mtf_results)
        module_timings['mtf_analysis'] = self.latency_monitor.end_timing('mtf_analysis')

        print(f"   Alignment: {alignment['agreement']*100:.0f}% | Direction: {alignment['direction']} | Score: {alignment['score']:.2f}")
        print(f"   Votes: 🔼{alignment['bullish_votes']} | 🔽{alignment['bearish_votes']} | ➖{alignment['neutral_votes']}")

        if not alignment['aligned']:
            print(f"⚠️ Timeframes not aligned - skipping")
            return None

        # 5. Correlation Check
        corr_check = self.correlation.is_correlated_with_open_positions(symbol)
        if not corr_check['allowed']:
            print(f"🔗 Correlation Filter: {corr_check['reason']}")
            return None

        # 6. Sniper Mode
        sniper_signal = self.sniper.get_sniper_signal(df_main, current_time)

        # 7. NLP (if crypto data available)
        df_btc, df_eth = None, None
        try:
            df_btc = self.mt5.get_latest_bars("BTCUSD", self.timeframe, count=50)
            df_eth = self.mt5.get_latest_bars("ETHUSD", self.timeframe, count=50)
        except:
            pass

        nlp_analysis = self.nlp.analyze_btc_eth_correlation(df_btc, df_eth)

        # 8. Feature Engineering
        self.latency_monitor.start_timing('feature_engineering')
        df_feat = self.fe.create_features(df_main)
        module_timings['feature_engineering'] = self.latency_monitor.end_timing('feature_engineering')

        if len(df_feat) == 0:
            print("❌ Feature engineering failed")
            return None

        current_bar = df_feat.iloc[[-1]]
        current_price = current_bar['close'].values[0]
        current_atr = current_bar['atr_14'].values[0]

        # 9. ML Brain Prediction
        self.latency_monitor.start_timing('ml_prediction')
        result = self.brain.predict(current_bar)
        signal = result['direction']
        confidence = result['confidence']
        module_timings['ml_prediction'] = self.latency_monitor.end_timing('ml_prediction')

        # 10. Lead-Lag Analysis
        self.latency_monitor.start_timing('lead_lag_analysis')
        lead_lag_score = self.lead_lag.get_lead_lag_score(symbol, self.mt5)
        module_timings['lead_lag_analysis'] = self.latency_monitor.end_timing('lead_lag_analysis')

        if lead_lag_score['has_leading_signal']:
            print(f"🔗 Lead-Lag Signal: {lead_lag_score['signal']} | "
                  f"Confidence: {lead_lag_score['confidence']:.2f}")
            print(f"   Reason: {lead_lag_score['reason']}")

        # 11. Apply MTF Confidence Multiplier
        mtf_multiplier = self.mtf.get_confidence_multiplier(alignment)
        boosted_confidence = min(1.0, confidence * mtf_multiplier)

        # 12. Apply Lead-Lag Multiplier
        lead_lag_boost, lead_lag_multiplier = self.lead_lag.should_boost_signal(
            symbol, signal, lead_lag_score
        )
        confidence_with_lead_lag = min(1.0, boosted_confidence * lead_lag_multiplier)

        # 13. Apply Probability Window Multiplier
        self.latency_monitor.start_timing('probability_window')
        prob_score = self.prob_window.get_probability_score(current_time, symbol)
        module_timings['probability_window'] = self.latency_monitor.end_timing('probability_window')

        prob_multiplier = prob_score['confidence_multiplier']
        final_confidence = min(1.0, confidence_with_lead_lag * prob_multiplier)

        print(f"🧠 ML Prediction: {signal}")
        print(f"   Base Confidence: {confidence:.2f}")
        print(f"   → MTF Boosted: {boosted_confidence:.2f}")
        print(f"   → Lead-Lag: {confidence_with_lead_lag:.2f}")
        print(f"   → Probability Window: {final_confidence:.2f} (FINAL)")

        if lead_lag_boost:
            print(f"   ✅ Lead-Lag AGREES (boost: {lead_lag_multiplier:.2f}x)")
        elif lead_lag_multiplier < 1.0:
            print(f"   ⚠️ Lead-Lag DISAGREES (reduce: {lead_lag_multiplier:.2f}x)")

        print(f"⏰ Time Probability: {prob_score['overall_probability']*100:.1f}% | "
              f"{prob_score['recommendation']}")

        # 14. Shield Check
        self.latency_monitor.start_timing('shield_check')
        shield_approved = self.shield.should_trade(final_confidence)
        module_timings['shield_check'] = self.latency_monitor.end_timing('shield_check')

        # Calculate total latency
        total_latency = time.time() - overall_start

        # Record latency
        self.latency_monitor.record_signal_latency(symbol, total_latency, module_timings)

        # Get latency score
        latency_score = self.latency_monitor.get_latency_score(symbol, total_latency)

        # Display latency breakdown
        print(f"\n⚡ Latency Score: {latency_score['score']}/100 ({latency_score['rating'].upper()})")
        print(f"   Total: {latency_score['current_latency_ms']:.1f} ms | "
              f"Avg: {latency_score['avg_latency_ms']:.1f} ms | "
              f"{latency_score['relative_speed']}")

        # Print detailed breakdown
        self.latency_monitor.print_module_breakdown(module_timings)

        return {
            'symbol': symbol,
            'price': current_price,
            'atr': current_atr,
            'signal': signal,
            'confidence': confidence,
            'boosted_confidence': boosted_confidence,
            'final_confidence': final_confidence,
            'shield_approved': shield_approved,
            'mtf_alignment': alignment,
            'sniper_signal': sniper_signal,
            'nlp_analysis': nlp_analysis,
            'correlation_check': corr_check,
            'news_phase': news_phase,
            'volatility_spike': volatility_spike,
            'lead_lag_score': lead_lag_score,
            'prob_score': prob_score,
            'latency_score': latency_score,
            'module_timings': module_timings,
            'total_latency': total_latency,
            'bar': current_bar
        }

    def execute_trade_v5(self, analysis: dict, current_time: datetime):
        """
        Execute trade with V5 enhancements.
        """
        symbol = analysis['symbol']
        signal = analysis['signal']
        confidence = analysis['final_confidence']
        entry = analysis['price']
        atr = analysis['atr']

        print(f"\n💹 {'='*50}")
        print(f"💹 TRADE EXECUTION: {symbol}")
        print(f"💹 {'='*50}")
        print(f"   Signal: {signal} | Final Confidence: {confidence:.2f}")
        print(f"   MTF Alignment: {analysis['mtf_alignment']['agreement']*100:.0f}%")
        print(f"   Shield: {'✅ APPROVED' if analysis['shield_approved'] else '❌ BLOCKED'}")
        if analysis['lead_lag_score']['has_leading_signal']:
            print(f"   Lead-Lag: {analysis['lead_lag_score']['leader']} leads this symbol")

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

        # Kelly Criterion Position Sizing
        kelly_info = self.kelly.calculate_position_size(self.account_balance, abs((sl - entry) / entry))
        kelly_risk = kelly_info['risk_per_trade']

        # Apply news-based risk adjustment
        news_phase = analysis['news_phase']
        adjusted_risk = kelly_risk * news_phase['risk_multiplier']

        print(f"💰 Kelly Criterion:")
        print(f"   Fraction: {kelly_info['kelly_fraction']:.3f}")
        print(f"   Base Risk per Trade: {kelly_risk*100:.2f}%")
        print(f"   News Multiplier: {news_phase['risk_multiplier']:.2f}x")
        print(f"   Adjusted Risk: {adjusted_risk*100:.2f}%")
        print(f"   Recommendation: {kelly_info['recommendation']}")
        print(f"   Win Rate: {kelly_info['win_rate']*100:.1f}%")
        print(f"   Win/Loss Ratio: {kelly_info['win_loss_ratio']:.2f}")

        # Use adjusted Kelly risk
        self.sizer.risk_per_trade = adjusted_risk

        # Calculate Take Profit (base)
        tp_distance = abs(sl - entry) * 1.5
        base_tp = entry + tp_distance if signal == 1 else entry - tp_distance

        # Apply news-based SL/TP adjustments
        news_adjustments = self.news_arbitrage.get_news_based_sl_tp(
            entry=entry,
            signal=signal,
            base_sl=sl,
            base_tp=base_tp,
            news_phase=news_phase
        )

        sl = news_adjustments['sl']
        tp = news_adjustments['tp']

        # Calculate Lot Size with adjusted SL
        lot = self.sizer.calculate_lot_size(symbol, entry, sl, atr)

        print(f"\n📊 Order Details:")
        print(f"   Entry: {entry:.5f}")
        print(f"   Stop Loss: {sl:.5f} ({stop_loss_result['strategy_used']})")
        print(f"   Take Profit: {tp:.5f}")
        print(f"   News Adjustment: {news_adjustments['reason']}")
        print(f"   Lot Size: {lot}")
        print(f"   Risk Amount: ${self.account_balance * adjusted_risk:.2f}")

        # LIVE TRADING
        print(f"\n✅ SENDING ORDER TO MT5...")

        ticket = self.hands.send_order(symbol, signal, lot, sl, tp)
        if ticket:
            self.manager.add_trade(ticket, symbol, entry, sl, tp, signal)
            self.correlation.add_position(symbol, signal)
            self.trades_today += 1

            # Record trade
            self.trade_history.append({
                'time': current_time,
                'symbol': symbol,
                'signal': signal,
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'lot': lot,
                'confidence': confidence,
                'ticket': ticket
            })

            print(f"✅ Order Sent! Ticket: {ticket}")
        else:
            print(f"❌ Order Failed")

        print(f"{'='*50}")

    def calculate_quant_metrics(self):
        """Calculate and display quant metrics"""
        if len(self.returns_history) < 10:
            return

        metrics = QuantMetrics(self.returns_history)
        all_metrics = metrics.get_all_metrics()

        print(f"\n{'='*60}")
        print(f"📊 QUANTITATIVE PERFORMANCE METRICS")
        print(f"{'='*60}")

        print(f"\n💰 RETURNS:")
        print(f"   Total Return: {all_metrics['total_return']*100:+.2f}%")
        print(f"   Annualized Return: {all_metrics['annualized_return']*100:+.2f}%")
        print(f"   Annualized Volatility: {all_metrics['annualized_volatility']*100:.2f}%")

        print(f"\n📈 RISK-ADJUSTED RETURNS:")
        print(f"   Sharpe Ratio: {all_metrics['sharpe_ratio']:.2f}")
        print(f"   Sortino Ratio: {all_metrics['sortino_ratio']:.2f}")
        print(f"   Calmar Ratio: {all_metrics['calmar_ratio']:.2f}")
        print(f"   Omega Ratio: {all_metrics['omega_ratio']:.2f}")

        print(f"\n⚠️ RISK METRICS:")
        print(f"   Max Drawdown: {all_metrics['max_drawdown']*100:.2f}%")
        print(f"   VaR 95%: {all_metrics['var_95']*100:.2f}%")
        print(f"   CVaR 95%: {all_metrics['cvar_95']*100:.2f}%")
        print(f"   Ulcer Index: {all_metrics['ulcer_index']:.2f}")

        print(f"\n📊 DISTRIBUTION:")
        print(f"   Skewness: {all_metrics['skewness']:.2f}")
        print(f"   Kurtosis: {all_metrics['kurtosis']:.2f}")
        print(f"   Tail Ratio: {all_metrics['tail_ratio']:.2f}")

        print(f"\n🎯 OTHER:")
        print(f"   Gain-to-Pain: {all_metrics['gain_to_pain']:.2f}")
        print(f"   Recovery Factor: {all_metrics['recovery_factor']:.2f}")

        print(f"{'='*60}\n")

    def save_session_data(self):
        """Save session data to JSON"""
        session_data = {
            'start_time': datetime.now().isoformat(),
            'start_balance': self.start_balance,
            'current_balance': self.get_account_equity(),
            'trades': self.trade_history,
            'returns': self.returns_history,
            'trades_count': len(self.trade_history)
        }

        filename = f"logs/session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('logs', exist_ok=True)

        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)

        print(f"💾 Session data saved to {filename}")

    def run(self):
        """
        Main trading loop with all V5 features.
        """
        print("\n" + "=" * 60)
        print("🚀 QUANTEDGE V5 ULTIMATE - STARTED")
        print("=" * 60)
        print(f"💰 Account Balance: ${self.account_balance}")
        print(f"🛡️ Drawdown Guard: {self.guard.max_loss}% max loss")
        print(f"\n🔧 V5 CORE FEATURES:")
        print(f"   ⏰ Time Machine: ACTIVE")
        print(f"   📊 Multi-Timeframe: ACTIVE (4 TFs)")
        print(f"   💰 Kelly Criterion: ACTIVE")
        print(f"   🔗 Correlation Filter: ACTIVE (max {self.correlation.max_correlation})")
        print(f"   🎯 Sniper Mode: ACTIVE")
        print(f"   🤖 NLP Sentiment: ACTIVE")
        print(f"   🛡️ Relim Shield: ACTIVE (Threshold: {self.shield.get_threshold():.2f})")
        print(f"\n🆕 NEW ADVANCED FEATURES:")
        print(f"   📰 Advanced News Arbitrage: ACTIVE")
        print(f"   🔗 Lead-Lag Detection: ACTIVE")
        print(f"   ⏰ Probability Window: ACTIVE")
        print(f"   ⚡ Latency Monitoring: ACTIVE")
        print(f"\n📊 Trading Symbols ({len(self.watchlist)}):")
        print(f"   Forex: {self.forex_pairs}")
        print(f"   Metals: {self.metal_pairs}")
        print(f"   Crypto: {self.crypto_pairs}")
        print(f"{'='*60}\n")

        cycle_count = 0

        while True:
            try:
                current_time = datetime.now(timezone.utc)
                cycle_count += 1

                # Drawdown Check
                current_eq = self.get_account_equity()
                self.guard.print_status(current_eq)

                if self.guard.check_status(current_eq):
                    print("🛑 Bot Stopped by Drawdown Guard.")
                    break

                # Max trades check
                if self.trades_today >= self.max_trades_per_day:
                    print(f"⏸️ Max trades per day reached ({self.max_trades_per_day}). Monitoring only.")
                    time.sleep(60)
                    continue

                print(f"\n{'='*60}")
                print(f"🔍 MARKET SCAN #{cycle_count} - {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                print(f"{'='*60}")

                # Time Machine Status
                self.time_machine.print_status(current_time)

                # Shield Status
                self.shield.print_status()

                # Kelly Stats
                kelly_stats = self.kelly.get_stats()
                print(f"\n💰 Kelly Criterion Stats:")
                print(f"   Kelly Fraction: {kelly_stats['kelly_fraction']:.3f}")
                print(f"   Win Rate: {kelly_stats['win_rate']*100:.1f}%")
                print(f"   W/L Ratio: {kelly_stats['win_loss_ratio']:.2f}")

                # Correlation Stats
                corr_report = self.correlation.get_correlation_report()
                diversification = self.correlation.get_diversification_score()
                print(f"\n🔗 Correlation Filter:")
                print(f"   Open Positions: {len(corr_report['open_positions'])}")
                print(f"   Diversification Score: {diversification*100:.0f}%")

                # Display news calendar every cycle
                if cycle_count % 5 == 0:  # Every 5 cycles
                    self.news_arbitrage.print_news_calendar(current_time, hours_ahead=4)

                # Analyze each asset
                candidates = []

                for symbol in self.watchlist:
                    analysis = self.analyze_market_v5(symbol, current_time)

                    if analysis is not None:
                        candidates.append(analysis)

                # Select best candidate
                if len(candidates) == 0:
                    print("\n❌ No valid signals found.")
                else:
                    # Sort by final confidence (includes MTF + Lead-Lag)
                    candidates.sort(key=lambda x: x['final_confidence'], reverse=True)
                    best = candidates[0]

                    print(f"\n✨ BEST CANDIDATE: {best['symbol']}")
                    print(f"   Final Confidence: {best['final_confidence']:.2f}")
                    print(f"   MTF Alignment: {best['mtf_alignment']['agreement']*100:.0f}%")
                    if best['lead_lag_score']['has_leading_signal']:
                        print(f"   Lead-Lag Boost: {best['lead_lag_score']['leader']} leads")

                    # Execute if conditions met
                    if (best['shield_approved'] and
                        best['signal'] != 0 and
                        best['final_confidence'] >= 0.50):

                        self.execute_trade_v5(best, current_time)
                    else:
                        print("⏸️ Trade conditions not met.")

                # Manage open positions
                print("\n📈 Managing Open Positions...")
                closed_trades = self.manager.manage_trades()

                # Record closed trades in probability window
                for closed_trade in closed_trades:
                    self.prob_window.record_closed_trade(closed_trade)
                    print(f"📊 Recorded trade to probability window: "
                          f"{closed_trade['symbol']} P&L: {closed_trade['profit']:.2f}")

                # Calculate quant metrics every 10 cycles
                if cycle_count % 10 == 0:
                    self.calculate_quant_metrics()

                # Display probability report every 15 cycles
                if cycle_count % 15 == 0:
                    self.prob_window.print_probability_report()

                # Display latency report every 20 cycles
                if cycle_count % 20 == 0:
                    self.latency_monitor.print_latency_report()

                # Save session data every 20 cycles
                if cycle_count % 20 == 0:
                    self.save_session_data()
                    self.prob_window.save_to_file()
                    self.latency_monitor.save_to_file()

                # Sleep
                print(f"\n💤 Sleeping 60 seconds...\n")
                time.sleep(60)

            except KeyboardInterrupt:
                print("\n🛑 Bot Stopped by User.")
                self.save_session_data()
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)


if __name__ == "__main__":
    # V5 Ultimate Bot
    bot = QuantEdgeV5(account_balance=10000, use_manual_balance=True)
    bot.run()

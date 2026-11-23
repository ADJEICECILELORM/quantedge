# bot_v6_ultimate.py - QuantEdge V6: RAG-Powered Institutional Trading System
"""
QuantEdge V6.0 - INSTITUTIONAL-GRADE RAG INTELLIGENCE:

🧠 RAG Intelligence:
✅ Multi-source news aggregation with source scoring
✅ Vector database (Qdrant) with semantic search
✅ Structured feature extraction (NO hallucination)
✅ Regime classification with strategy recommendations

📊 Quantitative Models:
✅ Jump-Diffusion (Merton) - news-driven jump probability
✅ Information Decay - optimal holding periods
✅ Enhanced Kelly Criterion - multi-factor position sizing

🏛️ Microstructure:
✅ VPIN Filter - toxicity/insider trading detection
✅ Lead-Lag Enhanced - front-running signals
✅ Pairs Trading - delta-neutral hedging

🔬 Optimizer:
✅ Constrained GA - parameter optimization only
✅ Multi-objective fitness - Sortino + drawdown + consistency

🛡️ Safety:
✅ Shadow Mode - test without execution (default)
✅ Risk Gates - immutable hard constraints
✅ Kill Switch - 5% daily loss limit
"""

import sys
sys.path.append('.')
import time
import MetaTrader5 as mt5
from datetime import datetime, timezone
import json
import os
import argparse
from typing import Dict, List, Optional

# Core V5 Components
from utils.mt5_connector import MT5Connector
from features.feature_engineer import FeatureEngineer
from pipeline.inference_pipeline import InferencePipeline
from risk.position_sizer import QuantPositionSizer
from risk.portfolio import PortfolioExposureManager
from risk.drawdown_guard import DrawdownGuard
from utils.order_executor import OrderExecutor
from utils.position_manager import PositionManager

# V5 Advanced Features
from utils.multi_timeframe import MultiTimeframeAnalyzer
from utils.kelly_criterion import KellyCriterion
from utils.correlation_filter import CorrelationFilter
from utils.economic_calendar import EconomicCalendar
from utils.latency_monitor import LatencyMonitor
from dashboard.quant_metrics import QuantMetrics

# V6 RAG Intelligence
from rag.news_ingestion import NewsIngestionOrchestrator
from rag.source_scoring import SourceScoringEngine
from rag.rag_retriever import RAGRetriever
from rag.feature_extractor import FeatureExtractor
from rag.regime_classifier import RegimeClassifier

# V6 Quantitative Models
from quant.jump_diffusion import JumpDiffusionModel
from quant.information_decay import InformationDecayModel
from quant.kelly_enhanced import EnhancedKellyCriterion

# V6 Microstructure
from microstructure.vpin_filter import VPINFilter
from microstructure.lead_lag_enhanced import EnhancedLeadLagDetector
from microstructure.pairs_trading import PairsTradingStrategy

# V6 Safety & Control
from safety.shadow_mode import ShadowModeLogger, ShadowModeToggle
from safety.risk_gates import RiskGates

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuantEdgeV6:
    """
    QuantEdge V6.0 - RAG-Powered Institutional Trading System.

    Combines:
    - V5 battle-tested execution engine
    - V6 RAG intelligence layer
    - Institutional quant models
    - Market microstructure analysis
    - Multi-layer safety systems
    """

    def __init__(
        self,
        account_balance: float = 10000,
        use_manual_balance: bool = True,
        shadow_mode: bool = True,
        config: Optional[dict] = None
    ):
        from utils.config import load_config, resolve_timeframe
        self.config = config or load_config()
        print("=" * 60)
        print("🚀 QUANTEDGE V6.0 - RAG INTELLIGENCE SYSTEM")
        print("=" * 60)

        self.account_balance = account_balance
        self.use_manual_balance = use_manual_balance
        self.start_balance = account_balance

        # Shadow mode toggle
        if shadow_mode:
            ShadowModeToggle.enable_shadow_mode()
        else:
            ShadowModeToggle.disable_shadow_mode()

        # === CORE V5 SYSTEMS ===
        print("\n📦 Loading V5 Core Systems...")
        self.mt5 = MT5Connector()
        self.fe = FeatureEngineer()
        self.brain = InferencePipeline()  # V5 LSTM models
        self.hands = OrderExecutor()
        self.manager = PositionManager()
        self.guard = DrawdownGuard(
            account_balance=account_balance,
            max_daily_loss_percent=self.config['risk']['max_daily_loss_percent']
        )

        # V5 Advanced
        self.mtf = MultiTimeframeAnalyzer()
        self.kelly_v5 = KellyCriterion(lookback=50, fraction=0.25)
        self.correlation = CorrelationFilter(max_correlation=self.config['risk']['max_correlation'])
        self.portfolio = PortfolioExposureManager(
            max_gross_exposure_usd=self.config['risk'].get('max_gross_exposure_usd', 20000),
            max_net_exposure_usd=self.config['risk'].get('max_net_exposure_usd', 10000),
        )
        self.calendar = EconomicCalendar()
        self.latency_monitor = LatencyMonitor(warning_threshold_ms=1000.0)
        self.sizer = QuantPositionSizer(
            account_balance=account_balance,
            risk_per_trade=self.config['account']['risk_per_trade'],
            max_lot_cap=self.config['risk']['max_lot'],
            vol_target_per_bar=self.config['risk'].get('vol_target_per_bar', 0.0015),
        )

        # === V6 RAG INTELLIGENCE ===
        self.rag_enabled = bool(self.config.get('rag', {}).get('enabled', False))
        if not self.rag_enabled:
            print('RAG intelligence DISABLED by config (mock news sources)')
        print("\n🧠 Loading V6 RAG Intelligence...")
        self.news_orchestrator = NewsIngestionOrchestrator()
        self.source_scorer = SourceScoringEngine()
        self.rag_retriever = RAGRetriever(collection_name="quantedge_news")
        self.feature_extractor = FeatureExtractor()
        self.regime_classifier = RegimeClassifier()

        # === V6 QUANTITATIVE MODELS ===
        print("📊 Loading V6 Quant Models...")
        self.jump_diffusion = JumpDiffusionModel()
        self.info_decay = InformationDecayModel()
        self.kelly_enhanced = EnhancedKellyCriterion()

        # === V6 MICROSTRUCTURE ===
        print("🏛️ Loading V6 Microstructure Filters...")
        self.vpin = VPINFilter()
        self.lead_lag_enhanced = EnhancedLeadLagDetector()
        self.pairs_trading = PairsTradingStrategy()

        # === V6 SAFETY LAYER ===
        print("🛡️ Loading V6 Safety Systems...")
        self.shadow_logger = ShadowModeLogger()
        self.risk_gates = RiskGates(account_balance=account_balance)

        # === SYMBOL UNIVERSE (Basic symbols all brokers have) ===
        print("\n🌍 Configuring Symbol Universe...")
        self.base_symbols = self.config['symbols']

        # Auto-resolve and enable symbols
        self.watchlist = []
        self.symbol_map = {}

        if self.mt5.connect():
            print("\n🔍 AUTO-DETECTING SYMBOLS...")
            for category, symbols in self.base_symbols.items():
                print(f"\n{category.upper().replace('_', ' ')}:")
                results = self.mt5.enable_multiple_symbols(symbols)
                for base, resolved in results.items():
                    if resolved:
                        self.watchlist.append(resolved)
                        self.symbol_map[base] = resolved

        self.timeframe = resolve_timeframe(self.config['timeframe'])

        # Summary
        print(f"\n{'='*60}")
        print(f"✅ SYMBOL DETECTION COMPLETE")
        print(f"{'='*60}")
        print(f"   Total Symbols: {len(self.watchlist)}")
        for category, symbols in self.base_symbols.items():
            enabled = [s for s in symbols if s in self.symbol_map]
            print(f"   {category.title()}: {len(enabled)}/{len(symbols)}")
        print(f"{'='*60}\n")

        # Check if we have symbols
        if not self.watchlist:
            print("\n" + "="*60)
            print("⚠️  WARNING: NO SYMBOLS DETECTED!")
            print("="*60)
            print("\nPossible causes:")
            print("1. MT5 is not running or not logged in")
            print("2. 'Algo Trading' button not enabled in MT5")
            print("3. Broker doesn't support these symbols")
            print("\nFix:")
            print("1. Open MetaTrader 5")
            print("2. Login to your account")
            print("3. Click 'Algo Trading' button (should turn GREEN)")
            print("4. Restart this bot")
            print("="*60 + "\n")

            logger.error("No symbols detected - cannot continue")
            raise RuntimeError("No trading symbols available. Check MT5 connection.")

        # Initialize correlation matrix and lead-lag
        if self.watchlist:
            print("📈 Initializing Market Analysis...")
            self.correlation.update_correlation_matrix(self.mt5, self.watchlist)
            self.lead_lag_enhanced.update_relationships(self.mt5, self.watchlist)

            # Find pairs for delta-neutral trading
            print("🔗 Finding Trading Pairs...")
            self.trading_pairs = self.pairs_trading.find_pairs(
                self.mt5,
                self.watchlist,
                min_correlation=0.7
            )
            print(f"   Found {len(self.trading_pairs)} viable pairs")

        # Tracking
        self.trades_today = 0
        self.max_trades_per_day = 20  # Increased for more pairs
        self.trade_history = []
        self.returns_history = []
        self.current_regime = None

        # Fetch initial news
        print("\n📰 Fetching Recent News...")
        self.refresh_news()

        print("\n" + "="*60)
        print("✅ QUANTEDGE V6.0 INITIALIZED SUCCESSFULLY")
        print("="*60)
        print(f"Mode: {ShadowModeToggle.get_status()}")
        print(f"Symbols: {len(self.watchlist)}")
        print(f"Trading Pairs: {len(self.trading_pairs) if hasattr(self, 'trading_pairs') else 0}")
        self.risk_gates.print_status()

    def refresh_news(self):
        """Fetch and process recent news events"""
        if not getattr(self, 'rag_enabled', False):
            return
        try:
            # Fetch news from last 60 minutes
            raw_events = self.news_orchestrator.fetch_news(minutes=60)

            print(f"   Fetched {len(raw_events)} news events")

            # Process and store in vector DB
            stored = 0
            for raw_event in raw_events:
                structured = self.news_orchestrator.process_event(raw_event)
                if structured:
                    # Store in RAG
                    if self.rag_retriever.store_event(structured):
                        stored += 1

            print(f"   Stored {stored} events in vector DB")

        except Exception as e:
            logger.error(f"Error refreshing news: {e}")

    def get_news_intelligence(self, symbol: str) -> Optional[Dict]:
        """
        Get RAG intelligence for symbol.

        Returns structured news features (NO hallucination).
        """
        if not getattr(self, 'rag_enabled', False):
            return None

        if not symbol or not isinstance(symbol, str):
            logger.warning(f"Invalid symbol provided: {symbol}")
            return None

        try:
            # Query RAG for relevant news
            query = f"News affecting {symbol} trading"
            similar_events = self.rag_retriever.retrieve_similar(
                query=query,
                top_k=5,
                time_decay_hours=24.0
            )

            if not similar_events:
                return None

            # Extract structured features from most relevant event
            most_relevant = similar_events[0]

            if 'event' not in most_relevant:
                logger.warning(f"Invalid event structure for {symbol}")
                return None

            news_features = self.feature_extractor.extract_features(
                event=most_relevant['event'],
                similar_events=similar_events
            )

            return {
                'features': news_features,
                'source_score': most_relevant.get('score', 0.0),
                'event': most_relevant['event']
            }

        except KeyError as e:
            logger.error(f"Missing key in news data for {symbol}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid value in news processing for {symbol}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting news intelligence for {symbol}")
            return None

    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Complete V6 analysis pipeline for a symbol.

        Pipeline:
        1. Fetch market data
        2. Get news intelligence (RAG)
        3. Classify market regime
        4. Calculate quant signals
        5. Apply microstructure filters
        6. Check risk gates
        """
        # Input validation
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"Invalid symbol: {symbol}")
            return None

        if len(symbol) < 3 or len(symbol) > 20:
            logger.warning(f"Symbol length invalid: {symbol}")
            return None

        try:
            # 1. Get market data
            df = self.mt5.get_data(symbol, self.timeframe, bars=500)

            if df is None:
                logger.debug(f"No data returned for {symbol}")
                return None

            if len(df) < 100:
                logger.debug(f"Insufficient data for {symbol}: {len(df)} bars")
                return None

            # Validate data quality
            if df['close'].isna().sum() > 0:
                logger.warning(f"Data contains NaN values for {symbol}")
                return None

            # 2. Get news intelligence
            news_intel = self.get_news_intelligence(symbol)
            news_features = news_intel['features'] if news_intel else None

            # 3. Classify regime
            regime = self.regime_classifier.classify(df, news_features)

            # 4. Multi-timeframe analysis (V5)
            mtf_signal = self.mtf.analyze(symbol, self.mt5)
            if mtf_signal is None:
                return None

            # 5. V5 LSTM prediction
            features = self.fe.create_features(df)
            if features is None or len(features) == 0:
                return None

            prediction = self.brain.predict(features)

            # 6. Jump-Diffusion probability (if news available)
            jump_prob = 0.0
            if news_features:
                jump_prob = self.jump_diffusion.calculate_jump_probability(
                    news_features=news_features,
                    time_horizon_hours=1.0
                )

            # 7. VPIN toxicity check
            vpin_result = self.vpin.should_block_trade(df, update=True)
            if vpin_result['should_block']:
                logger.info(f"VPIN blocked {symbol}: {vpin_result['reason']}")
                return None

            # 8. Lead-Lag signal
            lead_lag_signal = self.lead_lag_enhanced.get_lead_lag_signal(symbol, self.mt5)

            # 9. Combine signals
            combined_signal = self._combine_signals(
                prediction=prediction,
                mtf_signal=mtf_signal,
                regime=regime,
                news_features=news_features,
                jump_prob=jump_prob,
                lead_lag_signal=lead_lag_signal
            )

            if combined_signal is None:
                return None

            # 10. Calculate position size with Enhanced Kelly
            current_price = df['close'].iloc[-1]

            if news_features:
                position_result = self.kelly_enhanced.calculate_enhanced_position_size(
                    account_balance=self.account_balance,
                    news_features=news_features,
                    regime=regime,
                    current_drawdown=self.guard.current_drawdown
                )
            else:
                # Fallback to V5 Kelly
                kelly_result = self.kelly_v5.calculate_kelly_size(
                    account_balance=self.account_balance,
                    symbol=symbol,
                    mt5_connector=self.mt5
                )
                position_result = {
                    'recommended_size_usd': kelly_result['position_size_usd'],
                    'kelly_fraction': kelly_result['kelly_fraction']
                }

            position_size_usd = position_result['recommended_size_usd']

            # 11. Risk gates check
            gates_result = self.risk_gates.check_all_gates(
                position_size_usd=position_size_usd,
                current_balance=self.account_balance
            )

            if not gates_result['approved']:
                logger.warning(f"Risk gates blocked {symbol}: {gates_result['reason']}")
                return None

            # 12. Information decay - optimal holding period
            holding_period_hours = 4.0  # Default
            if news_features:
                decay_result = self.info_decay.get_optimal_holding_period(
                    initial_impact=news_features.impact_score,
                    event_type='economic_data'  # Could be classified from news
                )
                holding_period_hours = decay_result['optimal_holding_hours']

            return {
                'symbol': symbol,
                'signal': combined_signal,
                'regime': regime,
                'news_features': news_features,
                'jump_probability': jump_prob,
                'position_size_usd': position_size_usd,
                'holding_period_hours': holding_period_hours,
                'current_price': current_price,
                'vpin_safe': True,
                'lead_lag_signal': lead_lag_signal
            }

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None

    def _combine_signals(
        self,
        prediction: Dict,
        mtf_signal: Dict,
        regime,
        news_features,
        jump_prob: float,
        lead_lag_signal: Optional[Dict]
    ) -> Optional[int]:
        """
        Combine all signals into final trade decision.

        Returns:
            1 = BUY, -1 = SELL, None = NO TRADE
        """
        # V5 signals
        v5_prediction = prediction['direction']
        v5_confidence = prediction['confidence']
        mtf_trend = mtf_signal.get('overall_trend', 0)

        # Regime strategy
        regime_strategy = self.regime_classifier.get_recommended_strategy(regime)

        # Base signal from V5
        if v5_confidence < 0.6:
            return None

        base_signal = v5_prediction

        # Adjust based on regime
        if regime.regime_type == 'Mean Reversion':
            # Invert signal for mean reversion
            base_signal = -base_signal

        # News adjustment
        if news_features:
            # High impact news: follow news sentiment
            if news_features.impact_score > 0.7:
                if news_features.sentiment > 0.3:
                    base_signal = 1
                elif news_features.sentiment < -0.3:
                    base_signal = -1

            # Jump expected: increase conviction
            if jump_prob > 0.5:
                logger.info(f"High jump probability ({jump_prob:.2%}) - increasing conviction")

        # Lead-lag adjustment
        if lead_lag_signal and lead_lag_signal.get('has_leader'):
            # Follow the leader signal
            leader_signal = lead_lag_signal.get('leader_signal', 0)
            if abs(leader_signal) > 0:
                base_signal = leader_signal
                logger.info(f"Following lead-lag signal from {lead_lag_signal.get('leader_symbol')}")

        # MTF confirmation
        if base_signal * mtf_trend < 0:
            # Conflict with MTF
            return None

        return base_signal

    def execute_trade(self, analysis: Dict):
        """Execute trade based on analysis"""
        # Input validation
        if not analysis or not isinstance(analysis, dict):
            logger.error("Invalid analysis object provided")
            return

        required_keys = ['symbol', 'signal', 'position_size_usd', 'current_price']
        for key in required_keys:
            if key not in analysis:
                logger.error(f"Missing required key in analysis: {key}")
                return

        try:
            symbol = analysis['symbol']
            signal = analysis['signal']
            position_size_usd = analysis['position_size_usd']

            # Validate signal
            if signal not in [1, -1]:
                logger.error(f"Invalid signal value: {signal}")
                return

            # Validate position size
            if position_size_usd <= 0:
                logger.error(f"Invalid position size: ${position_size_usd}")
                return

            # Correlation check
            corr_check = self.correlation.is_correlated_with_open_positions(symbol)
            if not corr_check['allowed']:
                logger.info(f"Correlation filter blocked {symbol}: {corr_check['reason']}")
                return

            # Portfolio-level exposure cap (pre-trade rules engine)
            exposure_check = self.portfolio.can_open(symbol, position_size_usd, signal)
            if not exposure_check['allowed']:
                logger.info(f"Exposure cap blocked {symbol}: {exposure_check['reason']}")
                return

            # Calculate lot size
            current_price = analysis['current_price']
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return

            lot_size = position_size_usd / (current_price * symbol_info.trade_contract_size)
            lot_size = max(symbol_info.volume_min, min(symbol_info.volume_max, lot_size))

            # Calculate SL/TP
            atr = self.fe.calculate_atr(self.mt5.get_data(symbol, self.timeframe, bars=100))
            sl_distance = atr * 1.5
            tp_distance = atr * 2.5

            if signal == 1:  # BUY
                sl_price = current_price - sl_distance
                tp_price = current_price + tp_distance
                order_type = 'buy'
            else:  # SELL
                sl_price = current_price + sl_distance
                tp_price = current_price - tp_distance
                order_type = 'sell'

            # Shadow mode or live execution
            if ShadowModeToggle.is_shadow_mode():
                from rag.data_schemas import ProposedTrade

                proposed_trade = ProposedTrade(
                    symbol=symbol,
                    direction=signal,
                    entry_price=current_price,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    position_size_usd=position_size_usd,
                    lot_size=lot_size,
                    regime=analysis['regime'].regime_type,
                    confidence=0.7,  # Combined confidence
                    news_driven=analysis['news_features'] is not None,
                    timestamp=datetime.now(timezone.utc)
                )

                self.shadow_logger.log_proposed_trade(proposed_trade)
                self.journal.log_trade(
                    symbol=symbol,
                    direction=signal,
                    mode='shadow',
                    entry_price=current_price,
                    lot_size=lot_size,
                    position_size_usd=position_size_usd,
                    regime=analysis['regime'].regime_type,
                    news_driven=analysis['news_features'] is not None,
                )

                # Track in correlation filter even in shadow mode
                self.correlation.add_position(symbol, signal)
                self.portfolio.register_position(symbol, position_size_usd, signal)
                self.risk_gates.increment_open_trades()

                print(f"\n🔮 SHADOW TRADE LOGGED: {symbol} {order_type.upper()}")
                print(f"   Size: ${position_size_usd:.2f} ({lot_size:.2f} lots)")
                print(f"   Entry: {current_price:.5f}")
                print(f"   SL: {sl_price:.5f} | TP: {tp_price:.5f}")

            else:
                # LIVE EXECUTION
                result = self.hands.execute_order(
                    symbol=symbol,
                    order_type=order_type,
                    lot_size=lot_size,
                    sl_price=sl_price,
                    tp_price=tp_price
                )

                if result['success']:
                    self.trades_today += 1
                    self.risk_gates.increment_open_trades()
                    self.journal.log_trade(
                        symbol=symbol,
                        direction=signal,
                        mode='live',
                        entry_price=current_price,
                        lot_size=lot_size,
                        position_size_usd=position_size_usd,
                        regime=analysis['regime'].regime_type,
                        news_driven=analysis['news_features'] is not None,
                        reason=str(result.get('ticket')),
                    )

                    # Track in correlation filter
                    self.correlation.add_position(symbol, signal)
                    self.portfolio.register_position(symbol, position_size_usd, signal)

                    # Track in position manager
                    self.manager.add_trade(
                        ticket=result.get('ticket'),
                        symbol=symbol,
                        entry=current_price,
                        sl=sl_price,
                        tp=tp_price,
                        type=signal
                    )

                    print(f"\n✅ TRADE EXECUTED: {symbol} {order_type.upper()}")
                    print(f"   Ticket: {result.get('ticket')}")
                    print(f"   Size: ${position_size_usd:.2f}")
                else:
                    print(f"\n❌ Trade failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error executing trade: {e}")

    def run(self):
        """Main trading loop"""
        print("\n" + "="*60)
        print("🤖 QUANTEDGE V6 TRADING LOOP STARTED")
        print("="*60)

        cycle = 0

        while True:
            try:
                cycle += 1
                print(f"\n{'='*60}")
                print(f"📊 CYCLE #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")

                # Check kill switch with LIVE equity, not a startup snapshot
                live_account = mt5.account_info()
                current_balance = live_account.equity if live_account else self.account_balance
                kill_switch = self.risk_gates.check_kill_switch(current_balance)
                if kill_switch['triggered']:
                    print(f"\n🔴 KILL SWITCH TRIGGERED!")
                    print(f"   {kill_switch['reason']}")
                    print(f"   Daily Loss: {kill_switch['daily_loss_pct']:.2f}%")
                    break

                # Session filter
                if not self.time_machine.is_trading_allowed(datetime.now(timezone.utc)):
                    print("\n\U0001f4a4 Outside trading session (config) - waiting 5 minutes...")
                    time.sleep(300)
                    continue

                # Refresh news every 10 cycles (~5 minutes)
                if cycle % 10 == 1:
                    print("\n📰 Refreshing news...")
                    self.refresh_news()

                # Check for high-impact economic events
                upcoming_events = self.calendar.get_upcoming_events(minutes_ahead=60)
                high_impact = [e for e in upcoming_events if e['impact'] == 'high']

                if high_impact:
                    print(f"\n⚠️  {len(high_impact)} high-impact events in next hour")
                    print(f"   Proceeding with caution...")

                # Analyze all symbols
                opportunities = []

                print(f"\n🔍 Scanning {len(self.watchlist)} symbols...")
                for symbol in self.watchlist:
                    analysis = self.analyze_symbol(symbol)
                    if analysis:
                        opportunities.append(analysis)

                print(f"   Found {len(opportunities)} opportunities")

                # Sort by conviction (could use composite score)
                opportunities.sort(
                    key=lambda x: (
                        x['jump_probability'] if x['news_features'] else 0,
                        x['regime'].stability_score
                    ),
                    reverse=True
                )

                # Execute top opportunities
                for opp in opportunities[:5]:  # Top 5
                    if self.trades_today >= self.max_trades_per_day:
                        print(f"\n⏸️  Daily trade limit reached ({self.max_trades_per_day})")
                        break

                    print(f"\n💡 Opportunity: {opp['symbol']}")
                    print(f"   Regime: {opp['regime'].regime_type}")
                    print(f"   Signal: {'BUY' if opp['signal'] == 1 else 'SELL'}")
                    print(f"   Jump Prob: {opp['jump_probability']:.1%}")

                    self.execute_trade(opp)

                # Manage existing positions
                print(f"\n📋 Managing positions...")
                self.manager.manage_trades()

                # Performance summary
                if cycle % 20 == 0:
                    print("\n" + "="*60)
                    print("📈 PERFORMANCE SUMMARY")
                    print("="*60)
                    self.risk_gates.print_status()

                    if ShadowModeToggle.is_shadow_mode():
                        self.shadow_logger.print_performance()

                # Sleep
                print(f"\n💤 Sleeping 30 seconds...")
                time.sleep(30)

            except KeyboardInterrupt:
                print("\n\n⚠️  Shutdown requested...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(30)

        print("\n" + "="*60)
        print("🛑 QUANTEDGE V6 STOPPED")
        print("="*60)


def main():
    """Entry point with command-line arguments"""
    parser = argparse.ArgumentParser(description='QuantEdge - RAG Intelligence Trading System')

    parser.add_argument(
        '--config',
        default=None,
        help='Path to config.json (default: quantedge/config.json)'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Enable LIVE trading (default: shadow mode)'
    )

    parser.add_argument(
        '--balance',
        type=float,
        default=None,
        help='Account balance override in USD (default: from config)'
    )

    args = parser.parse_args()

    from utils.config import load_config, resolve_timeframe
    config = load_config(args.config)

    balance = args.balance if args.balance is not None else config['account']['balance']
    self_timeframe = resolve_timeframe(config['timeframe'])

    # Initialize bot
    bot = QuantEdgeV6(
        account_balance=balance,
        use_manual_balance=True,
        shadow_mode=not args.live,
        config=config,
    )

    # Run
    bot.run()


if __name__ == "__main__":
    main()

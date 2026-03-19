# QuantEdge V4 - Ultimate Features Documentation

## 🚀 Overview

QuantEdge V4 is the most advanced version of the trading system, integrating cutting-edge algorithmic trading features:

---

## 🧬 1. Genetic Algorithm Optimizer

**File:** `utils/genetic_optimizer.py`

### What It Does
Uses evolutionary algorithms to optimize trading parameters automatically.

### How It Works
- Creates a population of trading strategies with different parameters
- Evaluates each strategy using a fitness function (return, Sharpe ratio, drawdown)
- Breeds the best strategies together (crossover)
- Introduces random mutations for exploration
- Evolves over multiple generations to find optimal parameters

### Key Parameters Optimized
- `risk_per_trade`: How much to risk per trade (1-5%)
- `atr_multiplier`: Stop loss distance multiplier
- `confidence_threshold`: Minimum confidence to trade
- `tp_ratio`: Take profit ratio (risk:reward)
- `max_trades_per_day`: Maximum daily trades
- `volatility_filter`: ATR threshold for entry

### Usage
```python
from utils.genetic_optimizer import GeneticOptimizer

optimizer = GeneticOptimizer(population_size=50, generations=100)

def backtest_function(params):
    # Run backtest with params
    return {'total_return': 15, 'sharpe_ratio': 1.8, 'max_drawdown': -8, 'win_rate': 0.58}

best_params = optimizer.evolve(backtest_function)
print(f"Optimized Parameters: {best_params}")
```

---

## ⏰ 2. Time Machine (Session Filter)

**File:** `time_machine.py`

### What It Does
Filters trades based on market session and liquidity conditions.

### Key Features
- **Session Detection**: London Open, NY Open, Overlap, etc.
- **Weekend Filter**: Blocks trading on Saturday/Sunday
- **Rollover Avoidance**: Avoids 5pm EST rollover period
- **High Volatility Detection**: Identifies optimal trading windows

### Trading Sessions (UTC)
- **London Open**: 07:00-09:00 (High Volatility) ⚡
- **London Main**: 09:00-12:00
- **Overlap**: 12:00-13:00 (Highest Liquidity) 💰
- **NY Open**: 13:00-15:00 (High Volatility) ⚡
- **NY Main**: 15:00-18:00

### Usage
```python
from time_machine import TimeMachine
from datetime import datetime

tm = TimeMachine()

current_time = datetime.utcnow()

if tm.is_trading_allowed(current_time):
    print("✅ Trading Allowed")

if tm.is_high_volatility_period(current_time):
    print("🔥 High Volatility Window - Sniper Mode!")
```

---

## 🎯 3. Sniper Mode (High Volatility + News Arbitrage)

**File:** `utils/sniper_mode.py`

### What It Does
Detects compression patterns and explosive breakouts for high-probability trades.

### Key Features

#### A. Compression Detection
- Bollinger Band squeeze detection
- Triangle/consolidation patterns
- ATR-based volatility measurement

#### B. Breakout Detection
- Volume-confirmed breakouts
- Resistance/support breaks
- Momentum validation

#### C. News Arbitrage
- Tracks upcoming news events
- Avoids trading during high-impact news
- Identifies pre-news positioning opportunities

### Usage
```python
from utils.sniper_mode import SniperMode
from datetime import datetime, timedelta

sniper = SniperMode(lookback=50)

# Add news event
news_time = datetime.utcnow() + timedelta(minutes=30)
sniper.add_news_event(news_time, 'USD', 'high')

# Get signal
signal = sniper.get_sniper_signal(df, datetime.utcnow())

if signal['should_trade']:
    print(f"🎯 SNIPER SIGNAL: {signal['reason']}")
    print(f"   Confidence: {signal['confidence']:.2f}")
```

---

## 🤖 4. NLP Bag-of-Words (BTC-ETH Sentiment)

**File:** `features/nlp_sentiment.py`

### What It Does
Analyzes BTC and ETH price action to generate sentiment features for forex trading.

### How It Works

#### A. Price-to-Words Conversion
Converts price patterns into "words":
- **Bullish Words**: breakout, rally, surge, pump, moon
- **Bearish Words**: breakdown, crash, dump, capitulation
- **Neutral Words**: consolidation, ranging, sideways

#### B. Sentiment Scoring
- Calculates bullish/bearish scores (0-1)
- Generates overall sentiment (bullish/bearish/neutral)

#### C. Correlation Analysis
- Measures BTC-ETH correlation
- Detects divergences (opportunity signals)
- Generates crypto sentiment features

### Trading Signals
1. **Crypto Bullish**: BTC and ETH both bullish → Risk-on (buy EURUSD)
2. **Crypto Bearish**: BTC and ETH both bearish → Risk-off (sell EURUSD, buy Gold)
3. **BTC Strong ETH Weak**: Divergence → Volatility opportunity
4. **ETH Strong BTC Weak**: Divergence → Fade the weak

### Usage
```python
from features.nlp_sentiment import NLPSentimentAnalyzer

nlp = NLPSentimentAnalyzer()

analysis = nlp.analyze_btc_eth_correlation(df_btc, df_eth)

print(f"Correlation: {analysis['correlation']:.2f}")
print(f"Divergence: {analysis['divergence']:.2f}")
print(f"Signal: {analysis['signal']}")
print(f"BTC Sentiment: {analysis['btc_sentiment']['sentiment']}")
print(f"ETH Sentiment: {analysis['eth_sentiment']['sentiment']}")
```

---

## 🛡️ 5. Relim Shield (Dynamic Confidence Threshold)

**File:** `utils/relim_shield.py`

### What It Does
Adaptively adjusts the minimum confidence threshold based on recent performance.

### How It Works

#### Performance Metrics
- **Win Rate**: % of winning trades
- **Profit Factor**: Gross profit / Gross loss
- **Average Confidence**: Mean confidence of recent trades

#### Adaptive Logic
1. **Good Performance** (Win Rate > 60%, PF > 1.5)
   - Lower threshold → Take more trades

2. **Poor Performance** (Win Rate < 40%, PF < 1.0)
   - Raise threshold → Be more selective

3. **Marginal Performance** (Win Rate 40-50%)
   - Slightly raise threshold → Tighten standards

### Configuration
- **Initial Threshold**: 0.60 (60%)
- **Min Threshold**: 0.50 (50%)
- **Max Threshold**: 0.80 (80%)
- **Lookback**: Last 20 trades

### Usage
```python
from utils.relim_shield import RelimShield

shield = RelimShield(initial_threshold=0.60)

# Record trade result
shield.add_trade_result(confidence=0.65, outcome='win', pnl=50.0)

# Update threshold based on performance
shield.update_threshold()

# Check if trade is approved
if shield.should_trade(confidence=0.58):
    print("✅ Trade approved by Shield")

shield.print_status()
```

---

## 📊 6. Dynamic Stop Loss Management

**File:** `utils/dynamic_stop_loss.py`

### What It Does
Advanced stop loss system using multiple strategies for optimal risk management.

### Stop Loss Strategies

#### A. ATR Stop
- Basic stop using ATR multiplier
- Simple and effective

#### B. Volatility-Adjusted Stop
- Widens stops in high volatility
- Tightens stops in low volatility
- Adapts to market conditions

#### C. Time-Based Stop
- Tightens stop the longer you hold
- "Cut losers early" philosophy
- 0-5 bars: 1.5 ATR
- 5-10 bars: 1.2 ATR
- 10+ bars: 1.0 ATR

#### D. Chandelier Stop
- Uses highest high / lowest low
- More dynamic than fixed ATR
- Trails with market structure

#### E. Parabolic SAR
- Accelerating trailing stop
- Follows trend momentum

#### F. Hybrid (RECOMMENDED)
- Combines ALL methods
- Uses the tightest (most conservative) stop
- Best overall protection

### Automatic Stop Management
- **Breakeven at +10 pips**: Locks in zero risk
- **Trailing at +30 pips**: Protects profits
- **Time decay**: Cuts losing trades faster

### Usage
```python
from utils.dynamic_stop_loss import DynamicStopLoss

sl_manager = DynamicStopLoss(base_atr_multiplier=1.5)

# Calculate optimal stop
result = sl_manager.get_optimal_stop(
    entry_price=1.0850,
    atr=0.0015,
    current_vol=0.0018,
    target_vol=0.0015,
    direction=1,  # Buy
    bars_held=3,
    df=df,
    strategy='hybrid'
)

print(f"Final Stop Loss: {result['final_stop']}")
print(f"Strategy Used: {result['strategy_used']}")
```

---

## 🤖 7. Integration: Bot V4 Ultimate

**File:** `bot_v4_ultimate.py`

### The Complete System
Combines ALL features into one powerful trading bot.

### Execution Flow
1. **Drawdown Guard**: Check daily loss limit
2. **Time Machine**: Verify trading session
3. **Data Fetch**: Get market data + crypto data
4. **Sniper Analysis**: Check for compression/breakout
5. **NLP Analysis**: Analyze BTC-ETH sentiment
6. **Feature Engineering**: Calculate 80+ features
7. **Brain Prediction**: ML model prediction
8. **Relim Shield**: Dynamic confidence filter
9. **Dynamic Stop Loss**: Calculate optimal SL
10. **Position Sizing**: Calculate lot size
11. **Execute Trade**: Send order (or paper trade)
12. **Position Management**: Breakeven/trailing

### Running the Bot
```bash
cd OneDrive/quantedge
python bot_v4_ultimate.py
```

---

## 📈 Performance Enhancements

### Expected Improvements Over V3
- **Win Rate**: +5-10% (better entry timing)
- **Sharpe Ratio**: +0.5-1.0 (better risk management)
- **Max Drawdown**: -3-5% (dynamic stops + shield)
- **Profit Factor**: +0.3-0.5 (quality over quantity)

### Key Advantages
1. **Adaptive**: System learns and adjusts
2. **Robust**: Multiple layers of protection
3. **Intelligent**: Uses ML + NLP + Genetic algorithms
4. **Professional**: Hedge fund-level features

---

## 🛠️ Configuration & Optimization

### Genetic Algorithm Optimization
Run genetic optimization to find best parameters for your broker/account:

```python
from utils.genetic_optimizer import GeneticOptimizer

optimizer = GeneticOptimizer(population_size=100, generations=200)
best_params = optimizer.evolve(your_backtest_function)

# Apply to bot
bot = QuantEdgeV4(account_balance=10000)
bot.sizer.risk_per_trade = best_params['risk_per_trade']
bot.shield.threshold = best_params['confidence_threshold']
```

### Backtesting Recommended
Before live trading:
1. Run genetic optimization on 6 months of data
2. Walk-forward test on 2 months out-of-sample
3. Paper trade for 1 week
4. Start live with minimum lot size

---

## ⚠️ Important Notes

### Paper Trading Mode
By default, all bots run in **paper trading mode** (safe). To enable live trading:

```python
# In bot_v4_ultimate.py, uncomment:
ticket = self.hands.send_order(symbol, signal, lot, sl, tp)
```

### Risk Warning
- Start with small account or demo
- Never risk more than 2% per trade
- Monitor drawdown guard carefully
- Test extensively before going live

---

## 📚 Further Reading

- [Genetic Algorithms in Trading](https://www.investopedia.com/articles/trading/10/genetic-algorithms-optimizer.asp)
- [Session-Based Trading](https://www.babypips.com/learn/forex/market-hours)
- [NLP in Finance](https://towardsdatascience.com/nlp-for-trading)
- [Dynamic Stop Losses](https://www.investopedia.com/articles/trading/09/adaptive-stop-loss.asp)

---

**Version**: 4.0.0
**Last Updated**: 2026-01-23
**Author**: QuantEdge Team
**License**: MIT

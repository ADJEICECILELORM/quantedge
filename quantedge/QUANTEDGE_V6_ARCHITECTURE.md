# QuantEdge V6.0 - RAG Intelligence Architecture

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        QUANTEDGE V6.0                               │
│              Institutional-Grade News Intelligence                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  1. DATA INGESTION & SOURCE SCORING LAYER                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Reuters API │  │ Twitter/Reddit│  │  Economic    │             │
│  │  (Premium)   │  │  (Fast)       │  │  Calendars   │             │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────┘             │
│         │                 │                   │                     │
│         └─────────────────┴───────────────────┘                     │
│                             │                                       │
│                    ┌────────▼─────────┐                             │
│                    │  NewsIngestion   │                             │
│                    │   Orchestrator   │                             │
│                    └────────┬─────────┘                             │
│                             │                                       │
│                    ┌────────▼─────────┐                             │
│                    │  SourceScoring   │                             │
│                    │     Engine       │                             │
│                    │  - Speed         │                             │
│                    │  - Credibility   │                             │
│                    │  - Sensitivity   │                             │
│                    │  - Manipulation  │                             │
│                    └────────┬─────────┘                             │
│                             │                                       │
│                    Structured JSON Events                           │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  2. RAG INTELLIGENCE LAYER (Vector Database)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │              Qdrant Vector Database                     │       │
│  │        (fastembed: bge-small-en-v1.5)                   │       │
│  └─────────────────────────────────────────────────────────┘       │
│                             │                                       │
│                    ┌────────▼─────────┐                             │
│                    │   RAGRetriever   │                             │
│                    │  - Semantic      │                             │
│                    │    Search        │                             │
│                    │  - Time-weighted │                             │
│                    │  - Top 3-5       │                             │
│                    │    Similar       │                             │
│                    └────────┬─────────┘                             │
│                             │                                       │
│                    ┌────────▼─────────┐                             │
│                    │  FeatureExtract  │                             │
│                    │  - event_type    │                             │
│                    │  - sentiment     │                             │
│                    │  - novelty       │                             │
│                    │  - impact        │                             │
│                    │  - confidence    │                             │
│                    │  - source_score  │                             │
│                    │  - time_decay    │                             │
│                    └────────┬─────────┘                             │
│                             │                                       │
│                   Structured Features                               │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  3. REGIME & EVENT CLASSIFICATION                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────┐        │
│  │           RegimeClassifier                             │        │
│  │  - Trend/Momentum      (use trend-following)           │        │
│  │  - Mean Reversion      (use counter-trend)             │        │
│  │  - Volatility Expansion (use breakouts)                │        │
│  │  - Low Volatility      (reduce positions)              │        │
│  │                                                         │        │
│  │  RAG → Regime Detection (NOT direct trading)           │        │
│  └────────────────────────────────────────────────────────┘        │
│                             │                                       │
│                    Active Regime Signal                             │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  4. QUANTITATIVE MATHEMATICAL ENGINE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  JumpDiffusion   │  │ InfoDecay        │  │ KellyCriterion   │ │
│  │  (Merton Model)  │  │ I(t) = I0*e^-kt  │  │ (Dynamic)        │ │
│  │                  │  │                  │  │                  │ │
│  │ P(jump | news)   │  │ Alpha half-life  │  │ f* = (p*b-q)/b   │ │
│  │                  │  │ timing           │  │ + RAG confidence │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                     │
│  Each module declares:                                              │
│  - Assumptions (e.g., log-normal returns)                           │
│  - Valid regimes (e.g., high volatility only)                       │
│  - Required inputs (e.g., ATR, news impact score)                   │
│  - Failure modes (e.g., insufficient data)                          │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  5. INSTITUTIONAL MICROSTRUCTURE MODULE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  VPIN (Volume-Synchronized Probability Informed Trading)│       │
│  │  - Toxicity filter                                       │       │
│  │  - Block trades when VPIN > 90th percentile             │       │
│  │  - Insider trading detection                            │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Lead-Lag Correlation (Enhanced)                        │       │
│  │  - 1-min rolling correlation: DXY, XAU, BTC            │       │
│  │  - If DXY/XAU leads and BTC lags by 500ms              │       │
│  │  - Trigger front-run signal                             │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Pairs Trading (Delta-Neutral Hedging)                  │       │
│  │  - Long Gold / Short Bitcoin                            │       │
│  │  - For medium-confidence news                           │       │
│  │  - Neutralize USD exposure                              │       │
│  └─────────────────────────────────────────────────────────┘       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  6. GENETIC ALGORITHM OPTIMIZER (Constrained)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ONLY Optimizes:                                                    │
│  ✓ Parameters (stop-loss X, take-profit Y)                          │
│  ✓ Weights (RAG 60%, Math 40%)                                      │
│  ✓ Thresholds (RAG similarity > 0.7, VPIN < 0.9)                    │
│  ✓ Strategy selection (which regime uses which model)               │
│                                                                     │
│  EXPLICITLY FORBIDS:                                                │
│  ✗ Random formula invention                                         │
│  ✗ Unconstrained indicator mixing                                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Chromosome Structure:                                  │       │
│  │  [stop_loss_mult, rag_threshold, news_weight, ...]     │       │
│  │  Gene ranges: [1.0-3.0], [0.5-0.9], [0.3-0.7]          │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Fitness Function (NOT profit-only):                   │       │
│  │  - Risk-adjusted returns (Sortino Ratio)               │       │
│  │  - Drawdown penalties                                   │       │
│  │  - Overtrading penalties                                │       │
│  │  - Stability across regimes                             │       │
│  │  - Consistency over time                                │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│  Updates config.json every cycle                                    │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  7. SAFETY & CONTROL LAYER                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Hard Constraints:                                                  │
│  - Capital exposure limits (max 10% per trade)                      │
│  - Kill-switch logic (stop on 5% daily loss)                        │
│  - GA update rate limits (once per 24h max)                         │
│  - Human override hooks                                             │
│                                                                     │
│  GA Must NEVER Modify:                                              │
│  ✗ Data sources                                                     │
│  ✗ RAG logic                                                        │
│  ✗ Execution engine                                                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  Shadow Mode Toggle:                                    │       │
│  │  - Allow new modules to log 'Proposed Trades'          │       │
│  │  - WITHOUT executing                                    │       │
│  │  - For safe testing                                     │       │
│  └─────────────────────────────────────────────────────────┘       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  8. TRADE DECISION ENGINE (Abstracted)                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Inputs:                                                            │
│  - RAG features                                                     │
│  - Regime classification                                            │
│  - Quant model outputs                                              │
│  - Microstructure filters (VPIN, lead-lag)                          │
│  - GA-optimized parameters                                          │
│  - Risk controls                                                    │
│                                                                     │
│  Output:                                                            │
│  - Trade decision (buy/sell/hold)                                   │
│  - Position size (Kelly-adjusted)                                   │
│  - Stop loss / Take profit                                          │
│  - Confidence score                                                 │
│                                                                     │
│  If Shadow Mode:                                                    │
│  → Log to shadow_trades.json                                        │
│  Else:                                                              │
│  → Execute via MT5                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow

```
News Event
    ↓
Source Scoring (speed, credibility, manipulation risk)
    ↓
Store in Qdrant (vector embeddings)
    ↓
Query for similar events (semantic search)
    ↓
Extract structured features (sentiment, impact, novelty)
    ↓
Classify market regime (trend/reversion/volatility)
    ↓
Select quant models (jump-diffusion, info decay, Kelly)
    ↓
Apply microstructure filters (VPIN, lead-lag, pairs)
    ↓
GA-optimized parameters (stop-loss, thresholds, weights)
    ↓
Risk controls & safety layer
    ↓
Trade decision → Execute or Shadow Log
```

---

## 🎯 Module Interfaces

### 1. NewsIngestionOrchestrator
```python
class NewsIngestionOrchestrator:
    def __init__(self, sources: List[NewsSource])
    def fetch_news(self) -> List[RawNewsEvent]
    def process_event(self, raw_event: RawNewsEvent) -> StructuredNewsEvent
    def get_latest_events(self, minutes: int = 60) -> List[StructuredNewsEvent]
```

### 2. SourceScoringEngine
```python
class SourceScoringEngine:
    def score_source(self, source_name: str) -> SourceScore
    def calculate_composite_score(self, scores: SourceScore) -> float

class SourceScore:
    speed_score: float          # 0-1 (latency)
    credibility_score: float    # 0-1 (accuracy history)
    sensitivity_score: float    # 0-1 (market impact)
    manipulation_risk: float    # 0-1 (manipulation likelihood)
    composite_score: float      # Weighted average
```

### 3. RAGRetriever
```python
class RAGRetriever:
    def __init__(self, vector_db: QdrantClient)
    def store_event(self, event: StructuredNewsEvent)
    def retrieve_similar(self, query: str, top_k: int = 5) -> List[StructuredNewsEvent]
    def get_time_weighted_results(self, results: List, decay_hours: float = 24) -> List
```

### 4. FeatureExtractor
```python
class FeatureExtractor:
    def extract_features(self, event: StructuredNewsEvent, similar_events: List) -> NewsFeatures

class NewsFeatures:
    event_type: str            # 'rate_decision', 'earnings', 'geopolitical'
    sentiment: float           # -1 to +1
    novelty_score: float       # 0-1 (how unique is this event)
    impact_score: float        # 0-1 (expected market impact)
    confidence: float          # 0-1 (how confident are we)
    source_score_composite: float
    time_decay_factor: float   # Based on event age
```

### 5. RegimeClassifier
```python
class RegimeClassifier:
    def classify(self, market_data: pd.DataFrame, news_features: NewsFeatures) -> MarketRegime

class MarketRegime(Enum):
    TREND_MOMENTUM = "trend"
    MEAN_REVERSION = "reversion"
    VOLATILITY_EXPANSION = "volatility"
    LOW_VOLATILITY = "low_vol"
```

### 6. JumpDiffusionModel
```python
class JumpDiffusionModel:
    """Merton's Jump-Diffusion Model for news-driven price jumps"""

    # Assumptions
    ASSUMPTIONS = ["Log-normal returns", "Poisson jump arrivals", "Independent jumps"]
    VALID_REGIMES = [MarketRegime.VOLATILITY_EXPANSION]
    REQUIRED_INPUTS = ["current_price", "volatility", "news_impact_score"]
    FAILURE_MODES = ["Insufficient volatility history", "No recent jumps for calibration"]

    def calculate_jump_probability(self, news_impact: float, volatility: float) -> float
    def estimate_jump_size(self, news_sentiment: float) -> float
```

### 7. InformationDecayModel
```python
class InformationDecayModel:
    """I(t) = I0 * exp(-kt) - Alpha half-life for news"""

    def calculate_decay(self, initial_impact: float, hours_elapsed: float, k: float = 0.1) -> float
    def get_alpha_half_life(self, k: float) -> float  # ln(2) / k
```

### 8. VPINFilter
```python
class VPINFilter:
    """Volume-Synchronized Probability of Informed Trading"""

    def calculate_vpin(self, df: pd.DataFrame) -> float
    def is_toxic(self, vpin: float, threshold_percentile: float = 90) -> bool
    def should_block_trade(self, vpin: float) -> bool
```

### 9. ConstrainedGeneticAlgorithm
```python
class ConstrainedGeneticAlgorithm:
    def __init__(self, gene_ranges: Dict[str, Tuple[float, float]])
    def create_population(self, size: int) -> List[Chromosome]
    def mutate(self, chromosome: Chromosome, bounds: Dict) -> Chromosome
    def crossover(self, parent1: Chromosome, parent2: Chromosome) -> Chromosome
    def fitness(self, chromosome: Chromosome, trade_history: List) -> float
    def evolve(self, generations: int) -> Chromosome
    def export_config(self, best_chromosome: Chromosome, filepath: str)
```

### 10. ShadowModeLogger
```python
class ShadowModeLogger:
    def __init__(self, log_file: str = "data/shadow_trades.json")
    def log_proposed_trade(self, trade: ProposedTrade)
    def get_shadow_performance(self) -> Dict
```

---

## 📦 Dependencies

```python
# Core
qdrant-client      # Vector database
fastembed          # Embeddings (bge-small-en-v1.5)
numpy
scipy
pandas

# News ingestion
requests           # API calls
beautifulsoup4     # Web scraping
tweepy             # Twitter API (optional)
praw               # Reddit API (optional)

# Existing
MetaTrader5
ta
scikit-learn
xgboost
joblib
```

---

## 🔒 Constraints

1. **No guaranteed-profit claims**
2. **No black-box logic** - All decisions explainable
3. **No end-to-end automation without risk gates**
4. **Must be suitable for backtesting with historical news replay**
5. **Global, multi-language inputs** (timestamp normalization required)

---

## 📁 File Structure

```
quantedge/
├── rag/                          # NEW: RAG Intelligence
│   ├── __init__.py
│   ├── news_ingestion.py
│   ├── source_scoring.py
│   ├── rag_retriever.py
│   ├── feature_extractor.py
│   └── regime_classifier.py
│
├── quant/                        # NEW: Quantitative Models
│   ├── __init__.py
│   ├── jump_diffusion.py
│   ├── information_decay.py
│   └── kelly_enhanced.py
│
├── microstructure/               # NEW: Market Microstructure
│   ├── __init__.py
│   ├── vpin_filter.py
│   ├── lead_lag_enhanced.py
│   └── pairs_trading.py
│
├── optimizer/                    # NEW: Constrained GA
│   ├── __init__.py
│   ├── genetic_algorithm.py
│   └── fitness_functions.py
│
├── safety/                       # NEW: Safety & Control
│   ├── __init__.py
│   ├── shadow_mode.py
│   └── risk_gates.py
│
├── data/
│   ├── qdrant_data/             # Vector DB storage
│   ├── shadow_trades.json       # Shadow mode logs
│   └── config_ga.json           # GA-optimized config
│
└── bot_v6_rag.py                # NEW: V6 bot with RAG
```

---

## 🎯 Implementation Phases

### Phase 1: Foundation (Session 1)
- [x] Architecture design ✓
- [ ] NewsIngestionOrchestrator
- [ ] SourceScoringEngine
- [ ] Setup Qdrant vector DB

### Phase 2: RAG Core (Session 2)
- [ ] RAGRetriever
- [ ] FeatureExtractor
- [ ] RegimeClassifier

### Phase 3: Quant Models (Session 3)
- [ ] JumpDiffusionModel
- [ ] InformationDecayModel
- [ ] Enhanced KellyCriterion

### Phase 4: Microstructure (Session 4)
- [ ] VPINFilter
- [ ] Enhanced LeadLag
- [ ] PairsTrading

### Phase 5: Optimization & Safety (Session 5)
- [ ] ConstrainedGeneticAlgorithm
- [ ] ShadowModeLogger
- [ ] Integration with V5 bot

---

**Next**: Implement Phase 1 modules

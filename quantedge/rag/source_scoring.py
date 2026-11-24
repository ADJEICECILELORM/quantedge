# rag/source_scoring.py - Source Credibility & Performance Scoring
import logging
from typing import Dict, Optional
from datetime import datetime
import json
import os
from collections import defaultdict, deque

from rag.data_schemas import SourceScore, SourceType

logger = logging.getLogger(__name__)


class SourceScoringEngine:
    """
    Scores news sources based on:
    - Speed (latency vs competitors)
    - Credibility (historical accuracy)
    - Market Sensitivity (impact correlation)
    - Manipulation Risk (likelihood of fake news)
    """

    def __init__(self, config_path: str = "data/source_scoring_config.json"):
        self.config_path = config_path
        self.source_history = defaultdict(lambda: {
            'latencies': deque(maxlen=100),
            'accuracy_scores': deque(maxlen=100),
            'market_impacts': deque(maxlen=100),
            'manipulation_flags': deque(maxlen=100)
        })

        # Default source profiles
        self.source_profiles = {
            # Authoritative sources (high credibility, slower)
            'Reuters': {'speed': 0.7, 'credibility': 0.95, 'sensitivity': 0.9, 'manipulation_risk': 0.05},
            'Bloomberg': {'speed': 0.75, 'credibility': 0.95, 'sensitivity': 0.9, 'manipulation_risk': 0.05},
            'Federal Reserve': {'speed': 0.6, 'credibility': 1.0, 'sensitivity': 0.95, 'manipulation_risk': 0.0},
            'ECB': {'speed': 0.6, 'credibility': 1.0, 'sensitivity': 0.95, 'manipulation_risk': 0.0},

            # Fast public sources (lower credibility, faster)
            'Twitter': {'speed': 0.95, 'credibility': 0.4, 'sensitivity': 0.7, 'manipulation_risk': 0.7},
            'Reddit': {'speed': 0.9, 'credibility': 0.3, 'sensitivity': 0.6, 'manipulation_risk': 0.8},
            'Telegram': {'speed': 0.95, 'credibility': 0.35, 'sensitivity': 0.65, 'manipulation_risk': 0.75},

            # Scheduled feeds (predictable, high credibility)
            'Economic Calendar': {'speed': 0.5, 'credibility': 0.9, 'sensitivity': 0.85, 'manipulation_risk': 0.1},
            'Earnings Calendar': {'speed': 0.5, 'credibility': 0.85, 'sensitivity': 0.8, 'manipulation_risk': 0.1},
        }

        # Weights for composite score
        self.weights = {
            'speed': 0.20,
            'credibility': 0.40,
            'sensitivity': 0.25,
            'manipulation_risk': -0.15  # Negative weight (higher risk = lower score)
        }

        self.load_config()

    def load_config(self):
        """Load source profiles from config file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    if 'source_profiles' in config:
                        self.source_profiles.update(config['source_profiles'])
                    if 'weights' in config:
                        self.weights.update(config['weights'])
                logger.info(f"Loaded source scoring config from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading source config: {e}")

    def save_config(self):
        """Save source profiles to config file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            config = {
                'source_profiles': self.source_profiles,
                'weights': self.weights,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved source scoring config to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving source config: {e}")

    def score_source(self, source_name: str, source_type: Optional[SourceType] = None) -> SourceScore:
        """
        Score a news source.

        Args:
            source_name: Name of the source (e.g., 'Reuters', 'Twitter')
            source_type: Type of source (optional, for fallback scoring)

        Returns:
            SourceScore with all metrics
        """
        # Get profile (use defaults if not found)
        profile = self.source_profiles.get(source_name)

        if profile is None:
            logger.warning(f"Unknown source: {source_name}, using fallback scoring")
            profile = self._get_fallback_profile(source_type)

        # Calculate composite score
        composite = (
            profile['speed'] * self.weights['speed'] +
            profile['credibility'] * self.weights['credibility'] +
            profile['sensitivity'] * self.weights['sensitivity'] +
            profile['manipulation_risk'] * self.weights['manipulation_risk']
        )

        # Normalize to 0-1 (since manipulation_risk has negative weight)
        # Min possible: 0*0.2 + 0*0.4 + 0*0.25 + 1*(-0.15) = -0.15
        # Max possible: 1*0.2 + 1*0.4 + 1*0.25 + 0*(-0.15) = 0.85
        # Range: 1.0
        composite_normalized = (composite + 0.15) / 1.0
        composite_normalized = max(0.0, min(1.0, composite_normalized))

        return SourceScore(
            source_name=source_name,
            speed_score=profile['speed'],
            credibility_score=profile['credibility'],
            sensitivity_score=profile['sensitivity'],
            manipulation_risk=profile['manipulation_risk'],
            composite_score=composite_normalized
        )

    def _get_fallback_profile(self, source_type: Optional[SourceType]) -> Dict[str, float]:
        """Get fallback profile based on source type"""
        if source_type == SourceType.REUTERS or source_type == SourceType.BLOOMBERG:
            return {'speed': 0.7, 'credibility': 0.9, 'sensitivity': 0.85, 'manipulation_risk': 0.1}
        elif source_type in [SourceType.TWITTER, SourceType.REDDIT, SourceType.TELEGRAM]:
            return {'speed': 0.9, 'credibility': 0.35, 'sensitivity': 0.65, 'manipulation_risk': 0.75}
        elif source_type in [SourceType.ECONOMIC_CALENDAR, SourceType.EARNINGS_CALENDAR]:
            return {'speed': 0.5, 'credibility': 0.9, 'sensitivity': 0.85, 'manipulation_risk': 0.1}
        else:
            # Unknown - conservative scoring
            return {'speed': 0.5, 'credibility': 0.5, 'sensitivity': 0.5, 'manipulation_risk': 0.5}

    def update_source_performance(
        self,
        source_name: str,
        latency_seconds: Optional[float] = None,
        accuracy: Optional[float] = None,
        market_impact: Optional[float] = None,
        was_manipulation: bool = False
    ):
        """
        Update source performance metrics based on observed behavior.

        Args:
            source_name: Name of the source
            latency_seconds: Time from event to delivery (lower is better)
            accuracy: Accuracy score 0-1 (if event was verified)
            market_impact: Observed market impact 0-1
            was_manipulation: Flag if event was fake/manipulation
        """
        history = self.source_history[source_name]

        if latency_seconds is not None:
            history['latencies'].append(latency_seconds)

        if accuracy is not None:
            history['accuracy_scores'].append(accuracy)

        if market_impact is not None:
            history['market_impacts'].append(market_impact)

        history['manipulation_flags'].append(1.0 if was_manipulation else 0.0)

        # Update source profile if enough data
        if len(history['latencies']) >= 10:
            self._update_source_profile(source_name)

    def _update_source_profile(self, source_name: str):
        """Update source profile based on historical performance"""
        history = self.source_history[source_name]

        if source_name not in self.source_profiles:
            self.source_profiles[source_name] = {
                'speed': 0.5,
                'credibility': 0.5,
                'sensitivity': 0.5,
                'manipulation_risk': 0.5
            }

        # Speed: Lower latency = higher score
        if history['latencies']:
            avg_latency = sum(history['latencies']) / len(history['latencies'])
            # Assume 60s is slow (score=0.3), 5s is fast (score=0.95)
            speed_score = max(0.3, min(0.95, 1.0 - (avg_latency / 60)))
            self.source_profiles[source_name]['speed'] = speed_score

        # Credibility: Average accuracy
        if history['accuracy_scores']:
            avg_accuracy = sum(history['accuracy_scores']) / len(history['accuracy_scores'])
            self.source_profiles[source_name]['credibility'] = avg_accuracy

        # Sensitivity: Average market impact
        if history['market_impacts']:
            avg_impact = sum(history['market_impacts']) / len(history['market_impacts'])
            self.source_profiles[source_name]['sensitivity'] = avg_impact

        # Manipulation risk: Fraction of manipulated events
        if history['manipulation_flags']:
            manip_rate = sum(history['manipulation_flags']) / len(history['manipulation_flags'])
            self.source_profiles[source_name]['manipulation_risk'] = manip_rate

        logger.info(f"Updated profile for {source_name}: {self.source_profiles[source_name]}")

        # Save updated config
        self.save_config()

    def get_all_source_scores(self) -> Dict[str, SourceScore]:
        """Get scores for all known sources"""
        return {
            source_name: self.score_source(source_name)
            for source_name in self.source_profiles.keys()
        }

    def print_source_rankings(self):
        """Print source rankings by composite score"""
        scores = self.get_all_source_scores()
        ranked = sorted(scores.items(), key=lambda x: x[1].composite_score, reverse=True)

        print("\n" + "="*80)
        print("📊 NEWS SOURCE RANKINGS")
        print("="*80)
        print(f"{'Rank':<6} {'Source':<20} {'Composite':<12} {'Speed':<8} {'Credibility':<12} {'Sensitivity':<12} {'Manip Risk':<12}")
        print("-"*80)

        for i, (source_name, score) in enumerate(ranked, 1):
            print(f"{i:<6} {source_name:<20} {score.composite_score:.3f}        "
                  f"{score.speed_score:.2f}     {score.credibility_score:.2f}         "
                  f"{score.sensitivity_score:.2f}         {score.manipulation_risk:.2f}")

        print("="*80 + "\n")

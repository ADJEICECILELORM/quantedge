# pipeline/inference_pipeline.py - ML Inference Pipeline (Optimized)
import joblib
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import os

# Import cache manager
try:
    from utils.cache_manager import cache_predictions
except ImportError:
    def cache_predictions(func):
        return func

logger = logging.getLogger(__name__)


class InferencePipeline:
    """
    ML Inference Pipeline with optimizations:
    - Singleton pattern (models loaded once)
    - Prediction caching
    - Better error handling
    - Type hints
    """

    _instance = None
    _models_loaded = False

    def __new__(cls):
        """Singleton pattern - only one instance with loaded models"""
        if cls._instance is None:
            cls._instance = super(InferencePipeline, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Only load models once
        if not InferencePipeline._models_loaded:
            self._load_models()
            InferencePipeline._models_loaded = True

        self.weights = {'rf': 0.40, 'xgb': 0.47, 'lr': 0.13}
        self.prediction_count = 0

    def _load_models(self):
        """Load ML models and scaler"""
        print("Loading Models...")
        try:
            # Check if model files exist
            model_dir = "models/saved"
            self.model_dir = model_dir
            required_files = ['scaler.pkl', 'rf_model.pkl', 'xgb_model.pkl', 'lr_model.pkl']

            for file in required_files:
                filepath = os.path.join(model_dir, file)
                if not os.path.exists(filepath):
                    raise FileNotFoundError(f"Model file not found: {filepath}")

            # Load scaler
            self.scaler = joblib.load(os.path.join(model_dir, "scaler.pkl"))

            # Load models
            self.models = {
                'rf': joblib.load(os.path.join(model_dir, "rf_model.pkl")),
                'xgb': joblib.load(os.path.join(model_dir, "xgb_model.pkl")),
                'lr': joblib.load(os.path.join(model_dir, "lr_model.pkl"))
            }

            # Load training metadata for feature validation
            from models.registry import load_metadata
            self.feature_metadata = load_metadata(model_dir)
            if self.feature_metadata:
                logger.info(
                    f"Loaded training metadata: {self.feature_metadata.get('n_features')} "
                    f"features, trained {self.feature_metadata.get('trained_at')}"
                )
            else:
                logger.warning(
                    "No model metadata found - feature validation disabled. "
                    "Retrain models to enable it."
                )

            # Feature drift monitoring (PSI against training distributions)
            self.drift_monitor = None
            try:
                from utils.drift_monitor import FeatureDriftMonitor
                self.drift_monitor = FeatureDriftMonitor(model_dir)
                if not self.drift_monitor.enabled:
                    logger.warning(
                        "Metadata has no feature_stats - drift monitoring disabled "
                        "(retrain models to enable)"
                    )
            except Exception as e:
                logger.warning(f"Drift monitor unavailable: {e}")

            # Warm up models (dummy prediction for JIT compilation)
            self._warmup_models()

            print("✅ Models Loaded Successfully.")
            logger.info("ML models loaded successfully")

        except FileNotFoundError as e:
            logger.error(f"Model file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise

    def _warmup_models(self):
        """Warm up models with dummy prediction (JIT compilation, cache warming)"""
        try:
            # Create dummy data matching expected feature count
            n_features = self.scaler.n_features_in_
            dummy_data = np.random.randn(1, n_features)

            # Run dummy prediction through each model
            for model in self.models.values():
                _ = model.predict_proba(dummy_data)

            logger.info("Models warmed up successfully")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")

    def predict(self, latest_features_df: pd.DataFrame) -> Dict:
        """
        Predict trading direction using ensemble of ML models.

        Args:
            latest_features_df: DataFrame with calculated features

        Returns:
            Dict with:
                - direction: int (1=buy, -1=sell, 0=neutral)
                - confidence: float (0-1)
                - model_votes: Dict (individual model predictions)
        """
        if latest_features_df is None or len(latest_features_df) == 0:
            logger.warning("Empty features DataFrame provided")
            return {'direction': 0, 'confidence': 0.5, 'model_votes': {}}

        try:
            # Exclude non-feature columns
            exclude_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'target', 'regime_label']
            feature_cols = [c for c in latest_features_df.columns if c not in exclude_cols]

            if not feature_cols:
                logger.error("No feature columns found in DataFrame")
                return {'direction': 0, 'confidence': 0.5, 'model_votes': {}}

            if getattr(self, 'feature_metadata', None):
                from models.registry import validate_features
                ok, msg = validate_features(self.model_dir, feature_cols)
                if not ok:
                    logger.error(f"Feature validation failed: {msg}")
                    return {'direction': 0, 'confidence': 0.5, 'model_votes': {}, 'validation_error': msg}

            X = latest_features_df[feature_cols]

            # Check for NaN/Inf values
            if X.isnull().any().any():
                logger.warning("NaN values found in features, filling with 0")
                X = X.fillna(0)

            if np.isinf(X.values).any():
                logger.warning("Inf values found in features, clipping")
                X = X.replace([np.inf, -np.inf], [1e10, -1e10])

            # Scale features
            try:
                X_scaled = self.scaler.transform(X)
            except ValueError as e:
                logger.error(f"Feature scaling error: {e}")
                return {'direction': 0, 'confidence': 0.5, 'model_votes': {}}

            # Get predictions from each model
            predictions = {}
            for name, model in self.models.items():
                try:
                    proba = model.predict_proba(X_scaled)[0]

                    # Ensure we have 2 classes (short/long)
                    if len(proba) < 2:
                        logger.error(f"Model {name} returned invalid probability shape")
                        continue

                    predictions[name] = {
                        'prob_long': float(proba[1]),
                        'prob_short': float(proba[0]),
                        'vote': 1 if proba[1] > 0.5 else -1,
                        'confidence': float(max(proba))
                    }
                except Exception as e:
                    logger.error(f"Error in model {name} prediction: {e}")
                    predictions[name] = {
                        'prob_long': 0.5,
                        'prob_short': 0.5,
                        'vote': 0,
                        'confidence': 0.5
                    }

            # Ensemble voting with weighted average
            if not predictions:
                logger.error("All model predictions failed")
                return {'direction': 0, 'confidence': 0.5, 'model_votes': {}}

            # Calculate weighted scores
            score_long = sum(
                p['prob_long'] * p['confidence'] * self.weights.get(name, 0)
                for name, p in predictions.items()
                if p['vote'] == 1
            )

            score_short = sum(
                p['prob_short'] * p['confidence'] * self.weights.get(name, 0)
                for name, p in predictions.items()
                if p['vote'] == -1
            )

            total_weight = sum(self.weights.values())

            # Determine final direction and confidence
            if score_long > score_short:
                direction = 1
                confidence = score_long / total_weight
            else:
                direction = -1
                confidence = score_short / total_weight

            self.prediction_count += 1

            # Rolling-window drift check against training distributions
            return_dict_drift = None
            if self.drift_monitor is not None and self.drift_monitor.enabled:
                try:
                    self.drift_monitor.push(X)
                    if self.prediction_count % 100 == 0:
                        drift = self.drift_monitor.check()
                        if drift["status"] == "violation":
                            logger.error(
                                f"FEATURE DRIFT VIOLATION: max PSI {drift['max_psi']:.3f} - "
                                f"model is trading on a regime it never trained on. "
                                f"Worst: {drift['psi'][:5]}"
                            )
                        elif drift["status"] == "warning":
                            logger.warning(
                                f"Feature drift warning: max PSI {drift['max_psi']:.3f}"
                            )
                        return_dict_drift = drift["status"]
                except Exception as e:
                    logger.warning(f"Drift check failed: {e}")

            result = {
                'direction': direction,
                'confidence': float(confidence),
                'model_votes': predictions,
                'score_long': float(score_long),
                'score_short': float(score_short)
            }
            if return_dict_drift:
                result['drift_status'] = return_dict_drift
            return result

        except Exception as e:
            logger.exception(f"Unexpected error in predict(): {e}")
            return {'direction': 0, 'confidence': 0.5, 'model_votes': {}}

    def get_stats(self) -> Dict:
        """Get inference pipeline statistics"""
        return {
            'prediction_count': self.prediction_count,
            'models_loaded': len(self.models),
            'model_names': list(self.models.keys()),
            'weights': self.weights
        }

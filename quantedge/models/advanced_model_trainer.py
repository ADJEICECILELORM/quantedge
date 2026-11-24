# models/advanced_model_trainer.py - Advanced Model Training with Validation
"""
Advanced model trainer with:
- Walk-forward validation
- Hyperparameter optimization
- Model performance comparison
- Automatic backup and versioning
- Ensemble optimization
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import xgboost as xgb
import joblib
import os

from models.registry import save_metadata
from utils.drift_monitor import summarize_feature_distribution
import json
from datetime import datetime
import shutil
from typing import Dict, Tuple


class MulticlassLabelXGB(xgb.XGBClassifier):
    """
    XGBClassifier that accepts arbitrary signed labels like {-1, 0, 1}.

    XGBoost requires contiguous integer labels starting at 0, so y is
    re-encoded ascending on fit and predictions are translated back on
    predict(). predict_proba() column order always matches ascending
    classes_, which keeps InferencePipeline's class-aware mapping valid.
    """

    def fit(self, X, y, **kwargs):
        self._orig_classes_ = np.unique(y)
        remap = {c: i for i, c in enumerate(self._orig_classes_)}
        y_enc = np.asarray([remap[v] for v in y])
        self._raw_label_fit = True
        try:
            return super().fit(X, y_enc, **kwargs)
        finally:
            self._raw_label_fit = False

    def predict(self, X, **kwargs):
        encoded = super().predict(X, **kwargs)
        return self._orig_classes_[np.asarray(encoded, dtype=int)]

    def predict_proba(self, X, **kwargs):
        return super().predict_proba(X, **kwargs)

    @property
    def classes_(self):
        if getattr(self, '_raw_label_fit', False):
            return np.arange(self.n_classes_)
        return self._orig_classes_


class AdvancedModelTrainer:
    """
    Advanced model trainer with validation and optimization.
    """

    def __init__(self, df: pd.DataFrame, model_dir: str = "models/saved"):
        self.df = df
        self.model_dir = model_dir
        self.backup_dir = "models/backup"
        self.scaler = StandardScaler()
        self.models = {}
        self.ensemble_weights = {}
        self.performance_history = []

        # Create directories
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs("models/performance", exist_ok=True)

    def prepare_data(self) -> Tuple:
        """
        Prepare training data with proper feature selection.
        """
        target_col = 'target'

        # Exclude non-feature columns
        exclude_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume',
                       'target', 'regime_label']

        feature_cols = [c for c in self.df.columns if c not in exclude_cols]
        self.feature_cols_ = feature_cols

        print(f"Training on {len(feature_cols)} features (Enhanced with V5 features).")

        X = self.df[feature_cols]
        y = self.df[target_col]

        # Time-series split (80/20)
        split_idx = int(len(self.df) * 0.8)

        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_test_scaled, y_train, y_test, feature_cols

    def walk_forward_validation(self, n_splits: int = 5, gap: int = 5) -> Dict:
        """
        Perform walk-forward validation (time-series cross-validation).

        Returns:
            Dictionary of validation scores per model
        """
        print(f"\n{'='*60}")
        print(f"WALK-FORWARD VALIDATION ({n_splits} splits)")
        print(f"{'='*60}")

        X, _, y, _, feature_cols = self.prepare_data()

        # Time series split. gap bars are purged between train and test so
        # labels computed over forward_bars cannot leak across the boundary.
        tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)

        validation_scores = {
            'rf': [],
            'xgb': [],
            'lr': []
        }

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            print(f"\nFold {fold}/{n_splits}:")

            X_train_fold, X_val_fold = X[train_idx], X[val_idx]
            y_train_fold, y_val_fold = y.iloc[train_idx], y.iloc[val_idx]

            # Train models
            rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
            rf.fit(X_train_fold, y_train_fold)
            rf_score = rf.score(X_val_fold, y_val_fold)
            validation_scores['rf'].append(rf_score)
            print(f"  RF: {rf_score:.4f}")

            xgb_clf = MulticlassLabelXGB(n_estimators=200, learning_rate=0.05, max_depth=6,
                                         use_label_encoder=False, eval_metric='logloss', n_jobs=-1)
            xgb_clf.fit(X_train_fold, y_train_fold)
            xgb_score = xgb_clf.score(X_val_fold, y_val_fold)
            validation_scores['xgb'].append(xgb_score)
            print(f"  XGB: {xgb_score:.4f}")

            lr = LogisticRegression(max_iter=1000, n_jobs=-1)
            lr.fit(X_train_fold, y_train_fold)
            lr_score = lr.score(X_val_fold, y_val_fold)
            validation_scores['lr'].append(lr_score)
            print(f"  LR: {lr_score:.4f}")

        # Average scores
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY:")
        print(f"{'='*60}")
        for model_name, scores in validation_scores.items():
            avg_score = np.mean(scores)
            std_score = np.std(scores)
            print(f"{model_name.upper()}: {avg_score:.4f} (+/- {std_score:.4f})")

        return validation_scores

    def optimize_hyperparameters(self, X_train, y_train, model_type: str = 'xgb', gap: int = 5):
        """
        Optimize hyperparameters using GridSearchCV.
        """
        print(f"\n{'='*60}")
        print(f"OPTIMIZING {model_type.upper()} HYPERPARAMETERS")
        print(f"{'='*60}")

        if model_type == 'rf':
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [8, 10, 12],
                'min_samples_split': [2, 5, 10]
            }
            model = RandomForestClassifier(random_state=42, n_jobs=-1)

        elif model_type == 'xgb':
            param_grid = {
                'n_estimators': [100, 200, 300],
                'learning_rate': [0.01, 0.05, 0.1],
                'max_depth': [4, 6, 8]
            }
            model = MulticlassLabelXGB(use_label_encoder=False, eval_metric='logloss', n_jobs=-1)

        elif model_type == 'lr':
            param_grid = {
                'C': [0.1, 1.0, 10.0],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear', 'saga']
            }
            model = LogisticRegression(max_iter=1000, n_jobs=-1)

        # Grid search with time series CV
        tscv = TimeSeriesSplit(n_splits=3, gap=gap)
        grid_search = GridSearchCV(model, param_grid, cv=tscv, scoring='accuracy',
                                   n_jobs=-1, verbose=1)

        print("Running grid search (this may take a few minutes)...")
        grid_search.fit(X_train, y_train)

        print(f"\nBest parameters: {grid_search.best_params_}")
        print(f"Best CV score: {grid_search.best_score_:.4f}")

        return grid_search.best_estimator_, grid_search.best_params_

    def train_models(self, optimize: bool = False):
        """
        Train all models with optional hyperparameter optimization.
        """
        X_train, X_test, y_train, y_test, feature_cols = self.prepare_data()

        print(f"\n{'='*60}")
        print("TRAINING MODELS")
        print(f"{'='*60}")

        # Random Forest
        if optimize:
            print("\n--- Optimizing Random Forest ---")
            rf, rf_params = self.optimize_hyperparameters(X_train, y_train, 'rf')
        else:
            print("\n--- Training Random Forest ---")
            rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
            rf.fit(X_train, y_train)

        self.models['rf'] = rf
        rf_metrics = self._evaluate_model(rf, X_test, y_test, "Random Forest")

        # XGBoost
        if optimize:
            print("\n--- Optimizing XGBoost ---")
            xgb_clf, xgb_params = self.optimize_hyperparameters(X_train, y_train, 'xgb')
        else:
            print("\n--- Training XGBoost ---")
            xgb_clf = MulticlassLabelXGB(n_estimators=200, learning_rate=0.05, max_depth=6,
                                         use_label_encoder=False, eval_metric='logloss', n_jobs=-1)
            xgb_clf.fit(X_train, y_train)

        self.models['xgb'] = xgb_clf
        xgb_metrics = self._evaluate_model(xgb_clf, X_test, y_test, "XGBoost")

        # Logistic Regression
        print("\n--- Training Logistic Regression ---")
        lr = LogisticRegression(max_iter=1000, n_jobs=-1, class_weight='balanced')
        lr.fit(X_train, y_train)
        self.models['lr'] = lr
        lr_metrics = self._evaluate_model(lr, X_test, y_test, "Logistic Regression")

        # Feature importance
        print(f"\n{'='*60}")
        print("TOP 15 IMPORTANT FEATURES (XGBoost)")
        print(f"{'='*60}")
        importance = xgb_clf.feature_importances_
        indices = np.argsort(importance)[::-1]
        for i in range(min(15, len(feature_cols))):
            print(f"{i+1:2d}. {feature_cols[indices[i]]:30s} {importance[indices[i]]:.4f}")

        # Store performance
        self.performance_history.append({
            'timestamp': datetime.now().isoformat(),
            'rf': rf_metrics,
            'xgb': xgb_metrics,
            'lr': lr_metrics
        })

        return {
            'rf': rf_metrics,
            'xgb': xgb_metrics,
            'lr': lr_metrics
        }

    def _evaluate_model(self, model, X_test, y_test, model_name: str) -> Dict:
        """
        Comprehensive model evaluation.
        """
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)

        if y_proba.ndim == 2 and y_proba.shape[1] == 2:
            y_score = y_proba[:, 1]
            roc_auc = roc_auc_score(y_test, y_score, average='weighted')
        elif y_proba.ndim == 2 and y_proba.shape[1] > 2 and len(np.unique(y_test)) > 2:
            roc_auc = roc_auc_score(
                y_test, y_proba, multi_class='ovr', average='weighted', labels=model.classes_
            )
        else:
            print(f"  {model_name}: degenerate class set in test fold - ROC AUC set to 0.5")
            roc_auc = 0.5

        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
            'f1': f1_score(y_test, y_pred, average='weighted', zero_division=0),
            'roc_auc': roc_auc
        }

        print(f"\n{model_name} Performance:")
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
        print(f"  F1 Score:  {metrics['f1']:.4f}")
        print(f"  ROC AUC:   {metrics['roc_auc']:.4f}")

        return metrics

    def optimize_ensemble_weights(self, X_test, y_test):
        """
        Find optimal ensemble weights using grid search.
        """
        print(f"\n{'='*60}")
        print("OPTIMIZING ENSEMBLE WEIGHTS")
        print(f"{'='*60}")

        best_accuracy = 0
        best_weights = None

        # Try different weight combinations
        weight_options = [0.2, 0.3, 0.4, 0.5]

        for rf_weight in weight_options:
            for xgb_weight in weight_options:
                lr_weight = 1.0 - rf_weight - xgb_weight
                if lr_weight < 0 or lr_weight > 1:
                    continue

                # Get predictions
                rf_proba = self.models['rf'].predict_proba(X_test)
                xgb_proba = self.models['xgb'].predict_proba(X_test)
                lr_proba = self.models['lr'].predict_proba(X_test)

                # Weighted ensemble
                ensemble_proba = (rf_weight * rf_proba +
                                 xgb_weight * xgb_proba +
                                 lr_weight * lr_proba)
                ensemble_pred = np.argmax(ensemble_proba, axis=1)

                # Calculate accuracy
                accuracy = accuracy_score(y_test, ensemble_pred)

                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_weights = {
                        'rf': rf_weight,
                        'xgb': xgb_weight,
                        'lr': lr_weight
                    }

        print("\nBest Ensemble Weights:")
        print(f"  RF:  {best_weights['rf']:.2f}")
        print(f"  XGB: {best_weights['xgb']:.2f}")
        print(f"  LR:  {best_weights['lr']:.2f}")
        print(f"  Accuracy: {best_accuracy:.4f}")

        self.ensemble_weights = best_weights
        return best_weights

    def backup_existing_models(self):
        """
        Backup existing models before saving new ones.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_folder = os.path.join(self.backup_dir, f"backup_{timestamp}")

        if os.path.exists(self.model_dir):
            print(f"\n💾 Backing up existing models to: {backup_folder}")
            shutil.copytree(self.model_dir, backup_folder, dirs_exist_ok=True)
            print("✅ Backup complete")

    def save_models(self, with_backup: bool = True):
        """
        Save models with versioning.
        """
        try:
            from utils.retrain_trigger import clear_flag
            if clear_flag(self.model_dir):
                print("Cleared retrain-required flag (fresh models deployed)")
        except Exception:
            pass

        if with_backup:
            self.backup_existing_models()

        print(f"\n💾 Saving models to: {self.model_dir}")

        # Save models
        joblib.dump(self.scaler, f"{self.model_dir}/scaler.pkl")
        joblib.dump(self.models['rf'], f"{self.model_dir}/rf_model.pkl")
        joblib.dump(self.models['xgb'], f"{self.model_dir}/xgb_model.pkl")
        joblib.dump(self.models['lr'], f"{self.model_dir}/lr_model.pkl")

        # Save ensemble weights
        if self.ensemble_weights:
            with open(f"{self.model_dir}/ensemble_weights.json", 'w') as f:
                json.dump(self.ensemble_weights, f, indent=2)

        # Save metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'training_samples': len(self.df),
            'num_features': len(self.df.columns) - 6,  # Exclude metadata columns
            'performance': self.performance_history[-1] if self.performance_history else {}
        }

        with open(f"{self.model_dir}/model_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        time_col = 'time' if 'time' in self.df.columns else None
        feature_stats = summarize_feature_distribution(self.df, getattr(self, 'feature_cols_', []))
        save_metadata(
            model_dir=self.model_dir,
            feature_cols=getattr(self, 'feature_cols_', []),
            feature_stats=feature_stats,
            data_start=self.df[time_col].iloc[0] if time_col else None,
            data_end=self.df[time_col].iloc[-1] if time_col else None,
            metrics=(metadata.get('performance') or {}),
            extra={'trainer': 'AdvancedModelTrainer', 'training_samples': len(self.df)},
        )

        # Save performance history
        with open("models/performance/training_history.json", 'w') as f:
            json.dump(self.performance_history, f, indent=2)

        print("✅ All models, weights, and metadata saved")

    def compare_with_existing_models(self, X_test, y_test) -> bool:
        """
        Compare new models with existing ones.

        Returns:
            True if new models are better, False otherwise
        """
        print(f"\n{'='*60}")
        print("COMPARING WITH EXISTING MODELS")
        print(f"{'='*60}")

        # Check if existing models exist
        existing_model_path = f"{self.model_dir}/xgb_model.pkl"
        if not os.path.exists(existing_model_path):
            print("No existing models found. New models will be saved.")
            return True

        try:
            # Load existing models
            existing_scaler = joblib.load(f"{self.model_dir}/scaler.pkl")
            existing_xgb = joblib.load(f"{self.model_dir}/xgb_model.pkl")

            # Test on same data
            X_test_scaled = existing_scaler.transform(X_test)
            existing_accuracy = existing_xgb.score(X_test_scaled, y_test)
            new_accuracy = self.models['xgb'].score(self.scaler.transform(X_test), y_test)

            print(f"\nExisting XGB Accuracy: {existing_accuracy:.4f}")
            print(f"New XGB Accuracy:      {new_accuracy:.4f}")
            print(f"Improvement:           {(new_accuracy - existing_accuracy)*100:+.2f}%")

            if new_accuracy > existing_accuracy:
                print("\n✅ New models are BETTER - Will deploy")
                return True
            else:
                print("\n⚠️ New models are WORSE - Will NOT deploy")
                return False

        except Exception as e:
            print(f"⚠️ Error comparing models: {e}")
            return True  # Deploy anyway if comparison fails

    def print_training_summary(self):
        """Print comprehensive training summary"""
        print(f"\n{'='*60}")
        print("TRAINING COMPLETE - SUMMARY")
        print(f"{'='*60}")
        print(f"Training Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Training Samples: {len(self.df)}")
        print(f"Number of Features: {len(self.df.columns) - 6}")
        print("\nModels Trained:")
        print("  ✅ Random Forest")
        print("  ✅ XGBoost")
        print("  ✅ Logistic Regression")
        print("\nEnsemble Weights:")
        if self.ensemble_weights:
            print(f"  RF:  {self.ensemble_weights['rf']:.2f}")
            print(f"  XGB: {self.ensemble_weights['xgb']:.2f}")
            print(f"  LR:  {self.ensemble_weights['lr']:.2f}")
        print(f"{'='*60}\n")

# models/model_trainer.py
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import xgboost as xgb
import joblib
import os

from models.registry import save_metadata

class ModelTrainer:
    def __init__(self, df):
        self.df = df
        self.scaler = StandardScaler()
        self.models = {}
        if not os.path.exists("models/saved"):
            os.makedirs("models/saved")

    def prepare_data(self):
        target_col = 'target'
        
        # We added 'regime_label' here because it contains text ('ranging'/'trending')
        # The scaler cannot process text, so we must exclude it.
        exclude_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'target', 'regime_label']
        
        feature_cols = [c for c in self.df.columns if c not in exclude_cols]
        
        print(f"Training on {len(feature_cols)} features.")
        
        X = self.df[feature_cols]
        y = self.df[target_col]

        split_idx = int(len(self.df) * 0.8)
        
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test, feature_cols

    def train_models(self):
        X_train, X_test, y_train, y_test, feature_cols = self.prepare_data()
        metrics = {}
        
        print("--- Training Random Forest ---")
        rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
        rf.fit(X_train, y_train)
        self.models['rf'] = rf
        metrics['rf_accuracy'] = float(rf.score(X_test, y_test))
        print(f"RF Accuracy: {metrics['rf_accuracy']:.4f}")

        print("--- Training XGBoost ---")
        xgb_clf = xgb.XGBClassifier(n_estimators=200, learning_rate=0.05, max_depth=6, use_label_encoder=False, eval_metric='logloss')
        xgb_clf.fit(X_train, y_train)
        self.models['xgb'] = xgb_clf
        metrics['xgb_accuracy'] = float(xgb_clf.score(X_test, y_test))
        print(f"XGB Accuracy: {metrics['xgb_accuracy']:.4f}")

        print("--- Training Logistic Regression ---")
        lr = LogisticRegression(max_iter=1000)
        lr.fit(X_train, y_train)
        self.models['lr'] = lr
        metrics['lr_accuracy'] = float(lr.score(X_test, y_test))
        print(f"LR Accuracy: {metrics['lr_accuracy']:.4f}")
        
        print("\n--- Top 10 Important Features (XGB) ---")
        importance = xgb_clf.feature_importances_
        indices = np.argsort(importance)[::-1]
        for i in range(10):
            print(f"{i+1}. {feature_cols[indices[i]]} ({importance[indices[i]]:.4f})")

        self.metrics = metrics
        self.feature_cols = feature_cols

    def save_models(self):
        joblib.dump(self.scaler, "models/saved/scaler.pkl")
        joblib.dump(self.models['rf'], "models/saved/rf_model.pkl")
        joblib.dump(self.models['xgb'], "models/saved/xgb_model.pkl")
        joblib.dump(self.models['lr'], "models/saved/lr_model.pkl")
        print("\nAll models and scaler saved.")

    def save_metadata(self, model_dir="models/saved"):
        time_col = 'time' if 'time' in self.df.columns else None
        save_metadata(
            model_dir=model_dir,
            feature_cols=getattr(self, 'feature_cols', []),
            data_start=self.df[time_col].iloc[0] if time_col else None,
            data_end=self.df[time_col].iloc[-1] if time_col else None,
            hyperparams={
                'rf': {'n_estimators': 200, 'max_depth': 10},
                'xgb': {'n_estimators': 200, 'learning_rate': 0.05, 'max_depth': 6},
                'lr': {'max_iter': 1000},
            },
            metrics=getattr(self, 'metrics', {}),
            extra={'train_test_split': 'chronological 80/20'},
        )
        print("Metadata saved to models/saved/metadata.json")
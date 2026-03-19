# make_pipeline.py
code = r'''
# pipeline/inference_pipeline.py
import joblib
import pandas as pd
import numpy as np

class InferencePipeline:
    def __init__(self):
        print("Loading Models...")
        self.scaler = joblib.load("models/saved/scaler.pkl")
        self.models = {
            'rf': joblib.load("models/saved/rf_model.pkl"),
            'xgb': joblib.load("models/saved/xgb_model.pkl"),
            'lr': joblib.load("models/saved/lr_model.pkl")
        }
        print("Models Loaded Successfully.")
        self.weights = {
            'rf': 0.40, 
            'xgb': 0.47, 
            'lr': 0.13
        }

    def predict(self, latest_features_df):
        exclude_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'target', 'regime_label']
        feature_cols = [c for c in latest_features_df.columns if c not in exclude_cols]
        X = latest_features_df[feature_cols]
        
        try:
            X_scaled = self.scaler.transform(X)
        except Exception as e:
            print(f"Error scaling data: {e}")
            return {'signal': 0, 'error': 'Scaling Failed'}

        predictions = {}
        for name, model in self.models.items():
            try:
                proba = model.predict_proba(X_scaled)[0]
                pred_class = np.argmax(proba)
                confidence = max(proba)
                predictions[name] = {
                    'prob_long': proba[1],
                    'vote': 1 if proba[1] > 0.5 else -1,
                    'confidence': confidence
                }
            except Exception as e:
                print(f"Error in {name}: {e}")
                predictions[name] = {'vote': 0, 'confidence': 0.5} 
        
        score_long = 0
        score_short = 0
        
        for name, p in predictions.items():
            w = self.weights[name]
            if p['vote'] == 1:
                score_long += p['prob_long'] * p['confidence'] * w
            else:
                score_short += (1 - p['prob_long']) * p['confidence'] * w
        
        total_weight = sum(self.weights.values())
        if score_long > score_short:
            final_direction = 1
            final_confidence = score_long / total_weight
        else:
            final_direction = -1
            final_confidence = score_short / total_weight

        if final_confidence < 0.60:
            final_direction = 0 

        return {
            'direction': final_direction, 
            'confidence': final_confidence,
            'model_breakdown': predictions
        }
'''

# Create __init__.py
with open("pipeline/__init__.py", "w") as f:
    f.write("")

# Create inference_pipeline.py
with open("pipeline/inference_pipeline.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Files created successfully in pipeline/")
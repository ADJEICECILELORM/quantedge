# tests/test_models/test_model_trainer.py
import numpy as np

from models.advanced_model_trainer import AdvancedModelTrainer


class TestEvaluateModel:
    def test_two_column_proba_is_flattened_for_roc_auc(self):
        from sklearn.linear_model import LogisticRegression

        rng = np.random.default_rng(0)
        X = rng.normal(size=(200, 4))
        y = (X[:, 0] + X[:, 1] + rng.normal(scale=0.5, size=200)) > 0

        model = LogisticRegression()
        model.fit(X[:150], y[:150])
        X_test, y_test = X[150:], y[150:]

        trainer = object.__new__(AdvancedModelTrainer)
        metrics = trainer._evaluate_model(model, X_test, y_test, "test-model")

        assert 0.0 <= metrics["roc_auc"] <= 1.0
        assert 0.0 <= metrics["accuracy"] <= 1.0

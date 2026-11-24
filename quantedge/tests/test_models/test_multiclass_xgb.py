import numpy as np

from models.advanced_model_trainer import MulticlassLabelXGB


class TestMulticlassLabelXGB:
    def _model(self):
        return MulticlassLabelXGB(
            n_estimators=10,
            max_depth=2,
            eval_metric="logloss",
            use_label_encoder=False,
        )

    def test_accepts_signed_labels(self):
        X = np.random.RandomState(0).rand(60, 3)
        y = np.repeat([-1, 0, 1], 20)
        model = self._model()
        model.fit(X, y)
        assert list(model.classes_) == [-1, 0, 1]

    def test_predict_returns_original_label_space(self):
        X = np.random.RandomState(1).rand(60, 3)
        y = np.repeat([-1, 0, 1], 20)
        model = self._model()
        model.fit(X, y)
        preds = model.predict(X)
        assert set(np.unique(preds)).issubset({-1, 0, 1})

    def test_predict_proba_columns_match_classes(self):
        X = np.random.RandomState(2).rand(60, 3)
        y = np.repeat([-1, 0, 1], 20)
        model = self._model()
        model.fit(X, y)
        proba = model.predict_proba(X[:5])
        assert proba.shape == (5, 3)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, rtol=1e-5)
        assert np.nanargmax(proba[0]) == int(np.where(model.classes_ == model.predict(X[:1])[0])[0][0])

    def test_score_works_on_original_labels(self):
        X = np.random.RandomState(3).rand(60, 3)
        y = np.repeat([-1, 0, 1], 20)
        model = self._model()
        model.fit(X, y)
        score = model.score(X, y)
        assert 0.0 <= score <= 1.0

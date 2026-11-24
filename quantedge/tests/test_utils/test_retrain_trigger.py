from utils.retrain_trigger import check_flag, clear_flag, flag_path, raise_flag


class TestRetrainTrigger:
    def test_roundtrip(self, tmp_path):
        model_dir = str(tmp_path / "models" / "saved")
        assert check_flag(model_dir) is None

        path = raise_flag(model_dir, detail={"max_psi_adjusted": 0.4})
        assert path == flag_path(model_dir)

        flag = check_flag(model_dir)
        assert flag["reason"] == "feature_drift"
        assert flag["detail"]["max_psi_adjusted"] == 0.4

        assert clear_flag(model_dir) is True
        assert check_flag(model_dir) is None

    def test_clear_missing_flag_returns_false(self, tmp_path):
        assert clear_flag(str(tmp_path / "nothing")) is False

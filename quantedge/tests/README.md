# QuantEdge Testing Guide

## Running Tests

### Install Test Dependencies
```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Run Specific Test Files
```bash
# Test multi-timeframe analyzer
pytest tests/test_utils/test_multi_timeframe.py

# Test Kelly Criterion
pytest tests/test_utils/test_kelly_criterion.py

# Test cache manager
pytest tests/test_utils/test_cache_manager.py
```

### Run Tests by Category
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Verbose Output
```bash
pytest -v
```

### Show Print Statements
```bash
pytest -s
```

## Test Structure

```
tests/
├── conftest.py              # pytest configuration and fixtures
├── test_utils/              # Tests for utils modules
│   ├── test_multi_timeframe.py
│   ├── test_kelly_criterion.py
│   ├── test_cache_manager.py
│   └── test_performance_profiler.py
├── test_features/           # Tests for feature engineering
│   └── test_feature_engineer.py
├── test_pipeline/           # Tests for ML pipeline
│   └── test_inference_pipeline.py
├── test_integration/        # Integration tests
│   └── test_bot_workflow.py
└── fixtures/                # Test fixtures and mocks
    ├── mock_mt5.py
    └── sample_data.py
```

## Writing Tests

### Example Test
```python
import pytest
from utils.my_module import MyClass

class TestMyClass:
    def test_init(self):
        """Test initialization"""
        obj = MyClass()
        assert obj is not None

    def test_method(self, sample_fixture):
        """Test a method with fixture"""
        obj = MyClass()
        result = obj.method(sample_fixture)
        assert result == expected_value
```

### Using Fixtures
```python
def test_with_mock_mt5(mock_mt5_connector):
    """Use mock MT5 connector"""
    data = mock_mt5_connector.get_latest_bars('EURUSD', timeframe, 100)
    assert data is not None
```

## Continuous Testing

### Watch Mode (with pytest-watch)
```bash
pip install pytest-watch
ptw
```

### Pre-commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/sh
pytest
```

## Coverage Goals

- **Target**: 80%+ code coverage
- **Critical modules**: 90%+ coverage
- **View coverage report**: Open `htmlcov/index.html` after running coverage

## Troubleshooting

### Import Errors
Make sure you're in the quantedge directory:
```bash
cd C:\Users\ADJEI CECIL ELORM\OneDrive\quantedge
pytest
```

### Missing Dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock
```

### Slow Tests
Skip slow tests during development:
```bash
pytest -m "not slow"
```

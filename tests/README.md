# Testing Documentation

## Overview
The testing suite for ASTRA Core is comprehensive and covers multiple aspects of the system:
- Unit tests
- Integration tests
- Schema validation
- Performance benchmarks
- Safety checks

## Running Tests

### Unit Tests
```bash
pytest tests/unit/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Performance Tests
```bash
pytest tests/performance/
```

## Test Structure

```
tests/
├── unit/                     # Unit tests
│   ├── test_surgeon.py      # Model surgery tests
│   ├── test_rope.py         # RoPE tuning tests
│   └── test_schema.py       # Schema validation tests
├── integration/             # Integration tests
│   ├── test_pipeline.py    # Full pipeline tests
│   └── test_api.py         # API integration tests
└── performance/            # Performance tests
    ├── test_merge.py      # LoRA merge benchmarks
    └── test_validate.py   # Validation benchmarks
```

## Writing Tests

### Test Case Template
```python
def test_feature():
    # Arrange
    surgeon = ModelSurgeon()
    
    # Act
    result = surgeon.some_operation()
    
    # Assert
    assert result.success
    assert result.metrics.within_bounds()
```

### Fixtures
Common test fixtures are available in `conftest.py`:
- `model_fixture`
- `adapter_fixture`
- `schema_fixture`

### Mocking
Use the provided mock objects in `tests/mocks/`:
- `MockModel`
- `MockAdapter`
- `MockValidator`

## Coverage

Generate coverage report:
```bash
pytest --cov=evolution tests/
```

View HTML report:
```bash
pytest --cov=evolution --cov-report=html tests/
```

## Gates

Test gates enforce quality standards:
- Coverage >= 80%
- Performance within bounds
- No regressions
- Clean lint
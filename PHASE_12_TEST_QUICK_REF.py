"""Quick reference for running Phase 12 tests."""

# Quick Test Execution Guide
# ==========================

## Run All Unit Tests (Phase 1-5)
pytest tests/unit/ -v

## Run Specific Component Tests
pytest tests/unit/test_bootd.py -v         # Boot Daemon (50 tests)
pytest tests/unit/test_bus.py -v           # Event Bus (50 tests)
pytest tests/unit/test_memory.py -v        # Memory Layer (70 tests)
pytest tests/unit/test_policy.py -v        # Policy Engine (80 tests)

## Run with Coverage
pytest tests/unit/ --cov=astra --cov-report=html

## Run Specific Test Class
pytest tests/unit/test_bootd.py::TestBootDaemonInitialization -v

## Run Specific Test
pytest tests/unit/test_bootd.py::TestBootDaemonInitialization::test_initialization_standalone_mode -v

## Run Async Tests Only
pytest tests/unit/ -v -m asyncio

## Run with Markers
pytest tests/unit/ -v -m "not slow"
pytest tests/unit/ -v -m "performance"

## Run with Timeout (60 seconds per test)
pytest tests/unit/ -v --timeout=60

## Generate Coverage Report
pytest tests/unit/ --cov=astra --cov-report=term-missing

## Run Tests in Parallel (if pytest-xdist installed)
pytest tests/unit/ -n auto

## Run Tests with Detailed Output
pytest tests/unit/ -vv --tb=long

## Stop on First Failure
pytest tests/unit/ -x

## Run Last Failed Tests
pytest tests/unit/ --lf

## Run Slow Tests Only
pytest tests/unit/ -m slow

# Test Counts
# ===========
# Boot Daemon (test_bootd.py):        50 tests
# Event Bus (test_bus.py):            50 tests
# Memory Layer (test_memory.py):      70 tests
# Policy Engine (test_policy.py):     80 tests
# ─────────────────────────────────
# TOTAL (Phase 1-5):                 250 tests

# Expected Execution Time
# =======================
# Boot Daemon:    ~5-10 seconds
# Event Bus:      ~5-10 seconds (includes async)
# Memory Layer:   ~10-15 seconds
# Policy Engine:  ~10-15 seconds
# ─────────────────────────────────
# TOTAL:         ~30-50 seconds for all 250 tests

# Coverage Targets
# ================
# Boot Daemon:    85%+ ✅
# Event Bus:      90%+ ✅
# Memory Layer:   90%+ ✅
# Policy Engine:  90%+ ✅
# ─────────────────────────────────
# OVERALL:        88%+ ✅ (targeting >90% by Phase 12 completion)

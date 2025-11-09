"""
Tests for ASTRA OS Phase 9: Self-Modification Engine

Tests meta-programming capabilities including:
- Code analysis and AST introspection
- Pattern detection
- Dynamic code generation
- Self-testing and validation
- Safe execution with rollback
- Evolution tracking
"""

import pytest
from chat_os.cognitive.self_modification import (
    SelfModificationEngine,
    CodePattern,
    CodeModification,
    ModificationType,
    ValidationStatus,
    EvolutionRecord,
    get_self_modification_engine
)


def test_engine_initialization():
    """Test self-modification engine initialization"""
    engine = SelfModificationEngine(safe_mode=True)
    
    assert engine.safe_mode is True
    assert len(engine.modifications) == 0
    assert len(engine.generated_functions) == 0
    assert engine.current_generation == 0


def test_code_analysis_valid():
    """Test analysis of valid Python code"""
    engine = SelfModificationEngine()
    
    code = """
def test_func(x, y):
    return x + y

class TestClass:
    def method(self):
        pass
"""
    
    analysis = engine.analyze_code(code)
    
    assert analysis["valid"] is True
    assert len(analysis["functions"]) == 2  # test_func and method
    assert len(analysis["classes"]) == 1
    assert analysis["functions"][0]["name"] == "test_func"
    assert analysis["classes"][0]["name"] == "TestClass"


def test_code_analysis_invalid():
    """Test analysis of invalid Python code"""
    engine = SelfModificationEngine()
    
    code = "def broken syntax("
    
    analysis = engine.analyze_code(code)
    
    assert analysis["valid"] is False
    assert "error" in analysis


def test_complexity_calculation():
    """Test cyclomatic complexity calculation"""
    engine = SelfModificationEngine()
    
    # Simple function: complexity 1
    simple_code = """
def simple(x):
    return x * 2
"""
    
    # Complex function: complexity > 1
    complex_code = """
def complex(x):
    if x > 0:
        if x < 10:
            return x
        else:
            return 10
    else:
        return 0
"""
    
    simple_analysis = engine.analyze_code(simple_code)
    complex_analysis = engine.analyze_code(complex_code)
    
    simple_complexity = simple_analysis["functions"][0]["complexity"]
    complex_complexity = complex_analysis["functions"][0]["complexity"]
    
    assert simple_complexity == 1
    assert complex_complexity > simple_complexity


def test_pattern_detection():
    """Test detection of code patterns"""
    engine = SelfModificationEngine()
    
    code = """
def func1(x):
    return x + 1

def func2(y):
    return y * 2
"""
    
    analysis = engine.analyze_code(code)
    
    assert len(analysis["patterns"]) > 0
    assert len(engine.detected_patterns) > 0


def test_generate_function():
    """Test dynamic function generation"""
    engine = SelfModificationEngine()
    
    func = engine.generate_function(
        function_name="test_add",
        parameters=["a", "b"],
        body_template="return a + b",
        docstring="Test addition function"
    )
    
    # Function should work
    assert func(2, 3) == 5
    assert func(10, -5) == 5
    
    # Should be stored
    assert "test_add" in engine.generated_functions
    assert len(engine.modifications) == 1
    assert engine.successful_modifications == 1


def test_generate_function_with_logic():
    """Test generating function with conditional logic"""
    engine = SelfModificationEngine()
    
    func = engine.generate_function(
        function_name="test_max",
        parameters=["a", "b"],
        body_template="return a if a > b else b"
    )
    
    assert func(5, 3) == 5
    assert func(2, 8) == 8


def test_propose_modification():
    """Test proposing a code modification"""
    engine = SelfModificationEngine()
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test_module",
        description="Optimize function",
        modified_code="# optimized code",
        original_code="# original code",
        reason="Improve performance",
        confidence=0.9
    )
    
    assert mod_id in engine.modifications
    assert mod_id in engine.pending_modifications
    
    mod = engine.modifications[mod_id]
    assert mod.modification_type == ModificationType.OPTIMIZATION
    assert mod.confidence_score == 0.9
    assert mod.applied is False


def test_modification_risk_assessment():
    """Test risk assessment for different modification types"""
    engine = SelfModificationEngine()
    
    # Low risk: function creation
    low_risk_id = engine.propose_modification(
        modification_type=ModificationType.FUNCTION_CREATION,
        target_module="test",
        description="Create function",
        modified_code=""
    )
    
    # High risk: class modification
    high_risk_id = engine.propose_modification(
        modification_type=ModificationType.CLASS_MODIFICATION,
        target_module="test",
        description="Modify class",
        modified_code=""
    )
    
    low_risk_mod = engine.modifications[low_risk_id]
    high_risk_mod = engine.modifications[high_risk_id]
    
    assert low_risk_mod.risk_assessment == "low"
    assert high_risk_mod.risk_assessment == "high"


def test_validate_modification_success():
    """Test successful modification validation"""
    engine = SelfModificationEngine()
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.FUNCTION_CREATION,
        target_module="test",
        description="Valid code",
        modified_code="def test(): return True"
    )
    
    valid = engine.validate_modification(mod_id)
    
    assert valid is True
    mod = engine.modifications[mod_id]
    assert mod.validation_status == ValidationStatus.PASSED
    assert "syntax_check" in mod.test_results


def test_validate_modification_failure():
    """Test failed modification validation"""
    engine = SelfModificationEngine()
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.FUNCTION_CREATION,
        target_module="test",
        description="Invalid code",
        modified_code="def broken syntax("
    )
    
    valid = engine.validate_modification(mod_id)
    
    assert valid is False
    mod = engine.modifications[mod_id]
    assert mod.validation_status == ValidationStatus.FAILED
    assert mod_id in engine.failed_modifications


def test_validate_with_custom_test():
    """Test validation with custom test function"""
    engine = SelfModificationEngine()
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.FUNCTION_CREATION,
        target_module="test",
        description="Test code",
        modified_code="def test(): return 42"
    )
    
    # Custom test that checks for return value
    def custom_test(code: str) -> bool:
        return "return" in code
    
    valid = engine.validate_modification(mod_id, test_function=custom_test)
    
    assert valid is True
    mod = engine.modifications[mod_id]
    assert mod.test_results["custom_test"] == "passed"


def test_apply_modification_safe_mode():
    """Test applying modification in safe mode"""
    engine = SelfModificationEngine(safe_mode=True)
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test",
        description="Test",
        modified_code="def test(): pass"
    )
    
    # Should fail without validation in safe mode
    applied = engine.apply_modification(mod_id)
    assert applied is False
    
    # Validate first
    engine.validate_modification(mod_id)
    
    # Now should succeed
    applied = engine.apply_modification(mod_id)
    assert applied is True
    assert mod_id in engine.applied_modifications


def test_apply_modification_force():
    """Test forcing modification application without validation"""
    engine = SelfModificationEngine(safe_mode=True)
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test",
        description="Test",
        modified_code="def test(): pass"
    )
    
    # Force apply without validation
    applied = engine.apply_modification(mod_id, force=True)
    
    assert applied is True
    assert mod_id in engine.applied_modifications


def test_rollback_modification():
    """Test rolling back an applied modification"""
    engine = SelfModificationEngine()
    
    # Generate a function
    func = engine.generate_function(
        function_name="test_rollback",
        parameters=["x"],
        body_template="return x * 2"
    )
    
    # Get modification ID
    mod_id = list(engine.modifications.keys())[0]
    
    # Rollback
    rolled_back = engine.rollback_modification(mod_id)
    
    assert rolled_back is True
    mod = engine.modifications[mod_id]
    assert mod.rolled_back is True
    assert mod.validation_status == ValidationStatus.ROLLED_BACK
    assert engine.rolled_back_modifications == 1


def test_rollback_unapplied_modification():
    """Test rolling back a modification that wasn't applied"""
    engine = SelfModificationEngine()
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test",
        description="Test",
        modified_code="def test(): pass"
    )
    
    # Try to rollback before applying
    rolled_back = engine.rollback_modification(mod_id)
    
    assert rolled_back is False


def test_optimize_function_memoization():
    """Test function optimization with memoization"""
    engine = SelfModificationEngine()
    
    # Original function
    def slow_func(n):
        if n <= 1:
            return n
        return slow_func(n-1) + slow_func(n-2)
    
    # Optimize
    optimized = engine.optimize_function(slow_func, optimization_type="speed")
    
    # Should return optimized version
    assert optimized is not None
    
    # Test it works
    result = optimized(5)
    assert result == slow_func(5)
    
    # Should have modification record
    assert len(engine.modifications) > 0
    assert engine.successful_modifications > 0


def test_evolve_generation():
    """Test generation evolution tracking"""
    engine = SelfModificationEngine()
    
    # Generate some modifications
    engine.generate_function("func1", ["x"], "return x")
    engine.generate_function("func2", ["y"], "return y * 2")
    
    # Evolve generation
    record = engine.evolve_generation()
    
    assert record.generation == 1
    assert record.total_functions == 2
    assert len(record.modifications) == 2
    assert "successful_modifications" in record.improvement_metrics


def test_multiple_generations():
    """Test tracking multiple generations"""
    engine = SelfModificationEngine()
    
    # Generation 1
    engine.generate_function("gen1_func", ["x"], "return x")
    record1 = engine.evolve_generation()
    
    # Generation 2
    engine.generate_function("gen2_func", ["x"], "return x * 2")
    record2 = engine.evolve_generation()
    
    assert record2.generation == 2
    assert record2.generation > record1.generation
    assert len(engine.evolution_history) == 2


def test_get_modification_stats():
    """Test getting modification statistics"""
    engine = SelfModificationEngine()
    
    # Create some modifications
    engine.generate_function("func1", ["x"], "return x")
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test",
        description="Test",
        modified_code="invalid syntax("
    )
    engine.validate_modification(mod_id)  # Will fail
    
    stats = engine.get_modification_stats()
    
    assert stats["total_modifications"] == 2
    assert stats["applied"] == 1
    assert stats["failed"] == 1
    assert stats["generated_functions"] == 1
    assert 0 <= stats["success_rate"] <= 1


def test_get_evolution_history():
    """Test retrieving evolution history"""
    engine = SelfModificationEngine()
    
    engine.generate_function("func1", ["x"], "return x")
    engine.evolve_generation()
    
    engine.generate_function("func2", ["x"], "return x * 2")
    engine.evolve_generation()
    
    history = engine.get_evolution_history()
    
    assert len(history) == 2
    assert history[0].generation == 1
    assert history[1].generation == 2


def test_get_modification():
    """Test retrieving specific modification"""
    engine = SelfModificationEngine()
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test",
        description="Test modification",
        modified_code="code"
    )
    
    mod = engine.get_modification(mod_id)
    
    assert mod is not None
    assert mod.modification_id == mod_id
    assert mod.description == "Test modification"


def test_get_nonexistent_modification():
    """Test retrieving non-existent modification"""
    engine = SelfModificationEngine()
    
    mod = engine.get_modification("nonexistent")
    
    assert mod is None


def test_get_generated_function():
    """Test retrieving generated function"""
    engine = SelfModificationEngine()
    
    engine.generate_function("my_func", ["x"], "return x * 2")
    
    func = engine.get_generated_function("my_func")
    
    assert func is not None
    assert func(5) == 10


def test_get_nonexistent_generated_function():
    """Test retrieving non-existent generated function"""
    engine = SelfModificationEngine()
    
    func = engine.get_generated_function("nonexistent")
    
    assert func is None


def test_global_singleton():
    """Test global singleton pattern"""
    engine1 = get_self_modification_engine()
    engine2 = get_self_modification_engine()
    
    assert engine1 is engine2


def test_modification_type_enum():
    """Test ModificationType enum values"""
    assert ModificationType.FUNCTION_CREATION.value == "function_creation"
    assert ModificationType.OPTIMIZATION.value == "optimization"
    assert ModificationType.BUG_FIX.value == "bug_fix"


def test_validation_status_enum():
    """Test ValidationStatus enum values"""
    assert ValidationStatus.PENDING.value == "pending"
    assert ValidationStatus.PASSED.value == "passed"
    assert ValidationStatus.FAILED.value == "failed"
    assert ValidationStatus.ROLLED_BACK.value == "rolled_back"


def test_code_pattern_hash():
    """Test CodePattern hashing"""
    pattern1 = CodePattern(
        pattern_id="p1",
        pattern_type="function",
        description="Test",
        ast_structure={}
    )
    
    pattern2 = CodePattern(
        pattern_id="p1",
        pattern_type="function",
        description="Different",
        ast_structure={}
    )
    
    # Same ID = same hash
    assert hash(pattern1) == hash(pattern2)


def test_generate_function_with_docstring():
    """Test generating function with docstring"""
    engine = SelfModificationEngine()
    
    func = engine.generate_function(
        function_name="documented_func",
        parameters=["x"],
        body_template="return x * 2",
        docstring="This function doubles the input"
    )
    
    assert func.__doc__ == "This function doubles the input"
    assert func(5) == 10


def test_analyze_imports():
    """Test analyzing imports in code"""
    engine = SelfModificationEngine()
    
    code = """
import os
import sys
from pathlib import Path
"""
    
    analysis = engine.analyze_code(code)
    
    assert "os" in analysis["imports"]
    assert "sys" in analysis["imports"]
    assert "pathlib" in analysis["imports"]


def test_analyze_classes_with_methods():
    """Test analyzing classes with methods"""
    engine = SelfModificationEngine()
    
    code = """
class MyClass:
    def method1(self):
        pass
    
    def method2(self, x):
        return x
"""
    
    analysis = engine.analyze_code(code)
    
    assert len(analysis["classes"]) == 1
    assert analysis["classes"][0]["name"] == "MyClass"
    assert "method1" in analysis["classes"][0]["methods"]
    assert "method2" in analysis["classes"][0]["methods"]


def test_modification_confidence_score():
    """Test modification confidence scoring"""
    engine = SelfModificationEngine()
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test",
        description="High confidence",
        modified_code="code",
        confidence=0.95
    )
    
    mod = engine.modifications[mod_id]
    assert mod.confidence_score == 0.95


def test_modification_backup():
    """Test modification backup mechanism"""
    engine = SelfModificationEngine()
    
    original = "def old(): pass"
    modified = "def new(): pass"
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.REFACTORING,
        target_module="test",
        description="Refactor",
        modified_code=modified,
        original_code=original
    )
    
    mod = engine.modifications[mod_id]
    assert mod.backup_code == original
    assert mod.can_rollback is True


def test_safe_mode_enforcement():
    """Test safe mode prevents unapproved modifications"""
    engine = SelfModificationEngine(safe_mode=True)
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.FUNCTION_MODIFICATION,
        target_module="critical_module",
        description="Dangerous change",
        modified_code="# risky code"
    )
    
    # Should not apply without validation
    applied = engine.apply_modification(mod_id)
    assert applied is False


def test_unsafe_mode_allows_modifications():
    """Test unsafe mode allows modifications without validation"""
    engine = SelfModificationEngine(safe_mode=False)
    
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="test",
        description="Test",
        modified_code="def test(): pass"
    )
    
    # Should apply even without validation in unsafe mode
    applied = engine.apply_modification(mod_id)
    assert applied is True

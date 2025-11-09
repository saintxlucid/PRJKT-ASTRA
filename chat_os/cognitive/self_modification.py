"""
ASTRA OS - Phase 9: Self-Modification Engine

Enables ASTRA to analyze, understand, and modify its own code through
meta-programming capabilities. Supports safe self-improvement through
pattern recognition, code generation, testing, and rollback mechanisms.

Key capabilities:
- Code analysis and AST introspection
- Pattern detection in codebase
- Dynamic code generation
- Self-testing and validation
- Safe execution with rollback
- Evolution tracking
"""

import ast
import inspect
import importlib
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from pathlib import Path
from enum import Enum
import hashlib
import time
import copy


class ModificationType(Enum):
    """Types of self-modifications"""
    FUNCTION_CREATION = "function_creation"
    FUNCTION_MODIFICATION = "function_modification"
    CLASS_CREATION = "class_creation"
    CLASS_MODIFICATION = "class_modification"
    MODULE_CREATION = "module_creation"
    OPTIMIZATION = "optimization"
    REFACTORING = "refactoring"
    BUG_FIX = "bug_fix"


class ValidationStatus(Enum):
    """Validation status for modifications"""
    PENDING = "pending"
    VALIDATING = "validating"
    PASSED = "passed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class CodePattern:
    """Represents a detected pattern in code"""
    pattern_id: str
    pattern_type: str  # "function", "class", "idiom", "anti-pattern"
    description: str
    ast_structure: dict  # Simplified AST representation
    occurrences: list[str] = field(default_factory=list)  # File paths
    frequency: int = 0
    complexity_score: float = 0.0
    optimization_potential: float = 0.0  # [0-1]
    
    def __hash__(self):
        return hash(self.pattern_id)


@dataclass
class CodeModification:
    """Represents a self-modification to the codebase"""
    modification_id: str
    timestamp: float
    modification_type: ModificationType
    description: str
    
    # Source information
    target_module: str
    target_function: Optional[str] = None
    target_class: Optional[str] = None
    
    # Code content
    original_code: str = ""
    modified_code: str = ""
    generated_code: str = ""
    
    # Validation
    validation_status: ValidationStatus = ValidationStatus.PENDING
    test_results: dict = field(default_factory=dict)
    performance_before: Optional[float] = None
    performance_after: Optional[float] = None
    
    # Rollback capability
    backup_code: str = ""
    can_rollback: bool = True
    rolled_back: bool = False
    
    # Metadata
    reason: str = ""
    confidence_score: float = 0.0  # [0-1]
    risk_assessment: str = "low"  # "low", "medium", "high"
    applied: bool = False


@dataclass
class EvolutionRecord:
    """Tracks evolution of the system over time"""
    generation: int
    timestamp: float
    modifications: list[str]  # modification_ids
    total_functions: int
    total_classes: int
    total_lines: int
    complexity_score: float
    performance_score: float
    test_coverage: float
    improvement_metrics: dict = field(default_factory=dict)


class SelfModificationEngine:
    """
    Meta-programming engine that enables ASTRA to modify its own code.
    
    Provides safe self-improvement through:
    - Code analysis and pattern detection
    - Dynamic code generation
    - Validation and testing
    - Rollback mechanisms
    - Evolution tracking
    """
    
    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode  # If True, modifications require validation
        
        # Pattern library
        self.detected_patterns: dict[str, CodePattern] = {}
        self.pattern_library: dict[str, CodePattern] = {}
        
        # Modification tracking
        self.modifications: dict[str, CodeModification] = {}
        self.pending_modifications: list[str] = []
        self.applied_modifications: list[str] = []
        self.failed_modifications: list[str] = []
        
        # Evolution tracking
        self.evolution_history: list[EvolutionRecord] = []
        self.current_generation: int = 0
        
        # Code cache (for rollback)
        self.code_cache: dict[str, str] = {}
        
        # Generated functions (runtime)
        self.generated_functions: dict[str, Callable] = {}
        
        # Statistics
        self.total_analyses: int = 0
        self.successful_modifications: int = 0
        self.rolled_back_modifications: int = 0
    
    def analyze_code(self, code: str, context: str = "") -> dict[str, Any]:
        """
        Analyze code using AST (Abstract Syntax Tree).
        
        Returns analysis including:
        - Functions, classes, imports
        - Complexity metrics
        - Detected patterns
        - Optimization opportunities
        """
        self.total_analyses += 1
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "error": f"Syntax error: {e}",
                "valid": False
            }
        
        analysis = {
            "valid": True,
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity": 0,
            "lines": len(code.split('\n')),
            "patterns": []
        }
        
        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                analysis["functions"].append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "lineno": node.lineno,
                    "complexity": self._calculate_complexity(node)
                })
                analysis["complexity"] += self._calculate_complexity(node)
            
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                analysis["classes"].append({
                    "name": node.name,
                    "methods": methods,
                    "lineno": node.lineno
                })
            
            elif isinstance(node, ast.Import):
                analysis["imports"].extend([alias.name for alias in node.names])
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    analysis["imports"].append(node.module)
        
        # Detect patterns
        patterns = self._detect_patterns(tree)
        analysis["patterns"] = [p.pattern_id for p in patterns]
        
        # Store patterns
        for pattern in patterns:
            self.detected_patterns[pattern.pattern_id] = pattern
        
        return analysis
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of an AST node"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _detect_patterns(self, tree: ast.AST) -> list[CodePattern]:
        """Detect common patterns in AST"""
        patterns = []
        
        # Pattern 1: Functions with similar structure
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        for func in functions:
            # Simple pattern: function structure
            pattern_id = f"func_pattern_{func.name}"
            pattern = CodePattern(
                pattern_id=pattern_id,
                pattern_type="function",
                description=f"Function pattern: {func.name}",
                ast_structure={
                    "type": "function",
                    "name": func.name,
                    "args": len(func.args.args),
                    "complexity": self._calculate_complexity(func)
                },
                frequency=1
            )
            patterns.append(pattern)
        
        return patterns
    
    def generate_function(
        self,
        function_name: str,
        parameters: list[str],
        body_template: str,
        docstring: str = ""
    ) -> Callable:
        """
        Generate a new function dynamically.
        
        Args:
            function_name: Name of the function
            parameters: List of parameter names
            body_template: Python code for function body
            docstring: Function documentation
        
        Returns:
            Callable function object
        """
        # Build function code
        params_str = ", ".join(parameters)
        
        code_lines = [
            f"def {function_name}({params_str}):"
        ]
        
        if docstring:
            code_lines.append(f'    """{docstring}"""')
        
        # Add body (indent each line)
        for line in body_template.split('\n'):
            if line.strip():
                code_lines.append(f"    {line}")
        
        code = "\n".join(code_lines)
        
        # Compile and execute
        namespace = {}
        try:
            exec(code, namespace)
            func = namespace[function_name]
            
            # Store generated function
            self.generated_functions[function_name] = func
            
            # Create modification record
            mod_id = f"gen_func_{function_name}_{int(time.time())}"
            modification = CodeModification(
                modification_id=mod_id,
                timestamp=time.time(),
                modification_type=ModificationType.FUNCTION_CREATION,
                description=f"Generated function: {function_name}",
                target_module="__runtime__",
                target_function=function_name,
                generated_code=code,
                validation_status=ValidationStatus.PASSED,
                confidence_score=1.0,
                risk_assessment="low",
                applied=True
            )
            
            self.modifications[mod_id] = modification
            self.applied_modifications.append(mod_id)
            self.successful_modifications += 1
            
            return func
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate function: {e}")
    
    def propose_modification(
        self,
        modification_type: ModificationType,
        target_module: str,
        description: str,
        modified_code: str,
        original_code: str = "",
        reason: str = "",
        confidence: float = 0.5
    ) -> str:
        """
        Propose a modification to the codebase.
        
        Returns:
            modification_id
        """
        mod_id = hashlib.md5(
            f"{target_module}_{description}_{time.time()}".encode()
        ).hexdigest()[:16]
        
        # Assess risk based on modification type
        risk_map = {
            ModificationType.FUNCTION_CREATION: "low",
            ModificationType.OPTIMIZATION: "low",
            ModificationType.REFACTORING: "medium",
            ModificationType.FUNCTION_MODIFICATION: "medium",
            ModificationType.CLASS_MODIFICATION: "high",
            ModificationType.BUG_FIX: "medium",
        }
        risk = risk_map.get(modification_type, "high")
        
        modification = CodeModification(
            modification_id=mod_id,
            timestamp=time.time(),
            modification_type=modification_type,
            description=description,
            target_module=target_module,
            original_code=original_code,
            modified_code=modified_code,
            backup_code=original_code,
            reason=reason,
            confidence_score=confidence,
            risk_assessment=risk
        )
        
        self.modifications[mod_id] = modification
        self.pending_modifications.append(mod_id)
        
        return mod_id
    
    def validate_modification(
        self,
        modification_id: str,
        test_function: Optional[Callable] = None
    ) -> bool:
        """
        Validate a proposed modification.
        
        Args:
            modification_id: ID of modification to validate
            test_function: Optional test function to run
        
        Returns:
            True if validation passed, False otherwise
        """
        if modification_id not in self.modifications:
            return False
        
        mod = self.modifications[modification_id]
        mod.validation_status = ValidationStatus.VALIDATING
        
        # Check syntax
        try:
            ast.parse(mod.modified_code)
            mod.test_results["syntax_check"] = "passed"
        except SyntaxError as e:
            mod.test_results["syntax_check"] = f"failed: {e}"
            mod.validation_status = ValidationStatus.FAILED
            self.failed_modifications.append(modification_id)
            return False
        
        # Run custom test if provided
        if test_function:
            try:
                result = test_function(mod.modified_code)
                mod.test_results["custom_test"] = "passed" if result else "failed"
                
                if not result:
                    mod.validation_status = ValidationStatus.FAILED
                    self.failed_modifications.append(modification_id)
                    return False
                    
            except Exception as e:
                mod.test_results["custom_test"] = f"error: {e}"
                mod.validation_status = ValidationStatus.FAILED
                self.failed_modifications.append(modification_id)
                return False
        
        # Validation passed
        mod.validation_status = ValidationStatus.PASSED
        return True
    
    def apply_modification(self, modification_id: str, force: bool = False) -> bool:
        """
        Apply a validated modification.
        
        Args:
            modification_id: ID of modification to apply
            force: Skip validation if True (dangerous!)
        
        Returns:
            True if applied successfully
        """
        if modification_id not in self.modifications:
            return False
        
        mod = self.modifications[modification_id]
        
        # Check validation status
        if not force and self.safe_mode:
            if mod.validation_status != ValidationStatus.PASSED:
                return False
        
        # For runtime modifications (generated functions)
        if mod.target_module == "__runtime__":
            # Already applied during generation
            mod.applied = True
            return True
        
        # For file-based modifications (would write to file in real implementation)
        # Here we just mark as applied
        mod.applied = True
        
        # Move from pending to applied
        if modification_id in self.pending_modifications:
            self.pending_modifications.remove(modification_id)
        self.applied_modifications.append(modification_id)
        self.successful_modifications += 1
        
        return True
    
    def rollback_modification(self, modification_id: str) -> bool:
        """
        Rollback a modification to previous state.
        
        Returns:
            True if rolled back successfully
        """
        if modification_id not in self.modifications:
            return False
        
        mod = self.modifications[modification_id]
        
        if not mod.can_rollback:
            return False
        
        if not mod.applied:
            return False
        
        # For runtime modifications
        if mod.target_module == "__runtime__" and mod.target_function:
            if mod.target_function in self.generated_functions:
                del self.generated_functions[mod.target_function]
        
        # Mark as rolled back
        mod.rolled_back = True
        mod.applied = False
        mod.validation_status = ValidationStatus.ROLLED_BACK
        
        # Update lists
        if modification_id in self.applied_modifications:
            self.applied_modifications.remove(modification_id)
        
        self.rolled_back_modifications += 1
        
        return True
    
    def optimize_function(
        self,
        func: Callable,
        optimization_type: str = "general"
    ) -> Optional[Callable]:
        """
        Attempt to optimize a function.
        
        Args:
            func: Function to optimize
            optimization_type: Type of optimization ("general", "speed", "memory")
        
        Returns:
            Optimized function or None if optimization failed
        """
        # Get source code
        try:
            source = inspect.getsource(func)
        except Exception:
            return None
        
        # Analyze current function
        analysis = self.analyze_code(source)
        
        # Simple optimization: memoization for pure functions
        if optimization_type == "speed":
            # Generate memoized version
            func_name = func.__name__
            memoized_name = f"{func_name}_optimized"
            
            # Create memoization wrapper
            memoized_code = f"""
def {memoized_name}(*args, **kwargs):
    cache_key = str(args) + str(kwargs)
    if cache_key not in {memoized_name}._cache:
        {memoized_name}._cache[cache_key] = {func_name}(*args, **kwargs)
    return {memoized_name}._cache[cache_key]

{memoized_name}._cache = {{}}
"""
            
            # Compile optimized version
            namespace = {func_name: func}
            exec(memoized_code, namespace)
            optimized_func = namespace[memoized_name]
            
            # Record modification
            mod_id = f"opt_{func_name}_{int(time.time())}"
            modification = CodeModification(
                modification_id=mod_id,
                timestamp=time.time(),
                modification_type=ModificationType.OPTIMIZATION,
                description=f"Memoized {func_name} for speed",
                target_module="__runtime__",
                target_function=memoized_name,
                original_code=source,
                modified_code=memoized_code,
                validation_status=ValidationStatus.PASSED,
                reason=f"Optimization type: {optimization_type}",
                confidence_score=0.8,
                risk_assessment="low",
                applied=True
            )
            
            self.modifications[mod_id] = modification
            self.applied_modifications.append(mod_id)
            self.successful_modifications += 1
            
            return optimized_func
        
        return None
    
    def evolve_generation(self) -> EvolutionRecord:
        """
        Create a new generation snapshot.
        
        Tracks system evolution over time.
        """
        self.current_generation += 1
        
        # Collect metrics
        total_functions = len(self.generated_functions)
        total_modifications = len(self.applied_modifications)
        
        record = EvolutionRecord(
            generation=self.current_generation,
            timestamp=time.time(),
            modifications=self.applied_modifications.copy(),
            total_functions=total_functions,
            total_classes=0,  # Would count classes in real implementation
            total_lines=sum(len(m.modified_code.split('\n')) 
                          for m in self.modifications.values() if m.applied),
            complexity_score=sum(m.test_results.get("complexity", 0) 
                               for m in self.modifications.values() if m.applied),
            performance_score=0.0,  # Would measure performance in real implementation
            test_coverage=0.0,  # Would measure coverage in real implementation
            improvement_metrics={
                "successful_modifications": self.successful_modifications,
                "failed_modifications": len(self.failed_modifications),
                "rollbacks": self.rolled_back_modifications,
                "pending": len(self.pending_modifications)
            }
        )
        
        self.evolution_history.append(record)
        return record
    
    def get_modification_stats(self) -> dict[str, Any]:
        """Get statistics about modifications"""
        total = len(self.modifications)
        
        return {
            "total_modifications": total,
            "pending": len(self.pending_modifications),
            "applied": len(self.applied_modifications),
            "failed": len(self.failed_modifications),
            "rolled_back": self.rolled_back_modifications,
            "success_rate": (self.successful_modifications / total) if total > 0 else 0.0,
            "current_generation": self.current_generation,
            "total_analyses": self.total_analyses,
            "generated_functions": len(self.generated_functions),
            "detected_patterns": len(self.detected_patterns)
        }
    
    def get_evolution_history(self) -> list[EvolutionRecord]:
        """Get complete evolution history"""
        return self.evolution_history.copy()
    
    def get_modification(self, modification_id: str) -> Optional[CodeModification]:
        """Get modification by ID"""
        return self.modifications.get(modification_id)
    
    def get_generated_function(self, function_name: str) -> Optional[Callable]:
        """Get a generated function by name"""
        return self.generated_functions.get(function_name)


# Global singleton instance
_self_modification_engine: Optional[SelfModificationEngine] = None


def get_self_modification_engine(safe_mode: bool = True) -> SelfModificationEngine:
    """Get or create the global self-modification engine"""
    global _self_modification_engine
    if _self_modification_engine is None:
        _self_modification_engine = SelfModificationEngine(safe_mode=safe_mode)
    return _self_modification_engine


# Example usage
if __name__ == "__main__":
    engine = get_self_modification_engine(safe_mode=True)
    
    # Example 1: Analyze code
    sample_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""
    
    analysis = engine.analyze_code(sample_code)
    print(f"Analysis: {analysis['functions']}")
    print(f"Complexity: {analysis['complexity']}")
    
    # Example 2: Generate a new function
    add_func = engine.generate_function(
        function_name="dynamic_add",
        parameters=["a", "b"],
        body_template="return a + b",
        docstring="Dynamically generated addition function"
    )
    
    result = add_func(5, 3)
    print(f"Generated function result: {result}")  # 8
    
    # Example 3: Propose and validate modification
    mod_id = engine.propose_modification(
        modification_type=ModificationType.OPTIMIZATION,
        target_module="math_utils",
        description="Optimize fibonacci with memoization",
        modified_code="# Optimized code here",
        original_code=sample_code,
        reason="Improve performance",
        confidence=0.9
    )
    
    # Validate
    valid = engine.validate_modification(mod_id)
    print(f"Modification valid: {valid}")
    
    # Apply if valid
    if valid:
        engine.apply_modification(mod_id)
    
    # Example 4: Evolution tracking
    record = engine.evolve_generation()
    print(f"Generation {record.generation}: {record.total_functions} functions")
    
    # Example 5: Statistics
    stats = engine.get_modification_stats()
    print(f"Stats: {stats}")

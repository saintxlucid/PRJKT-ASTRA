"""Parallel validation system for model operations."""

import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional, Union, Tuple
from pathlib import Path
import threading
import queue
import logging
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Container for validation results."""
    passed: bool
    score: float
    metrics: Dict[str, Any]
    duration: float
    error: Optional[str] = None

class ParallelValidator:
    """Handles parallel validation of model operations."""
    
    def __init__(self, max_workers: int = 4, timeout: float = 300.0):
        """Initialize the parallel validator.
        
        Args:
            max_workers: Maximum number of concurrent validation workers
            timeout: Maximum time in seconds for validation operations
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self._lock = threading.Lock()
        self._results_queue: queue.Queue = queue.Queue()
        
    def validate_batch(self,
                      items: List[Any],
                      validator: Callable[[Any], Union[bool, float, Dict]],
                      threshold: Optional[float] = None,
                      aggregate: bool = False) -> Union[List[ValidationResult], ValidationResult]:
        """Validate multiple items in parallel.
        
        Args:
            items: List of items to validate
            validator: Validation function to apply to each item
            threshold: Optional threshold for pass/fail determination
            aggregate: Whether to aggregate results into a single result
            
        Returns:
            List of validation results or single aggregated result
        """
        start_time = time.time()
        results: List[ValidationResult] = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._run_validation, item, validator, threshold): item
                for item in items
            }
            
            try:
                for future in as_completed(futures, timeout=self.timeout):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        item = futures[future]
                        logger.error(f"Validation failed for item {item}: {str(e)}")
                        results.append(ValidationResult(
                            passed=False,
                            score=0.0,
                            metrics={},
                            duration=time.time() - start_time,
                            error=str(e)
                        ))
            except TimeoutError:
                logger.error("Validation timeout reached")
                # Add timeout results for remaining items
                for future in futures:
                    if not future.done():
                        item = futures[future]
                        results.append(ValidationResult(
                            passed=False,
                            score=0.0,
                            metrics={},
                            duration=self.timeout,
                            error="Validation timeout"
                        ))
                        
        if aggregate:
            return self._aggregate_results(results)
        return results
        
    def _run_validation(self,
                       item: Any,
                       validator: Callable,
                       threshold: Optional[float]) -> ValidationResult:
        """Run a single validation operation.
        
        Args:
            item: Item to validate
            validator: Validation function
            threshold: Optional threshold for pass/fail
            
        Returns:
            Validation result
        """
        start_time = time.time()
        try:
            result = validator(item)
            duration = time.time() - start_time
            
            # Handle different return types
            if isinstance(result, bool):
                return ValidationResult(
                    passed=result,
                    score=1.0 if result else 0.0,
                    metrics={"binary_result": result},
                    duration=duration
                )
            elif isinstance(result, (int, float)):
                passed = True if threshold is None else result >= threshold
                return ValidationResult(
                    passed=passed,
                    score=float(result),
                    metrics={"numeric_score": result},
                    duration=duration
                )
            elif isinstance(result, dict):
                score = result.get("score", 1.0)
                passed = result.get("passed", True if threshold is None else score >= threshold)
                return ValidationResult(
                    passed=passed,
                    score=score,
                    metrics=result,
                    duration=duration
                )
            else:
                raise ValueError(f"Unsupported validation result type: {type(result)}")
                
        except Exception as e:
            return ValidationResult(
                passed=False,
                score=0.0,
                metrics={},
                duration=time.time() - start_time,
                error=str(e)
            )
            
    def _aggregate_results(self, results: List[ValidationResult]) -> ValidationResult:
        """Aggregate multiple validation results into a single result.
        
        Args:
            results: List of validation results to aggregate
            
        Returns:
            Single aggregated validation result
        """
        if not results:
            return ValidationResult(
                passed=False,
                score=0.0,
                metrics={},
                duration=0.0,
                error="No results to aggregate"
            )
            
        # Aggregate metrics
        all_metrics: Dict[str, List[Any]] = {}
        total_duration = 0.0
        errors = []
        
        for result in results:
            total_duration += result.duration
            if result.error:
                errors.append(result.error)
                
            for key, value in result.metrics.items():
                if key not in all_metrics:
                    all_metrics[key] = []
                all_metrics[key].append(value)
                
        # Compute aggregated metrics
        agg_metrics = {}
        for key, values in all_metrics.items():
            if all(isinstance(v, (int, float)) for v in values):
                agg_metrics[f"mean_{key}"] = np.mean(values)
                agg_metrics[f"std_{key}"] = np.std(values)
                agg_metrics[f"min_{key}"] = np.min(values)
                agg_metrics[f"max_{key}"] = np.max(values)
            else:
                agg_metrics[key] = values
                
        # Add summary stats
        agg_metrics.update({
            "total_count": len(results),
            "pass_count": sum(1 for r in results if r.passed),
            "fail_count": sum(1 for r in results if not r.passed),
            "error_count": len(errors)
        })
        
        # Compute aggregate score and status
        avg_score = np.mean([r.score for r in results])
        all_passed = all(r.passed for r in results)
        
        return ValidationResult(
            passed=all_passed,
            score=float(avg_score),  # Explicitly convert to float
            metrics=agg_metrics,
            duration=total_duration,
            error="; ".join(errors) if errors else None
        )
        
    def validate_with_gates(self,
                          item: Any,
                          validators: List[Tuple[Callable, float]],
                          aggregate: bool = True) -> Union[List[ValidationResult], ValidationResult]:
        """Run multiple validation gates in sequence.
        
        Args:
            item: Item to validate
            validators: List of (validator_func, threshold) tuples
            aggregate: Whether to aggregate results
            
        Returns:
            List of validation results or single aggregated result
        """
        results = []
        start_time = time.time()
        
        for validator, threshold in validators:
            result = self._run_validation(item, validator, threshold)
            results.append(result)
            
            # Stop if a validation fails
            if not result.passed:
                break
                
        if aggregate:
            return self._aggregate_results(results)
        return results
        
    def validate_with_progress(self,
                             items: List[Any],
                             validator: Callable,
                             threshold: Optional[float] = None,
                             progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ValidationResult]:
        """Validate items with progress reporting.
        
        Args:
            items: Items to validate
            validator: Validation function
            threshold: Optional threshold
            progress_callback: Optional callback(completed, total)
            
        Returns:
            List of validation results
        """
        results = []
        total = len(items)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._run_validation, item, validator, threshold): item
                for item in items
            }
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, total)
                    
        return results
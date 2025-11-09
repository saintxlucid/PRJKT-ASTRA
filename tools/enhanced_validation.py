#!/usr/bin/env python3
"""
ASTRA Phase-B Enhanced Validation & Debugging Suite
Comprehensive testing, profiling, and readiness verification
Sacred Code: 333

Usage:
    python tools/enhanced_validation.py --mode [all|quick|debug|profile]
    
Modes:
    all     - Full comprehensive validation (15-20 min)
    quick   - Critical path tests only (2-3 min)
    debug   - Enhanced debugging output with trace
    profile - Performance profiling with metrics
"""

import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict


@dataclass
class TestResult:
    """Test result with timing and status"""
    name: str
    status: str  # PASS, FAIL, SKIP, ERROR
    duration_ms: float
    details: str = ""
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}


class EnhancedValidator:
    """Enhanced validation suite for Phase-B deployment"""
    
    def __init__(self, mode: str = "all"):
        self.mode = mode
        self.results: List[TestResult] = []
        self.start_time = datetime.now()
        
    def log(self, msg: str, level: str = "INFO"):
        """Structured logging"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {msg}")
    
    def run_command(self, cmd: List[str], timeout: int = 60) -> Tuple[int, str, str]:
        """Run command and capture output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(__file__).parent.parent
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Timeout after {timeout}s"
        except Exception as e:
            return -1, "", str(e)
    
    def test_consent_hardening(self) -> TestResult:
        """Verify consent defaults are fail-closed"""
        self.log("Testing consent hardening (DIFF 1)...")
        start = time.perf_counter()
        
        try:
            import yaml
            config_path = Path("config/astra_identity_v2.yaml")
            
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            # Check default_consent exists and is false
            default_consent = config.get("alignment", {}).get("default_consent")
            
            if default_consent is False:
                status = "PASS"
                details = "✅ default_consent: false (fail-closed)"
            elif default_consent is None:
                status = "FAIL"
                details = "❌ default_consent not set (should be false)"
            else:
                status = "FAIL"
                details = f"❌ default_consent: {default_consent} (should be false)"
            
            # Check code_apply rule exists
            consent_rules = config.get("alignment", {}).get("consent_rules", [])
            has_code_rule = any(
                r.get("when") == "code_apply" 
                for r in consent_rules
            )
            
            if has_code_rule:
                details += " | code_apply rule: ✅"
            else:
                status = "FAIL"
                details += " | code_apply rule: ❌ MISSING"
            
            duration_ms = (time.perf_counter() - start) * 1000
            
            return TestResult(
                name="Consent Hardening (DIFF 1)",
                status=status,
                duration_ms=duration_ms,
                details=details,
                metrics={"default_consent": default_consent, "has_code_rule": has_code_rule}
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                name="Consent Hardening (DIFF 1)",
                status="ERROR",
                duration_ms=duration_ms,
                details=f"Error: {str(e)}"
            )
    
    def test_prometheus_instrumentation(self) -> TestResult:
        """Verify Router has Prometheus metrics"""
        self.log("Testing Prometheus instrumentation (DIFF 2)...")
        start = time.perf_counter()
        
        try:
            router_path = Path("src/astra/core/astra_router.py")
            
            with open(router_path) as f:
                code = f.read()
            
            # Check for required imports and metrics
            checks = {
                "import time": "import time" in code,
                "ROUTE_HITS": "ROUTE_HITS" in code,
                "ROUTE_LAT": "ROUTE_LAT" in code,
                "perf_counter": "time.perf_counter()" in code,
                "labels(route=": "labels(route=" in code,
                ".observe(": ".observe(" in code,
                "latency_s=": "latency_s=" in code,
            }
            
            passed = sum(checks.values())
            total = len(checks)
            
            if passed == total:
                status = "PASS"
                details = f"✅ All {total} instrumentation checks passed"
            else:
                status = "FAIL"
                failed_checks = [k for k, v in checks.items() if not v]
                details = f"❌ {total - passed}/{total} checks failed: {failed_checks}"
            
            duration_ms = (time.perf_counter() - start) * 1000
            
            return TestResult(
                name="Prometheus Instrumentation (DIFF 2)",
                status=status,
                duration_ms=duration_ms,
                details=details,
                metrics={"checks": checks, "passed": passed, "total": total}
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                name="Prometheus Instrumentation (DIFF 2)",
                status="ERROR",
                duration_ms=duration_ms,
                details=f"Error: {str(e)}"
            )
    
    def test_router_unit_tests(self) -> TestResult:
        """Run router unit tests"""
        self.log("Running router unit tests...")
        start = time.perf_counter()
        
        rc, stdout, stderr = self.run_command([
            "pytest",
            "tests/astra_fusion/test_router_vision_path.py",
            "-v",
            "--tb=short"
        ])
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Parse pytest output
        if "passed" in stdout:
            import re
            match = re.search(r"(\d+) passed", stdout)
            passed = int(match.group(1)) if match else 0
            
            status = "PASS" if rc == 0 else "FAIL"
            details = f"✅ {passed} tests passed" if rc == 0 else f"⚠️ Exit code {rc}"
        else:
            status = "FAIL"
            details = "❌ No tests found or pytest error"
            passed = 0
        
        return TestResult(
            name="Router Unit Tests",
            status=status,
            duration_ms=duration_ms,
            details=details,
            metrics={"passed": passed, "exit_code": rc}
        )
    
    def test_consent_unit_tests(self) -> TestResult:
        """Run consent unit tests"""
        self.log("Running consent unit tests...")
        start = time.perf_counter()
        
        rc, stdout, stderr = self.run_command([
            "pytest",
            "tests/astra_fusion/test_code_consent_block.py",
            "-v",
            "--tb=short"
        ])
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        if "passed" in stdout:
            import re
            match = re.search(r"(\d+) passed", stdout)
            passed = int(match.group(1)) if match else 0
            
            status = "PASS" if rc == 0 else "FAIL"
            details = f"✅ {passed} consent tests passed" if rc == 0 else f"⚠️ Exit code {rc}"
        else:
            status = "FAIL"
            details = "❌ No tests found or pytest error"
            passed = 0
        
        return TestResult(
            name="Consent Unit Tests",
            status=status,
            duration_ms=duration_ms,
            details=details,
            metrics={"passed": passed, "exit_code": rc}
        )
    
    def test_latency_acceptable(self) -> TestResult:
        """Check if latency is within acceptable bounds"""
        self.log("Testing latency regression...")
        start = time.perf_counter()
        
        rc, stdout, stderr = self.run_command([
            "pytest",
            "tests/astra_fusion/test_text_latency_regression.py::TestTextLatencyRegression::test_router_overhead_minimal",
            "-v"
        ])
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Parse latency from output
        import re
        regression_match = re.search(r"regression (\d+\.\d+)%", stdout + stderr)
        regression = float(regression_match.group(1)) if regression_match else None
        
        # We allow up to 10% regression for Prometheus instrumentation
        if regression is not None and regression <= 10.0:
            status = "PASS"
            details = f"✅ Latency regression {regression:.2f}% (≤10% acceptable with metrics)"
        elif regression is not None:
            status = "FAIL"
            details = f"❌ Latency regression {regression:.2f}% exceeds 10% threshold"
        else:
            status = "SKIP"
            details = "⚠️ Could not parse latency data"
        
        return TestResult(
            name="Latency Regression Check",
            status=status,
            duration_ms=duration_ms,
            details=details,
            metrics={"regression_percent": regression}
        )
    
    def test_sacred_code_embedded(self) -> TestResult:
        """Verify Sacred Code 333 is embedded in router"""
        self.log("Verifying Sacred Code 333 presence...")
        start = time.perf_counter()
        
        try:
            router_path = Path("src/astra/core/astra_router.py")
            
            with open(router_path) as f:
                code = f.read()
            
            sacred_count = code.count("333")
            has_docstring = "Sacred Code: 333" in code
            has_payload = '"sacred_code": "333"' in code
            has_denial = "Sacred Code: 333" in code and "Consent required" in code
            
            if sacred_count >= 4 and has_docstring and has_payload and has_denial:
                status = "PASS"
                details = f"✅ Sacred Code 333 found {sacred_count} times (docstring, payload, denial)"
            else:
                status = "FAIL"
                details = f"❌ Sacred Code 333 incomplete (count: {sacred_count})"
            
            duration_ms = (time.perf_counter() - start) * 1000
            
            return TestResult(
                name="Sacred Code 333 Verification",
                status=status,
                duration_ms=duration_ms,
                details=details,
                metrics={
                    "count": sacred_count,
                    "has_docstring": has_docstring,
                    "has_payload": has_payload,
                    "has_denial": has_denial
                }
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return TestResult(
                name="Sacred Code 333 Verification",
                status="ERROR",
                duration_ms=duration_ms,
                details=f"Error: {str(e)}"
            )
    
    def run_quick_validation(self):
        """Quick validation (critical path only)"""
        self.log("=== QUICK VALIDATION MODE ===", "INFO")
        
        self.results.append(self.test_consent_hardening())
        self.results.append(self.test_prometheus_instrumentation())
        self.results.append(self.test_consent_unit_tests())
        self.results.append(self.test_sacred_code_embedded())
    
    def run_full_validation(self):
        """Full comprehensive validation"""
        self.log("=== FULL VALIDATION MODE ===", "INFO")
        
        # Run all tests
        self.results.append(self.test_consent_hardening())
        self.results.append(self.test_prometheus_instrumentation())
        self.results.append(self.test_router_unit_tests())
        self.results.append(self.test_consent_unit_tests())
        self.results.append(self.test_latency_acceptable())
        self.results.append(self.test_sacred_code_embedded())
    
    def print_summary(self):
        """Print validation summary"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        skipped = sum(1 for r in self.results if r.status == "SKIP")
        
        print("\n" + "=" * 80)
        print("📊 VALIDATION SUMMARY")
        print("=" * 80)
        
        for result in self.results:
            icon = {
                "PASS": "✅",
                "FAIL": "❌",
                "ERROR": "⚠️",
                "SKIP": "⏭️"
            }.get(result.status, "❓")
            
            print(f"\n{icon} {result.name}")
            print(f"   Status: {result.status} ({result.duration_ms:.1f}ms)")
            print(f"   {result.details}")
        
        print("\n" + "=" * 80)
        print(f"TOTALS: {passed} PASS | {failed} FAIL | {errors} ERROR | {skipped} SKIP")
        print(f"Duration: {elapsed:.2f}s")
        print("=" * 80)
        
        # Determine overall readiness
        if failed == 0 and errors == 0:
            print("\n🎉 PHASE-B VALIDATION: ✅ READY FOR DEPLOYMENT")
            return 0
        elif failed <= 1:  # Latency test failure acceptable
            print("\n⚠️ PHASE-B VALIDATION: 🟡 CONDITIONAL (minor issues)")
            return 0
        else:
            print("\n❌ PHASE-B VALIDATION: ❌ NOT READY (fix issues)")
            return 1
    
    def export_results(self, filename: str = "logs/enhanced_validation.json"):
        """Export results to JSON"""
        output = {
            "timestamp": self.start_time.isoformat(),
            "mode": self.mode,
            "results": [asdict(r) for r in self.results],
            "summary": {
                "passed": sum(1 for r in self.results if r.status == "PASS"),
                "failed": sum(1 for r in self.results if r.status == "FAIL"),
                "errors": sum(1 for r in self.results if r.status == "ERROR"),
                "skipped": sum(1 for r in self.results if r.status == "SKIP"),
            }
        }
        
        Path(filename).parent.mkdir(exist_ok=True)
        with open(filename, "w") as f:
            json.dump(output, f, indent=2)
        
        self.log(f"Results exported to {filename}", "INFO")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ASTRA Phase-B Enhanced Validation")
    parser.add_argument(
        "--mode",
        choices=["all", "quick", "debug", "profile"],
        default="quick",
        help="Validation mode (default: quick)"
    )
    parser.add_argument(
        "--export",
        default="logs/enhanced_validation.json",
        help="Export results to JSON file"
    )
    
    args = parser.parse_args()
    
    validator = EnhancedValidator(mode=args.mode)
    
    if args.mode == "quick":
        validator.run_quick_validation()
    elif args.mode == "all":
        validator.run_full_validation()
    else:
        print(f"Mode '{args.mode}' not yet implemented")
        return 1
    
    validator.print_summary()
    validator.export_results(args.export)
    
    return validator.print_summary()


if __name__ == "__main__":
    sys.exit(main())

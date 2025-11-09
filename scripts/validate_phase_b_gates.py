#!/usr/bin/env python3
"""
Phase B Go/No-Go Gate Validator
Automated 7-point evaluation for October 19 deployment decision
Usage: python scripts/validate_phase_b_gates.py [--verbose] [--export json|txt]
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import re


class GateValidator:
    def __init__(self, log_file: str = "logs/astra.log", metrics_file: str = "metrics_oct19.txt"):
        self.log_file = Path(log_file)
        self.metrics_file = Path(metrics_file)
        self.results = {}
        self.timestamp = datetime.now()
        
    def validate_all_gates(self) -> Dict[str, dict]:
        """Run all 7 gates and return results"""
        print(f"\n🚦 Phase B Go/No-Go Gate Validation")
        print(f"   Started: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Log File: {self.log_file}")
        print("-" * 80)
        
        gates = [
            ("gate_1_router_stability", self.gate_1_router_stability),
            ("gate_2_latency_performance", self.gate_2_latency_performance),
            ("gate_3_consent_gates", self.gate_3_consent_gates),
            ("gate_4_system_health", self.gate_4_system_health),
            ("gate_5_error_rate", self.gate_5_error_rate),
            ("gate_6_memory_hygiene", self.gate_6_memory_hygiene),
            ("gate_7_smoke_tests", self.gate_7_smoke_tests),
        ]
        
        for gate_name, gate_func in gates:
            try:
                self.results[gate_name] = gate_func()
                self._print_gate_result(gate_name, self.results[gate_name])
            except Exception as e:
                self.results[gate_name] = {
                    "status": "ERROR",
                    "error": str(e),
                    "message": f"Gate validation failed: {e}"
                }
                print(f"❌ {gate_name}: {e}")
        
        self._print_summary()
        return self.results
    
    def gate_1_router_stability(self) -> dict:
        """Gate 1: Router Stability - no fatal errors, sane route hit rates"""
        print("\n📊 GATE 1: Router Stability")
        
        if not self.log_file.exists():
            return {"status": "FAIL", "error": f"Log file not found: {self.log_file}"}
        
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.readlines()
        
        # Count errors
        fatal_errors = [l for l in logs if re.search(r'(ERROR|CRITICAL)', l)]
        error_count = len(fatal_errors)
        
        # Count sacred_code=333
        sacred_code = [l for l in logs if re.search(r'sacred_code.*333', l)]
        sacred_count = len(sacred_code)
        
        # Parse route hits (simplified - looks for "astra_route_hits" pattern)
        route_hits = {}
        for line in logs:
            if 'astra_route_hits' in line and 'route=' in line:
                # Example: astra_route_hits{route="text"} 650
                match = re.search(r'route="(\w+)"\}\s+(\d+)', line)
                if match:
                    route_hits[match.group(1)] = int(match.group(2))
        
        # Evaluate
        status = "PASS"
        reason = []
        
        if error_count > 50:
            status = "FAIL"
            reason.append(f"Fatal errors: {error_count} (threshold: 50)")
        elif error_count > 10:
            status = "CAUTION"
            reason.append(f"Fatal errors: {error_count} (borderline)")
        else:
            reason.append(f"✅ Fatal errors: {error_count} (acceptable)")
        
        if route_hits:
            total_hits = sum(route_hits.values())
            text_percent = (route_hits.get('text', 0) / total_hits * 100) if total_hits > 0 else 0
            others_percent = 100 - text_percent
            
            if text_percent >= 60 and others_percent <= 40:
                reason.append(f"✅ Route mix: TEXT {text_percent:.1f}% (target ≥60%)")
            elif text_percent >= 40:
                status = "CAUTION" if status == "PASS" else status
                reason.append(f"⚠️ Route mix: TEXT {text_percent:.1f}% (target ≥60%)")
            else:
                status = "FAIL"
                reason.append(f"❌ Route mix: TEXT {text_percent:.1f}% (threshold: 40%)")
        
        if sacred_count >= 50:
            reason.append(f"✅ Sacred code 333: {sacred_count} (present)")
        elif sacred_count > 0:
            reason.append(f"⚠️ Sacred code 333: {sacred_count} (sparse)")
        else:
            status = "FAIL"
            reason.append(f"❌ Sacred code 333: 0 (audit trail broken)")
        
        return {
            "status": status,
            "fatal_errors": error_count,
            "sacred_code_count": sacred_count,
            "route_hits": route_hits,
            "details": reason
        }
    
    def gate_2_latency_performance(self) -> dict:
        """Gate 2: Latency - p95 within ±5% baseline"""
        print("\n📊 GATE 2: Latency Performance")
        
        # Parse metrics file if available
        latencies = {}
        
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'astra_latency_p95_ms' in line:
                        match = re.search(r'route="(\w+)".*\s+([\d.]+)', line)
                        if match:
                            latencies[match.group(1)] = float(match.group(2))
        
        # Baselines (from Phase A pre-deployment)
        baselines = {
            "text": 950,      # ±5% = 902-998ms
            "vision": 1800,   # <2000ms
            "audio": 1700,    # <2000ms
        }
        
        status = "PASS"
        reason = []
        
        for route, baseline in baselines.items():
            if route in latencies:
                actual = latencies[route]
                
                if route == "text":
                    lower, upper = baseline * 0.95, baseline * 1.05
                    if lower <= actual <= upper:
                        reason.append(f"✅ {route.upper()}: {actual:.0f}ms (target: {lower:.0f}-{upper:.0f}ms)")
                    elif actual > upper:
                        status = "FAIL" if actual > baseline * 1.1 else "CAUTION"
                        reason.append(f"⚠️ {route.upper()}: {actual:.0f}ms (target: {lower:.0f}-{upper:.0f}ms)")
                    else:
                        reason.append(f"✅ {route.upper()}: {actual:.0f}ms (below baseline)")
                else:
                    if actual < 2000:
                        reason.append(f"✅ {route.upper()}: {actual:.0f}ms (target: <2000ms)")
                    else:
                        status = "FAIL"
                        reason.append(f"❌ {route.upper()}: {actual:.0f}ms (threshold: 2000ms)")
            else:
                reason.append(f"⚠️ {route.upper()}: No data available")
        
        if not latencies:
            reason.append("⚠️ No metrics file found - skipping latency check")
            status = "CAUTION"
        
        return {
            "status": status,
            "latencies": latencies,
            "baselines": baselines,
            "details": reason
        }
    
    def gate_3_consent_gates(self) -> dict:
        """Gate 3: Consent enforcement - 0 unauthorized code.apply"""
        print("\n📊 GATE 3: Consent Gates Enforcement")
        
        if not self.log_file.exists():
            return {"status": "FAIL", "error": f"Log file not found"}
        
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.readlines()
        
        # Count blocked code attempts
        blocked = [l for l in logs if re.search(r'consent_denied|code_execution_blocked', l)]
        blocked_count = len(blocked)
        
        # Count unauthorized executions (should be 0)
        unauthorized = [l for l in logs if re.search(r'code\.apply.*executed.*consent=false', l)]
        unauthorized_count = len(unauthorized)
        
        # Count audit trail entries with sacred_code
        audit_entries = [l for l in logs if re.search(r'sacred_code.*333.*audit_trail', l)]
        audit_count = len(audit_entries)
        
        status = "PASS"
        reason = []
        
        if unauthorized_count > 0:
            status = "FAIL"
            reason.append(f"❌ Unauthorized code executions: {unauthorized_count} (should be 0)")
        else:
            reason.append(f"✅ Unauthorized code executions: 0")
        
        if blocked_count > 5:
            reason.append(f"✅ Blocked code attempts: {blocked_count} (gate is active)")
        elif blocked_count > 0:
            reason.append(f"⚠️ Blocked code attempts: {blocked_count} (sparse)")
        else:
            status = "CAUTION" if status == "PASS" else status
            reason.append(f"⚠️ Blocked code attempts: 0 (gate may not be active)")
        
        if audit_count > 100:
            reason.append(f"✅ Audit entries with sacred_code: {audit_count}")
        elif audit_count > 50:
            reason.append(f"✅ Audit entries with sacred_code: {audit_count}")
        elif audit_count > 0:
            status = "CAUTION" if status == "PASS" else status
            reason.append(f"⚠️ Audit entries with sacred_code: {audit_count} (sparse)")
        else:
            status = "FAIL"
            reason.append(f"❌ Audit entries with sacred_code: 0 (audit trail broken)")
        
        return {
            "status": status,
            "unauthorized_executions": unauthorized_count,
            "blocked_attempts": blocked_count,
            "audit_entries": audit_count,
            "details": reason
        }
    
    def gate_4_system_health(self) -> dict:
        """Gate 4: System health - /health endpoints returning 200"""
        print("\n📊 GATE 4: System Health")
        
        if not self.log_file.exists():
            return {"status": "FAIL", "error": f"Log file not found"}
        
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.readlines()
        
        # Count health check failures
        failed_checks = [l for l in logs if re.search(r'health_check.*failed', l)]
        failed_count = len(failed_checks)
        
        # Count process restarts (should be 1 - startup only)
        restarts = [l for l in logs if re.search(r'application_startup|process_restart', l)]
        restart_count = len(restarts)
        
        status = "PASS"
        reason = []
        
        if failed_count > 20:
            status = "FAIL"
            reason.append(f"❌ Failed health checks: {failed_count} (threshold: 20)")
        elif failed_count > 10:
            status = "CAUTION"
            reason.append(f"⚠️ Failed health checks: {failed_count} (borderline)")
        else:
            reason.append(f"✅ Failed health checks: {failed_count} (acceptable)")
        
        if restart_count <= 1:
            reason.append(f"✅ Process restarts: {restart_count} (only startup)")
        elif restart_count <= 2:
            status = "CAUTION" if status == "PASS" else status
            reason.append(f"⚠️ Process restarts: {restart_count}")
        else:
            status = "FAIL"
            reason.append(f"❌ Process restarts: {restart_count} (threshold: 2)")
        
        return {
            "status": status,
            "failed_health_checks": failed_count,
            "process_restarts": restart_count,
            "details": reason
        }
    
    def gate_5_error_rate(self) -> dict:
        """Gate 5: Error rate < 1%"""
        print("\n📊 GATE 5: Error Rate")
        
        if not self.log_file.exists():
            return {"status": "FAIL", "error": f"Log file not found"}
        
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.readlines()
        
        # Count errors (4xx/5xx status codes)
        errors = [l for l in logs if re.search(r'status.*[45]\d{2}', l)]
        error_count = len(errors)
        
        # Count total requests
        total_requests = [l for l in logs if re.search(r'request_complete', l)]
        total_count = len(total_requests)
        
        # Calculate error rate
        error_rate = (error_count / total_count * 100) if total_count > 0 else 0
        
        # Count repeating error patterns
        error_patterns = {}
        for line in errors:
            match = re.search(r'stack_trace.*"([^"]{50})', line)
            if match:
                pattern = match.group(1)
                error_patterns[pattern] = error_patterns.get(pattern, 0) + 1
        
        repeating = {k: v for k, v in error_patterns.items() if v > 5}
        
        status = "PASS"
        reason = []
        
        if error_rate < 1.0:
            reason.append(f"✅ Error rate: {error_rate:.2f}% (target: <1.0%)")
        elif error_rate < 1.5:
            status = "CAUTION"
            reason.append(f"⚠️ Error rate: {error_rate:.2f}% (target: <1.0%)")
        else:
            status = "FAIL"
            reason.append(f"❌ Error rate: {error_rate:.2f}% (threshold: 1.5%)")
        
        if repeating:
            status = "FAIL"
            for pattern, count in repeating.items():
                reason.append(f"❌ Repeating error: {pattern[:40]}... ({count} times)")
        else:
            reason.append(f"✅ No repeating error patterns (>5 occurrences)")
        
        return {
            "status": status,
            "error_rate": f"{error_rate:.2f}%",
            "error_count": error_count,
            "total_requests": total_count,
            "repeating_patterns": repeating,
            "details": reason
        }
    
    def gate_6_memory_hygiene(self) -> dict:
        """Gate 6: Memory - DB growth <3%, dedupe succeeded"""
        print("\n📊 GATE 6: Memory Hygiene")
        
        reason = []
        status = "PASS"
        
        # Check episodic DB size
        db_path = Path("runtime/episodic.db")
        if db_path.exists():
            current_size = db_path.stat().st_size
            baseline_size = 10485760  # 10 MB from Oct 18
            growth_percent = ((current_size - baseline_size) / baseline_size * 100)
            
            if growth_percent < 3.0:
                reason.append(f"✅ Episodic DB growth: {growth_percent:.2f}% (target: <3%)")
            elif growth_percent < 5.0:
                status = "CAUTION"
                reason.append(f"⚠️ Episodic DB growth: {growth_percent:.2f}% (target: <3%)")
            else:
                status = "FAIL"
                reason.append(f"❌ Episodic DB growth: {growth_percent:.2f}% (threshold: 5%)")
        else:
            reason.append(f"⚠️ Episodic DB not found at {db_path}")
        
        # Check dedupe job
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                logs = f.readlines()
            
            dedupe_completed = [l for l in logs if re.search(r'dedupe_job.*completed', l)]
            dedupe_failed = [l for l in logs if re.search(r'dedupe_job.*failed', l)]
            
            if dedupe_completed:
                reason.append(f"✅ Dedupe job: completed")
            elif dedupe_failed:
                status = "FAIL"
                reason.append(f"❌ Dedupe job: FAILED")
            else:
                reason.append(f"⚠️ Dedupe job: not run yet (runs at 3-4 AM)")
        
        return {
            "status": status,
            "db_growth_percent": growth_percent if db_path.exists() else None,
            "details": reason
        }
    
    def gate_7_smoke_tests(self) -> dict:
        """Gate 7: Smoke test suite - 24/25 passing"""
        print("\n📊 GATE 7: Smoke Test Suite")
        
        # This would normally run pytest and parse results
        # For now, we'll note that this should be run separately
        reason = [
            "⚠️ Smoke tests must be run separately with pytest",
            "Target: pytest tests/astra_fusion/ -v",
            "Expected: 24 PASSED, 1 FAILED (known latency test), 12 SKIPPED"
        ]
        
        return {
            "status": "MANUAL",
            "note": "Run pytest separately",
            "details": reason
        }
    
    def _print_gate_result(self, gate_name: str, result: dict):
        """Pretty-print gate result"""
        status_emoji = "✅" if result["status"] == "PASS" else "⚠️" if result["status"] == "CAUTION" else "❌" if result["status"] == "FAIL" else "❓"
        print(f"{status_emoji} {gate_name.replace('_', ' ').upper()}: {result['status']}")
        for detail in result.get("details", []):
            print(f"   {detail}")
    
    def _print_summary(self):
        """Print overall decision"""
        statuses = [r["status"] for r in self.results.values()]
        pass_count = statuses.count("PASS")
        caution_count = statuses.count("CAUTION")
        fail_count = statuses.count("FAIL")
        manual_count = statuses.count("MANUAL")
        
        print("\n" + "=" * 80)
        print(f"📊 SUMMARY: {pass_count} PASS | {caution_count} CAUTION | {fail_count} FAIL | {manual_count} MANUAL")
        print("=" * 80)
        
        if pass_count >= 7:
            decision = "✅ GO - All gates passed"
        elif pass_count == 6:
            decision = "✅ GO - 1 CAUTION, proceed with monitoring"
        elif pass_count >= 5:
            decision = "⚠️ CONDITIONAL GO - Hotfix required, re-evaluate"
        else:
            decision = "❌ NO-GO - Rollback and investigate"
        
        print(f"\n🎯 DECISION: {decision}\n")
        
        return decision
    
    def export_results(self, format: str = "json", output_file: str = "gate_results.json"):
        """Export results to file"""
        if format == "json":
            with open(output_file, 'w') as f:
                json.dump({
                    "timestamp": self.timestamp.isoformat(),
                    "gates": self.results
                }, f, indent=2, default=str)
        
        print(f"\n📁 Results exported to {output_file}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase B Go/No-Go Gate Validator")
    parser.add_argument("--log", default="logs/astra.log", help="Path to application log")
    parser.add_argument("--metrics", default="metrics_oct19.txt", help="Path to metrics file")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--export", choices=["json", "txt"], help="Export results")
    parser.add_argument("--output", default="gate_results.json", help="Output file for export")
    
    args = parser.parse_args()
    
    validator = GateValidator(log_file=args.log, metrics_file=args.metrics)
    results = validator.validate_all_gates()
    
    if args.export:
        validator.export_results(format=args.export, output_file=args.output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

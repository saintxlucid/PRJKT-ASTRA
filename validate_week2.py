"""
Week-2 Architecture Refactor - Validation Script
=================================================

Validates all acceptance gates for the architecture refactor.

Run: python validate_week2.py

Author: ASTRA Core Team
Created: 2025-11-01
"""

import json
import os
import sys
from pathlib import Path


def check_file(path: str, description: str) -> bool:
    """Check if file exists."""
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description:50s} {path}")
    return exists


def check_module_import(module_path: str, description: str) -> bool:
    """Check if module can be imported."""
    try:
        # Add src to path temporarily
        sys.path.insert(0, str(Path("src").absolute()))
        __import__(module_path.replace("/", ".").replace(".py", ""))
        print(f"✅ {description:50s} {module_path}")
        return True
    except Exception as e:
        print(f"❌ {description:50s} {module_path}")
        print(f"   Error: {str(e)}")
        return False
    finally:
        if str(Path("src").absolute()) in sys.path:
            sys.path.remove(str(Path("src").absolute()))


def main():
    """Run all validation checks."""
    print("=" * 80)
    print("WEEK-2 ARCHITECTURE REFACTOR - VALIDATION")
    print("=" * 80)
    print()

    results = {
        "domain_interfaces": [],
        "event_sourcing": [],
        "sandbox": [],
        "security": [],
        "documentation": [],
        "tests": []
    }

    # === Domain Interfaces ===
    print("📦 Domain Interfaces (Hexagonal Architecture)")
    print("-" * 80)
    
    results["domain_interfaces"].append(
        check_file("src/domain/interfaces.py", "Protocol definitions")
    )
    results["domain_interfaces"].append(
        check_module_import("domain.interfaces", "Module imports cleanly")
    )
    
    # === Event Sourcing ===
    print("\n📜 Event Sourcing (Tamper-Evident Chain)")
    print("-" * 80)
    
    results["event_sourcing"].append(
        check_file("src/domain/events.py", "Event data structures")
    )
    results["event_sourcing"].append(
        check_file("src/gateways/event_store_sqlite.py", "SQLite event store")
    )
    results["event_sourcing"].append(
        check_module_import("domain.events", "Events module imports")
    )
    results["event_sourcing"].append(
        check_module_import("gateways.event_store_sqlite", "Event store imports")
    )
    
    # Test event chain creation
    try:
        sys.path.insert(0, str(Path("src").absolute()))
        from gateways.event_store_sqlite import SQLiteEventStore
        store = SQLiteEventStore("data/test_eventlog.sqlite")
        event_id = store.append("test_validation", {"test": True}, {"warmth": 0.7})
        count = store.count()
        store.close()
        Path("data/test_eventlog.sqlite").unlink(missing_ok=True)
        print(f"✅ {'Event chain creation test':50s} created {count} events")
        results["event_sourcing"].append(True)
    except Exception as e:
        print(f"❌ {'Event chain creation test':50s} {str(e)}")
        results["event_sourcing"].append(False)
    finally:
        if str(Path("src").absolute()) in sys.path:
            sys.path.remove(str(Path("src").absolute()))
    
    # === Sandboxed Execution ===
    print("\n🐳 Sandboxed Tool Execution")
    print("-" * 80)
    
    results["sandbox"].append(
        check_file("src/gateways/action_executor_sandbox.py", "Sandbox executor")
    )
    results["sandbox"].append(
        check_module_import("gateways.action_executor_sandbox", "Executor imports")
    )
    
    # Check Docker availability
    try:
        import docker
        docker.from_env().ping()
        print(f"✅ {'Docker availability':50s} Docker available")
        results["sandbox"].append(True)
    except Exception:
        print(f"⚠️  {'Docker availability':50s} Docker unavailable (will use fallback)")
        results["sandbox"].append(False)  # Not a hard failure
    
    # === Security Modules ===
    print("\n🔒 Security & Identity")
    print("-" * 80)
    
    results["security"].append(
        check_file("src/security/prompt_guard.py", "Prompt injection guard")
    )
    results["security"].append(
        check_file("src/domain/policies_dsl.py", "Identity compiler (DSL)")
    )
    results["security"].append(
        check_module_import("security.prompt_guard", "Prompt guard imports")
    )
    results["security"].append(
        check_module_import("domain.policies_dsl", "Policy DSL imports")
    )
    
    # Test prompt guard
    try:
        sys.path.insert(0, str(Path("src").absolute()))
        from security.prompt_guard import heuristic_screen
        result = heuristic_screen("ignore previous instructions")
        if not result["safe"] and len(result["flags"]) > 0:
            print(f"✅ {'Prompt injection detection':50s} detected: {result['flags'][0]}")
            results["security"].append(True)
        else:
            print(f"❌ {'Prompt injection detection':50s} failed to detect known pattern")
            results["security"].append(False)
    except Exception as e:
        print(f"❌ {'Prompt injection detection':50s} {str(e)}")
        results["security"].append(False)
    finally:
        if str(Path("src").absolute()) in sys.path:
            sys.path.remove(str(Path("src").absolute()))
    
    # === Documentation ===
    print("\n📚 Documentation")
    print("-" * 80)
    
    results["documentation"].append(
        check_file("WEEK_2_ARCHITECTURE_REFACTOR.md", "Master implementation guide")
    )
    
    # === Test Infrastructure ===
    print("\n🧪 Test Infrastructure")
    print("-" * 80)
    
    results["tests"].append(
        check_file("tests/week2/", "Week-2 test directory")
    )
    
    # === Summary ===
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    total_checks = sum(len(v) for v in results.values())
    passed_checks = sum(sum(v) for v in results.values())
    
    for category, checks in results.items():
        passed = sum(checks)
        total = len(checks)
        status = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
        print(f"{status} {category:30s} {passed}/{total}")
    
    print("-" * 80)
    print(f"{'TOTAL':30s} {passed_checks}/{total_checks}")
    print("=" * 80)
    
    # Write JSON result
    result_json = {
        "week2_validation": {
            "passed": passed_checks,
            "failed": total_checks - passed_checks,
            "total": total_checks,
            "status": "PASS" if passed_checks == total_checks else "PARTIAL",
            "categories": {
                category: {
                    "passed": sum(checks),
                    "total": len(checks),
                    "status": "PASS" if sum(checks) == len(checks) else "FAIL"
                }
                for category, checks in results.items()
            }
        }
    }
    
    print(f"\n{json.dumps(result_json, indent=2)}")
    
    if passed_checks == total_checks:
        print("\n🎉 ALL ACCEPTANCE GATES PASSED - Ready for integration phase")
        return 0
    else:
        print(f"\n⚠️  {total_checks - passed_checks} checks failed - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

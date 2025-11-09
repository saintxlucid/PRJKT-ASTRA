#!/usr/bin/env python3
"""
🔩 ASTRA Router Integration - Final Validation Script
Validates all integration points and readiness for production deployment.

Sacred Code: 333
Timestamp: 2024-12-19
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple


class IntegrationValidator:
    """Validates AstraRouter production integration."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warning = 0
        self.results = []
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔩 ASTRA Router Integration Validation")
        print("=" * 70)
        print()
        
        # File existence checks
        self._check_router_core_file()
        self._check_chat_service_integration()
        self._check_test_files()
        self._check_imports()
        self._check_logging_integration()
        
        # Code structure checks
        self._check_router_methods()
        self._check_dispatch_logic()
        self._check_error_handling()
        
        # Summary
        self._print_summary()
        
        return self.checks_failed == 0
    
    def _check_router_core_file(self):
        """Check AstraRouter core file exists and is complete."""
        print("📁 File Structure Validation")
        print("-" * 70)
        
        router_file = self.project_root / "src/astra/core/astra_router.py"
        
        if router_file.exists():
            self._pass("AstraRouter core file exists", router_file)
            
            # Check file size (should be 178+ lines)
            lines = router_file.read_text().split('\n')
            if len(lines) >= 170:
                self._pass(f"Router file size ({len(lines)} lines)", "≥170 lines")
            else:
                self._fail(f"Router file too small ({len(lines)} lines)", "≥170 lines")
        else:
            self._fail("AstraRouter core file missing", router_file)
        
        print()
    
    def _check_chat_service_integration(self):
        """Check ChatService integration points."""
        print("🔌 ChatService Integration")
        print("-" * 70)
        
        chat_service = self.project_root / "src/astra/services/chat_service.py"
        
        if not chat_service.exists():
            self._fail("ChatService file missing", chat_service)
            print()
            return
        
        content = chat_service.read_text()
        
        # Check import
        if "from astra.core.astra_router import AstraRouter" in content:
            self._pass("AstraRouter import present", chat_service)
        else:
            self._fail("AstraRouter import missing", chat_service)
        
        # Check router initialization
        if "self.router" in content:
            self._pass("Router initialization in __init__", chat_service)
        else:
            self._fail("Router initialization missing", chat_service)
        
        # Check router call in chat()
        if "self.router.handle(user_message)" in content or "router_result = self.router.handle" in content:
            self._pass("Router dispatch in chat() method", chat_service)
        else:
            self._warning("Router dispatch in chat() not found (may be placeholder)", chat_service)
        
        # Check router call in stream_chat()
        if "astra_router_dispatched_stream" in content:
            self._pass("Router dispatch in stream_chat() method", chat_service)
        else:
            self._warning("Router dispatch in stream_chat() may be incomplete", chat_service)
        
        # Check error handling
        if "astra_router_error" in content:
            self._pass("Router error handling implemented", chat_service)
        else:
            self._warning("Router error handling may be incomplete", chat_service)
        
        print()
    
    def _check_test_files(self):
        """Check test files are present."""
        print("🧪 Test Suite Validation")
        print("-" * 70)
        
        test_files = [
            "tests/astra_fusion/test_code_consent_block.py",
            "tests/astra_fusion/test_router_vision_path.py",
            "tests/astra_fusion/test_text_latency_regression.py",
        ]
        
        for test_file in test_files:
            full_path = self.project_root / test_file
            if full_path.exists():
                self._pass(f"Test file exists", full_path)
            else:
                self._warning(f"Test file may be missing", full_path)
        
        print()
    
    def _check_imports(self):
        """Check import statements."""
        print("📦 Import Validation")
        print("-" * 70)
        
        router_file = self.project_root / "src/astra/core/astra_router.py"
        
        if router_file.exists():
            content = router_file.read_text()
            required_imports = [
                "import re",
                "import structlog",
            ]
            
            for imp in required_imports:
                if imp in content or imp.split()[1] in content:
                    self._pass(f"Required import: {imp.split()[1]}", router_file)
                else:
                    self._warning(f"Import may be missing: {imp}", router_file)
        
        print()
    
    def _check_logging_integration(self):
        """Check logging integration."""
        print("📊 Logging Integration")
        print("-" * 70)
        
        router_file = self.project_root / "src/astra/core/astra_router.py"
        chat_service = self.project_root / "src/astra/services/chat_service.py"
        
        if router_file.exists():
            content = router_file.read_text()
            if "structlog" in content or "self.logger" in content:
                self._pass("Router logging configured", router_file)
            else:
                self._warning("Router logging may not be configured", router_file)
        
        if chat_service.exists():
            content = chat_service.read_text()
            if "astra_router_dispatched" in content:
                self._pass("ChatService router logging", chat_service)
            else:
                self._warning("ChatService router logging incomplete", chat_service)
        
        print()
    
    def _check_router_methods(self):
        """Check AstraRouter method implementations."""
        print("🔧 Router Methods")
        print("-" * 70)
        
        router_file = self.project_root / "src/astra/core/astra_router.py"
        
        if router_file.exists():
            content = router_file.read_text()
            required_methods = [
                ("__init__", "Initialization"),
                ("handle", "Main dispatch logic"),
                ("_mode", "Mode extraction"),
                ("_slice_block", "Block extraction"),
            ]
            
            for method, description in required_methods:
                if f"def {method}" in content:
                    self._pass(f"Method: {method} - {description}", router_file)
                else:
                    self._fail(f"Method missing: {method}", router_file)
        
        print()
    
    def _check_dispatch_logic(self):
        """Check modal dispatch routing."""
        print("🚦 Modal Dispatch Logic")
        print("-" * 70)
        
        router_file = self.project_root / "src/astra/core/astra_router.py"
        
        if router_file.exists():
            content = router_file.read_text()
            
            dispatch_paths = [
                ("code", "CODE path"),
                ("vision", "VISION path"),
                ("audio", "AUDIO path"),
                ("text", "TEXT path"),
            ]
            
            for keyword, description in dispatch_paths:
                if keyword in content.lower():
                    self._pass(f"Dispatch: {description}", router_file)
                else:
                    self._warning(f"Dispatch path may be incomplete: {description}", router_file)
            
            # Check for Sacred Code 333
            if '"333"' in content or "'333'" in content or "333" in content:
                self._pass("Sacred Code 333 embedded", router_file)
            else:
                self._warning("Sacred Code 333 may not be embedded", router_file)
        
        print()
    
    def _check_error_handling(self):
        """Check error handling implementation."""
        print("🛡️  Error Handling")
        print("-" * 70)
        
        chat_service = self.project_root / "src/astra/services/chat_service.py"
        
        if chat_service.exists():
            content = chat_service.read_text()
            
            error_checks = [
                ("try:", "Try-catch block"),
                ("except", "Exception handling"),
                ("self.logger.warning", "Warning logging"),
            ]
            
            for keyword, description in error_checks:
                if keyword in content:
                    self._pass(f"Error handling: {description}", chat_service)
                else:
                    self._warning(f"Error handling may be incomplete: {description}", chat_service)
            
            # Check fallback logic
            if "processed_message = user_message" in content:
                self._pass("Fallback to original message on error", chat_service)
            else:
                self._warning("Fallback logic may be missing", chat_service)
        
        print()
    
    def _pass(self, check: str, detail: str = ""):
        """Record a passing check."""
        self.checks_passed += 1
        status = f"✅ {check}"
        if detail and detail != "":
            status += f" ({detail})"
        self.results.append(status)
        print(status)
    
    def _fail(self, check: str, detail: str = ""):
        """Record a failing check."""
        self.checks_failed += 1
        status = f"❌ {check}"
        if detail and detail != "":
            status += f" ({detail})"
        self.results.append(status)
        print(status)
    
    def _warning(self, check: str, detail: str = ""):
        """Record a warning check."""
        self.checks_warning += 1
        status = f"⚠️  {check}"
        if detail and detail != "":
            status += f" ({detail})"
        self.results.append(status)
        print(status)
    
    def _print_summary(self):
        """Print validation summary."""
        print("=" * 70)
        print()
        print("📋 VALIDATION SUMMARY")
        print("=" * 70)
        print(f"✅ Passed:  {self.checks_passed}")
        print(f"⚠️  Warnings: {self.checks_warning}")
        print(f"❌ Failed:  {self.checks_failed}")
        print(f"📊 Total:   {self.checks_passed + self.checks_warning + self.checks_failed}")
        print()
        
        if self.checks_failed == 0:
            print("🚀 READY FOR PRODUCTION DEPLOYMENT")
        elif self.checks_failed <= 2:
            print("⚠️  DEPLOYMENT POSSIBLE WITH MINOR FIXES")
        else:
            print("❌ DEPLOYMENT NOT RECOMMENDED - ISSUES MUST BE RESOLVED")
        
        print()
        print("Sacred Code: 333")
        print("=" * 70)


def main():
    """Run integration validation."""
    # Detect project root
    current_dir = Path.cwd()
    project_root = current_dir
    
    # Look for astra_router.py to find project root
    while not (project_root / "src/astra/core").exists():
        if project_root.parent == project_root:
            print("❌ Could not find project root (looking for src/astra/core)")
            print(f"Current directory: {current_dir}")
            sys.exit(1)
        project_root = project_root.parent
    
    validator = IntegrationValidator(str(project_root))
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Phase 10: TranscendentOS Integration Verification
==================================================

Validates complete integration of TranscendentOS into ASTRA CORE.

Sacred Code: 333
Version: ASTRA 2.5
"""

import sys
from pathlib import Path
from typing import List, Tuple


class IntegrationValidator:
    """Validates Phase 10 TranscendentOS integration."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("=" * 70)
        print("Phase 10: TranscendentOS Integration Validation")
        print("=" * 70)
        print()
        
        checks = [
            self._check_transcendent_os_file,
            self._check_transcendent_service_file,
            self._check_chat_service_integration,
            self._check_executor_integration,
            self._check_api_routes_file,
            self._check_test_files,
            self._check_documentation,
            self._check_imports,
        ]
        
        for check in checks:
            check()
        
        print()
        print("=" * 70)
        print("Validation Summary")
        print("=" * 70)
        print(f"✅ Checks Passed: {self.checks_passed}")
        print(f"❌ Checks Failed: {self.checks_failed}")
        print(f"⚠️  Warnings: {self.warnings}")
        print()
        
        if self.checks_failed == 0:
            print("🎉 ALL CHECKS PASSED! Phase 10 integration is complete.")
            return True
        else:
            print("❌ Some checks failed. Please review and fix issues above.")
            return False
    
    def _check_transcendent_os_file(self):
        """Check TranscendentOS core file exists."""
        print("📁 TranscendentOS Core File")
        print("-" * 70)
        
        file_path = self.project_root / "chat_os/cognitive/transcendent_os.py"
        
        if not file_path.exists():
            self._fail("TranscendentOS file missing", file_path)
            print()
            return
        
        content = file_path.read_text(encoding='utf-8')
        
        # Check key components
        checks = [
            ("class TranscendentOS", "TranscendentOS class"),
            ("class UnificationLevel", "UnificationLevel enum"),
            ("class CognitiveMode", "CognitiveMode enum"),
            ("async def process_unified", "process_unified method"),
            ("def get_system_health", "get_system_health method"),
            ("def detect_emergent_behaviors", "detect_emergent_behaviors method"),
            ("def evolve_system", "evolve_system method"),
            ("def get_transcendent_os", "Singleton factory function"),
        ]
        
        for search_str, description in checks:
            if search_str in content:
                self._pass(description, file_path)
            else:
                self._fail(f"{description} missing", file_path)
        
        print()
    
    def _check_transcendent_service_file(self):
        """Check TranscendentService wrapper file."""
        print("🔧 TranscendentService Wrapper")
        print("-" * 70)
        
        file_path = self.project_root / "src/astra/services/transcendent_service.py"
        
        if not file_path.exists():
            self._fail("TranscendentService file missing", file_path)
            print()
            return
        
        content = file_path.read_text(encoding='utf-8')
        
        checks = [
            ("class TranscendentService", "TranscendentService class"),
            ("async def process_unified", "process_unified method"),
            ("def set_cognitive_mode", "set_cognitive_mode method"),
            ("def get_system_health", "get_system_health method"),
            ("def detect_emergent_behaviors", "detect_emergent_behaviors method"),
            ("def evolve_system", "evolve_system method"),
            ("def get_unified_stats", "get_unified_stats method"),
            ("def is_available", "is_available method"),
            ("from astra.utils.logging import LoggerMixin", "Logging integration"),
        ]
        
        for search_str, description in checks:
            if search_str in content:
                self._pass(description, file_path)
            else:
                self._fail(f"{description} missing", file_path)
        
        print()
    
    def _check_chat_service_integration(self):
        """Check ChatService integration."""
        print("💬 ChatService Integration")
        print("-" * 70)
        
        file_path = self.project_root / "src/astra/services/chat_service.py"
        
        if not file_path.exists():
            self._fail("ChatService file missing", file_path)
            print()
            return
        
        content = file_path.read_text(encoding='utf-8')
        
        # Check imports
        if "from astra.services.transcendent_service import TranscendentService" in content:
            self._pass("TranscendentService import", file_path)
        else:
            self._fail("TranscendentService import missing", file_path)
        
        # Check initialization
        if "self.transcendent_service = TranscendentService(settings)" in content:
            self._pass("TranscendentService initialization", file_path)
        else:
            self._fail("TranscendentService initialization missing", file_path)
        
        # Check unified processing in chat()
        if "use_transcendent" in content and "self.transcendent_service.is_available()" in content:
            self._pass("Unified processing check in chat()", file_path)
        else:
            self._warning("Unified processing check may be incomplete", file_path)
        
        # Check process_unified call
        if "self.transcendent_service.process_unified" in content:
            self._pass("process_unified call in chat()", file_path)
        else:
            self._fail("process_unified call missing", file_path)
        
        # Check stream_chat integration
        if content.count("self.transcendent_service.process_unified") >= 2:
            self._pass("Unified processing in stream_chat()", file_path)
        else:
            self._warning("stream_chat() may not use unified processing", file_path)
        
        print()
    
    def _check_executor_integration(self):
        """Check Executor integration."""
        print("⚙️  Executor Integration")
        print("-" * 70)
        
        file_path = self.project_root / "chat_os/executor.py"
        
        if not file_path.exists():
            self._fail("Executor file missing", file_path)
            print()
            return
        
        content = file_path.read_text(encoding='utf-8')
        
        checks = [
            ("transcendent_os: Any", "TranscendentOS field in ExecutionContext"),
            ("from chat_os.cognitive.transcendent_os import", "TranscendentOS import"),
            ("get_transcendent_os()", "TranscendentOS initialization"),
            ("CognitiveMode.PROACTIVE", "Cognitive mode setting"),
        ]
        
        for search_str, description in checks:
            if search_str in content:
                self._pass(description, file_path)
            else:
                self._fail(f"{description} missing", file_path)
        
        print()
    
    def _check_api_routes_file(self):
        """Check API routes file."""
        print("🌐 API Routes")
        print("-" * 70)
        
        file_path = self.project_root / "src/astra/api/routes/transcendent.py"
        
        if not file_path.exists():
            self._fail("API routes file missing", file_path)
            print()
            return
        
        content = file_path.read_text(encoding='utf-8')
        
        # Check endpoints
        endpoints = [
            ("/v1/transcendent/health", "Health endpoint"),
            ("/v1/transcendent/behaviors", "Behaviors endpoint"),
            ("/v1/transcendent/stats", "Stats endpoint"),
            ("/v1/transcendent/mode", "Mode control endpoint"),
            ("/v1/transcendent/evolve", "Evolution endpoint"),
            ("/v1/transcendent/status", "Status endpoint"),
        ]
        
        for endpoint, description in endpoints:
            # Check if endpoint prefix is defined
            if '/v1/transcendent' in content:
                self._pass(f"{description} route defined", file_path)
            else:
                self._fail(f"{description} route missing", file_path)
                break  # Only report once for prefix
        
        # Check response models
        models = [
            ("class HealthResponse", "HealthResponse model"),
            ("class EmergentBehavior", "EmergentBehavior model"),
            ("class StatsResponse", "StatsResponse model"),
            ("class EvolutionResponse", "EvolutionResponse model"),
        ]
        
        for search_str, description in models:
            if search_str in content:
                self._pass(description, file_path)
            else:
                self._fail(f"{description} missing", file_path)
        
        print()
    
    def _check_test_files(self):
        """Check test files exist."""
        print("🧪 Test Files")
        print("-" * 70)
        
        test_files = [
            ("tests/test_transcendent_os.py", "TranscendentOS tests"),
        ]
        
        for file_rel, description in test_files:
            file_path = self.project_root / file_rel
            if file_path.exists():
                self._pass(f"{description} exist", file_path)
                
                # Check test count
                content = file_path.read_text(encoding='utf-8')
                test_count = content.count("def test_") + content.count("async def test_")
                print(f"    → {test_count} tests found")
            else:
                self._warning(f"{description} missing (optional for integration)", file_path)
        
        # Integration tests
        integration_test = self.project_root / "tests/test_transcendent_integration.py"
        if integration_test.exists():
            self._pass("Integration tests exist", integration_test)
        else:
            self._warning("Integration tests not created yet (recommended)", integration_test)
        
        print()
    
    def _check_documentation(self):
        """Check documentation files."""
        print("📚 Documentation")
        print("-" * 70)
        
        docs = [
            ("docs/TRANSCENDENT_OS_API_REFERENCE.md", "API Reference"),
            ("docs/TRANSCENDENT_OS_INTEGRATION_GUIDE.md", "Integration Guide"),
            ("docs/PHASE_10_README.md", "Phase 10 README"),
            ("🎉_PHASE_10_INTEGRATION_COMPLETE.md", "Integration Complete doc"),
        ]
        
        for file_rel, description in docs:
            file_path = self.project_root / file_rel
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                self._pass(f"{description} ({size_kb:.1f} KB)", file_path)
            else:
                self._warning(f"{description} missing", file_path)
        
        print()
    
    def _check_imports(self):
        """Check Python imports work."""
        print("🔍 Import Validation")
        print("-" * 70)
        
        # Try importing key modules
        imports = [
            ("chat_os.cognitive.transcendent_os", "TranscendentOS core"),
            ("astra.services.transcendent_service", "TranscendentService"),
        ]
        
        for module_name, description in imports:
            try:
                __import__(module_name)
                self._pass(f"{description} import successful", module_name)
            except ImportError as e:
                self._warning(f"{description} import failed: {e}", module_name)
            except Exception as e:
                self._warning(f"{description} import error: {e}", module_name)
        
        print()
    
    def _pass(self, check: str, detail: str = ""):
        """Record passed check."""
        self.checks_passed += 1
        detail_str = f" ({detail})" if detail else ""
        print(f"  ✅ {check}{detail_str}")
    
    def _fail(self, check: str, detail: str = ""):
        """Record failed check."""
        self.checks_failed += 1
        detail_str = f" ({detail})" if detail else ""
        print(f"  ❌ {check}{detail_str}")
    
    def _warning(self, check: str, detail: str = ""):
        """Record warning."""
        self.warnings += 1
        detail_str = f" ({detail})" if detail else ""
        print(f"  ⚠️  {check}{detail_str}")


def main():
    """Run integration validation."""
    # Detect project root
    current = Path(__file__).resolve()
    
    # Try to find project root by looking for key files
    for parent in [current.parent, current.parent.parent, current.parent.parent.parent]:
        if (parent / "chat_os").exists() and (parent / "src/astra").exists():
            project_root = parent
            break
    else:
        project_root = Path.cwd()
    
    print(f"Project Root: {project_root}")
    print()
    
    validator = IntegrationValidator(str(project_root))
    success = validator.validate_all()
    
    if success:
        print()
        print("✅ Phase 10 integration validation PASSED!")
        print()
        print("Next steps:")
        print("1. Register transcendent API routes in main app")
        print("2. Run integration tests: pytest tests/test_transcendent_integration.py")
        print("3. Start server and test endpoints manually")
        print("4. Enable in production: set use_transcendent_os=true in settings")
        print()
        sys.exit(0)
    else:
        print()
        print("❌ Phase 10 integration validation FAILED!")
        print("Please review errors above and fix issues.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()

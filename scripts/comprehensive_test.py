"""
Comprehensive Testing and Debugging Script

This script performs thorough testing of all ASTRA components:
- Virtual environment and dependencies
- Model information access
- Harmony format utilities
- Configuration loading
- Database connectivity
- Vector store setup
- Import validation

Usage:
    python scripts/comprehensive_test.py
"""

import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

# Test results tracking
test_results: List[Tuple[str, bool, str]] = []


def log_test(test_name: str, passed: bool, details: str = ""):
    """Log a test result."""
    test_results.append((test_name, passed, details))
    status = "✓" if passed else "✗"
    print(f"   [{status}] {test_name}")
    if details and not passed:
        print(f"       Details: {details}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"   {title}")
    print('='*80)


def test_virtual_environment():
    """Test virtual environment setup."""
    print_section("1. Virtual Environment Tests")
    
    # Test Python version
    try:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        log_test("Python version", True, f"Python {version}")
    except Exception as e:
        log_test("Python version", False, str(e))
    
    # Test Python path
    try:
        python_path = sys.executable
        in_venv = ".venv" in python_path
        log_test("Python in .venv", in_venv, python_path)
    except Exception as e:
        log_test("Python in .venv", False, str(e))
    
    # Test sys.path
    try:
        has_src = any("src" in p for p in sys.path)
        log_test("Project src in sys.path", has_src, f"Found {len(sys.path)} paths")
    except Exception as e:
        log_test("Project src in sys.path", False, str(e))


def test_core_imports():
    """Test importing core dependencies."""
    print_section("2. Core Dependency Import Tests")
    
    core_packages = {
        "fastapi": "FastAPI",
        "pydantic": "Pydantic",
        "sqlalchemy": "SQLAlchemy",
        "chromadb": "ChromaDB",
        "sentence_transformers": "SentenceTransformers",
        "structlog": "Structlog",
        "httpx": "HTTPX",
        "tenacity": "Tenacity",
        "uvicorn": "Uvicorn",
    }
    
    for package, name in core_packages.items():
        try:
            __import__(package.replace("-", "_"))
            log_test(f"Import {name}", True)
        except ImportError as e:
            log_test(f"Import {name}", False, str(e))


def test_ml_imports():
    """Test importing ML/AI packages."""
    print_section("3. ML/AI Package Import Tests")
    
    ml_packages = {
        "torch": "PyTorch",
        "transformers": "Transformers",
        "openai": "OpenAI SDK",
        "numpy": "NumPy",
        "scipy": "SciPy",
    }
    
    for package, name in ml_packages.items():
        try:
            __import__(package)
            log_test(f"Import {name}", True)
        except ImportError as e:
            log_test(f"Import {name}", False, str(e))


def test_model_info():
    """Test model information access."""
    print_section("4. Model Information Access Tests")
    
    try:
        from src.astra.models.model_info import (
            get_model_info,
            list_available_models,
            GPT_OSS_120B_INFO,
            GPT_OSS_20B_INFO,
            MODEL_REGISTRY
        )
        log_test("Import model_info module", True)
        
        # Test list_available_models
        try:
            models = list_available_models()
            has_both = len(models) == 2 and "gpt-oss-20b" in models and "gpt-oss-120b" in models
            log_test("List available models", has_both, f"Found: {models}")
        except Exception as e:
            log_test("List available models", False, str(e))
        
        # Test get_model_info
        try:
            model = get_model_info("gpt-oss-20b")
            valid = model is not None and model.display_name == "GPT-OSS-20B"
            log_test("Get model info (gpt-oss-20b)", valid)
        except Exception as e:
            log_test("Get model info (gpt-oss-20b)", False, str(e))
        
        # Test direct access
        try:
            model = GPT_OSS_20B_INFO
            valid = (
                model.architecture.total_parameters == 20_900_000_000 and
                model.architecture.layers == 24 and
                model.architecture.num_experts == 32
            )
            log_test("Direct access GPT_OSS_20B_INFO", valid)
        except Exception as e:
            log_test("Direct access GPT_OSS_20B_INFO", False, str(e))
        
        # Test reasoning modes
        try:
            model = GPT_OSS_20B_INFO
            has_modes = len(model.reasoning_modes) == 3
            modes = [m.mode for m in model.reasoning_modes]
            correct_modes = "low" in modes and "medium" in modes and "high" in modes
            log_test("Reasoning modes configured", has_modes and correct_modes, f"Modes: {modes}")
        except Exception as e:
            log_test("Reasoning modes configured", False, str(e))
        
        # Test benchmarks
        try:
            model = GPT_OSS_20B_INFO
            has_benchmarks = len(model.benchmarks) > 0
            log_test("Performance benchmarks loaded", has_benchmarks, f"Count: {len(model.benchmarks)}")
        except Exception as e:
            log_test("Performance benchmarks loaded", False, str(e))
        
        # Test harmony format
        try:
            model = GPT_OSS_20B_INFO
            harmony = model.harmony_format
            has_roles = len(harmony.role_hierarchy) == 5
            has_channels = len(harmony.channels) == 3
            log_test("Harmony format configured", has_roles and has_channels)
        except Exception as e:
            log_test("Harmony format configured", False, str(e))
        
        # Test tool capabilities
        try:
            model = GPT_OSS_20B_INFO
            has_tools = len(model.tool_capabilities) == 3
            log_test("Tool capabilities loaded", has_tools, f"Count: {len(model.tool_capabilities)}")
        except Exception as e:
            log_test("Tool capabilities loaded", False, str(e))
            
    except ImportError as e:
        log_test("Import model_info module", False, str(e))


def test_harmony_format():
    """Test Harmony format utilities."""
    print_section("5. Harmony Format Utilities Tests")
    
    try:
        from src.astra.infrastructure.llm.harmony import (
            HarmonyPromptBuilder,
            HarmonyMessage,
            HarmonyRole,
            HarmonyChannel,
            strip_cot_from_history,
            parse_harmony_response,
            extract_final_response,
            convert_to_openai_format
        )
        log_test("Import harmony module", True)
        
        # Test HarmonyPromptBuilder
        try:
            builder = HarmonyPromptBuilder()
            builder.add_system_message("Test system message")
            builder.add_user_message("Test user message")
            prompt = builder.build()
            valid = len(prompt) > 0 and "<|start_header_id|>" in prompt
            log_test("HarmonyPromptBuilder.build()", valid)
        except Exception as e:
            log_test("HarmonyPromptBuilder.build()", False, str(e))
        
        # Test HarmonyMessage creation
        try:
            msg = HarmonyMessage(
                role=HarmonyRole.USER,
                content="Test content",
                channel=HarmonyChannel.FINAL
            )
            valid = msg.role == HarmonyRole.USER and msg.content == "Test content"
            log_test("HarmonyMessage creation", valid)
        except Exception as e:
            log_test("HarmonyMessage creation", False, str(e))
        
        # Test parse_harmony_response
        try:
            response = "<|start_header_id|>assistant|final<|end_header_id|>\n\nTest response"
            messages = parse_harmony_response(response)
            valid = len(messages) > 0
            log_test("parse_harmony_response()", valid, f"Parsed {len(messages)} messages")
        except Exception as e:
            log_test("parse_harmony_response()", False, str(e))
        
        # Test strip_cot_from_history
        try:
            messages = [
                HarmonyMessage(role=HarmonyRole.USER, content="Q", channel=HarmonyChannel.FINAL),
                HarmonyMessage(role=HarmonyRole.ASSISTANT, content="Analysis", channel=HarmonyChannel.ANALYSIS),
                HarmonyMessage(role=HarmonyRole.ASSISTANT, content="Answer", channel=HarmonyChannel.FINAL),
            ]
            stripped = strip_cot_from_history(messages)
            valid = len(stripped) == 2  # Should remove analysis channel
            log_test("strip_cot_from_history()", valid, f"Reduced from {len(messages)} to {len(stripped)}")
        except Exception as e:
            log_test("strip_cot_from_history()", False, str(e))
        
        # Test convert_to_openai_format
        try:
            messages = [
                HarmonyMessage(role=HarmonyRole.SYSTEM, content="System", channel=HarmonyChannel.FINAL),
                HarmonyMessage(role=HarmonyRole.USER, content="User", channel=HarmonyChannel.FINAL),
            ]
            openai_msgs = convert_to_openai_format(messages, include_cot=False)
            valid = len(openai_msgs) == 2 and openai_msgs[0]["role"] == "system"
            log_test("convert_to_openai_format()", valid)
        except Exception as e:
            log_test("convert_to_openai_format()", False, str(e))
            
    except ImportError as e:
        log_test("Import harmony module", False, str(e))


def test_configuration():
    """Test configuration loading."""
    print_section("6. Configuration Loading Tests")
    
    # Test .env file exists
    try:
        env_path = project_root / ".env"
        exists = env_path.exists()
        log_test(".env file exists", exists, str(env_path))
    except Exception as e:
        log_test(".env file exists", False, str(e))
    
    # Test config module import
    try:
        from src.astra.models.config import get_settings, LLMConfig
        log_test("Import config module", True)
        
        # Test get_settings
        try:
            settings = get_settings()
            log_test("Load settings", True, f"Environment: {getattr(settings, 'environment', 'unknown')}")
        except Exception as e:
            log_test("Load settings", False, str(e))
            
    except ImportError as e:
        log_test("Import config module", False, str(e))
    
    # Test default.yaml exists
    try:
        yaml_path = project_root / "config" / "default.yaml"
        exists = yaml_path.exists()
        log_test("default.yaml exists", exists, str(yaml_path))
    except Exception as e:
        log_test("default.yaml exists", False, str(e))


def test_database():
    """Test database setup."""
    print_section("7. Database Tests")
    
    # Test database directory
    try:
        db_dir = project_root / "data" / "database"
        exists = db_dir.exists()
        log_test("Database directory exists", exists, str(db_dir))
    except Exception as e:
        log_test("Database directory exists", False, str(e))
    
    # Test SQLAlchemy models import
    try:
        from src.astra.infrastructure.storage.database import Base, Conversation, Message
        log_test("Import database models", True)
    except ImportError as e:
        log_test("Import database models", False, str(e))
    
    # Test database connection
    try:
        from sqlalchemy import create_engine, text
        from src.astra.models.config import get_settings
        
        settings = get_settings()
        # Use a test database path
        test_db_url = f"sqlite:///{project_root}/data/database/test_connection.db"
        engine = create_engine(test_db_url, echo=False)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            valid = result.fetchone()[0] == 1
            log_test("Database connection", valid)
        
        # Properly dispose of engine before cleanup
        engine.dispose()
        
        # Clean up test database
        import os
        import time
        test_db_path = project_root / "data" / "database" / "test_connection.db"
        
        # Give time for file handles to close
        time.sleep(0.5)
        
        if test_db_path.exists():
            try:
                os.remove(test_db_path)
            except PermissionError:
                # File is still locked, but test passed
                pass
            
    except Exception as e:
        log_test("Database connection", False, str(e))


def test_vector_store():
    """Test vector store setup."""
    print_section("8. Vector Store Tests")
    
    # Test ChromaDB directory
    try:
        chroma_dir = project_root / "data" / "chromadb"
        exists = chroma_dir.exists()
        log_test("ChromaDB directory exists", exists, str(chroma_dir))
    except Exception as e:
        log_test("ChromaDB directory exists", False, str(e))
    
    # Test ChromaDB client creation
    try:
        import chromadb
        import shutil
        import time
        
        chroma_path = str(project_root / "data" / "chromadb" / "test_collection")
        
        # Clean up before test if exists
        if Path(chroma_path).exists():
            try:
                shutil.rmtree(chroma_path)
            except (PermissionError, OSError):
                pass  # Previous test artifacts, ignore
        
        # Create client and test
        client = chromadb.PersistentClient(path=chroma_path)
        log_test("ChromaDB client creation", True)
        
        # Clean up test collection after client is done
        del client  # Release the client
        import gc
        gc.collect()  # Force garbage collection to close file handles
        
        time.sleep(0.5)  # Give time for file handles to close
        
        if Path(chroma_path).exists():
            try:
                shutil.rmtree(chroma_path)
            except (PermissionError, OSError):
                # File still locked, but test passed
                pass
            
    except Exception as e:
        log_test("ChromaDB client creation", False, str(e))


def test_file_structure():
    """Test project file structure."""
    print_section("9. File Structure Tests")
    
    critical_files = [
        ".env",
        "pyproject.toml",
        "config/default.yaml",
        "src/astra/models/model_info.py",
        "src/astra/models/config.py",
        "src/astra/infrastructure/llm/harmony.py",
        "docs/models/gpt_oss_model_card.md",
        "scripts/activate_astra.ps1",
        "scripts/test_model_info.py",
    ]
    
    for file_path in critical_files:
        try:
            full_path = project_root / file_path
            exists = full_path.exists()
            log_test(f"File: {file_path}", exists)
        except Exception as e:
            log_test(f"File: {file_path}", False, str(e))


def generate_report():
    """Generate final test report."""
    print_section("Test Summary")
    
    total = len(test_results)
    passed = sum(1 for _, success, _ in test_results if success)
    failed = total - passed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n   Total Tests: {total}")
    print(f"   Passed: {passed} ({success_rate:.1f}%)")
    print(f"   Failed: {failed}")
    print()
    
    if failed > 0:
        print("   Failed Tests:")
        for name, success, details in test_results:
            if not success:
                print(f"      ✗ {name}")
                if details:
                    print(f"        {details}")
        print()
    
    # Save report to file
    report_path = project_root / "TEST_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ASTRA Comprehensive Test Report\n\n")
        f.write(f"**Date**: {Path(__file__).stat().st_mtime}\n")
        f.write(f"**Total Tests**: {total}\n")
        f.write(f"**Passed**: {passed} ({success_rate:.1f}%)\n")
        f.write(f"**Failed**: {failed}\n\n")
        
        f.write("## Test Results\n\n")
        for name, success, details in test_results:
            status = "✓" if success else "✗"
            f.write(f"- [{status}] {name}\n")
            if details and not success:
                f.write(f"  - Details: {details}\n")
        
        f.write("\n## Recommendations\n\n")
        if failed == 0:
            f.write("All tests passed! System is ready for use.\n")
        else:
            f.write("Please address the failed tests before proceeding.\n")
    
    print(f"   Report saved to: {report_path}")
    print()
    
    return failed == 0


def main():
    """Run all tests."""
    print("="*80)
    print("   ASTRA Comprehensive Testing & Debugging")
    print("="*80)
    
    try:
        test_virtual_environment()
        test_core_imports()
        test_ml_imports()
        test_model_info()
        test_harmony_format()
        test_configuration()
        test_database()
        test_vector_store()
        test_file_structure()
        
        success = generate_report()
        
        if success:
            print("="*80)
            print("   ✓ ALL TESTS PASSED!")
            print("="*80)
            return 0
        else:
            print("="*80)
            print("   ✗ Some tests failed. Check report for details.")
            print("="*80)
            return 1
            
    except Exception as e:
        print(f"\n   ✗ Fatal error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

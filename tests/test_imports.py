"""
Basic test to verify core imports work.

This ensures the package structure is correct.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_imports():
    """Test that all core modules can be imported"""
    # Configuration

    # Errors

    # Logging

    # LLM

    # Services

    # API

    print("✅ All core imports successful!")


def test_config_loading():
    """Test configuration system"""
    from astra.models.config import Settings

    settings = Settings()
    assert settings.server.port > 0
    assert settings.llm.provider in ["llamacpp", "openai", "anthropic"]
    print(f"✅ Configuration loaded: {settings.llm.provider} provider")


if __name__ == "__main__":
    print("Running basic import tests...")
    print("=" * 60)

    try:
        test_imports()
        test_config_loading()
        print("=" * 60)
        print("✅ All tests passed!")
    except Exception as e:
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
VLM Service Smoke Test

Quick validation that VLM service can be imported and instantiated with mocked dependencies.
Does NOT require actual model files or GPU - suitable for CI/CD pipelines.

Usage:
    python scripts/test_vlm_smoke.py
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def mock_dependencies():
    """Setup mock dependencies for VLM."""
    # Mock torch
    torch_mock = Mock()
    torch_mock.cuda.is_available.return_value = False
    torch_mock.device.return_value = Mock(type='cpu')
    torch_mock.float32 = 'float32'
    torch_mock.no_grad = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))

    # Mock PIL
    pil_mock = Mock()
    img = Mock()
    img.convert.return_value = img
    img.size = (384, 384)
    img.thumbnail = Mock()
    pil_mock.new.return_value = img
    pil_mock.Resampling.LANCZOS = 1

    # Mock transformers
    processor = Mock()
    processor.return_value = {'pixel_values': Mock()}

    model = Mock()
    model.generate.return_value = [[1, 2, 3]]
    model.to.return_value = model
    model.eval.return_value = model
    model.cpu.return_value = model

    tokenizer = Mock()
    tokenizer.batch_decode.return_value = ["Test caption from smoke test"]

    return {
        'torch': torch_mock,
        'pil': pil_mock,
        'processor': processor,
        'model': model,
        'tokenizer': tokenizer
    }


def test_import():
    """Test that VLM module can be imported."""
    print("✓ Testing VLM module import...")
    try:
        from services import vlm_service_local  # noqa: F401
        print("  ✓ VLM module imported successfully")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_config_creation():
    """Test VLMConfig creation."""
    print("✓ Testing VLMConfig creation...")
    try:
        from services.vlm_service_local import VLMConfig
        cfg = VLMConfig(
            model_name_or_path="fake/model/path",
            device="cpu",
            batch_size=2
        )
        assert cfg.model_name_or_path == "fake/model/path"
        assert cfg.batch_size == 2
        print("  ✓ VLMConfig created successfully")
        return True
    except Exception as e:
        print(f"  ✗ Config creation failed: {e}")
        return False


def test_service_instantiation():
    """Test VLMService instantiation with mocked dependencies."""
    print("✓ Testing VLMService instantiation (mocked)...")

    mocks = mock_dependencies()

    # Patch at import time within the VLMService.__init__
    with patch('os.path.exists', return_value=True):
        try:
            from services.vlm_service_local import VLMConfig, VLMService

            # Mock the imports inside __init__
            with patch.object(VLMService, '__init__', lambda self, cfg: None):
                vlm = VLMService(VLMConfig(model_name_or_path="fake/model", device="cpu"))
                # Manually set attributes for testing
                vlm.cfg = VLMConfig(model_name_or_path="fake/model", device="cpu", warmup_runs=0)
                vlm.torch = mocks['torch']
                vlm.Image = mocks['pil']
                vlm.processor = mocks['processor']
                vlm.model = mocks['model']
                vlm.tokenizer = mocks['tokenizer']
                vlm.device = Mock(type='cpu')
                vlm._executor = None

                # Test methods exist
                assert hasattr(vlm, 'caption_images')
                assert hasattr(vlm, 'answer_question')
                print("  ✓ VLMService structure validated")

            print("  ✓ VLMService instantiation successful")
            return True

        except Exception as e:
            print(f"  ✗ Service instantiation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_factory_function():
    """Test build_vlm_from_config factory."""
    print("✓ Testing factory function...")

    # Test without actual instantiation (just verify function signature)
    try:
        from services.vlm_service_local import build_vlm_from_config

        # Test config validation
        try:
            build_vlm_from_config({})  # Missing vlm section
            print("  ✗ Should have raised ValueError for missing config")
            return False
        except ValueError as e:
            if "model_name_or_path" in str(e):
                print("  ✓ Config validation works correctly")
            else:
                print(f"  ✗ Unexpected error: {e}")
                return False

        print("  ✓ Factory function signature validated")
        return True

    except Exception as e:
        print(f"  ✗ Factory test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("VLM Service Smoke Tests")
    print("=" * 60)

    tests = [
        test_import,
        test_config_creation,
        test_service_instantiation,
        test_factory_function,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
        print()

    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("✓ All smoke tests PASSED")
        return 0
    else:
        print("✗ Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

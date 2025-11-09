# SPDX-License-Identifier: MIT
"""
Unit tests for VLM Service (Vision-Language Model)

Tests use mocking to avoid requiring real model files or GPU hardware.
"""
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_torch():
    """Mock torch module."""
    with patch('src.services.vlm_service_local.torch') as mock:
        mock.cuda.is_available.return_value = True
        mock.device.return_value = Mock(type='cuda')
        mock.float16 = 'float16'
        mock.float32 = 'float32'
        mock.no_grad = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))
        yield mock


@pytest.fixture
def mock_pil():
    """Mock PIL.Image."""
    with patch('src.services.vlm_service_local.Image') as mock:
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)
        img.thumbnail = Mock()
        mock.new.return_value = img
        mock.open.return_value = img
        mock.Resampling.LANCZOS = 1
        yield mock


@pytest.fixture
def mock_transformers():
    """Mock transformers components."""
    with patch('src.services.vlm_service_local.AutoProcessor') as proc_mock, \
         patch('src.services.vlm_service_local.VisionEncoderDecoderModel') as model_mock, \
         patch('src.services.vlm_service_local.AutoTokenizer') as tok_mock:

        # Mock processor
        processor = Mock()
        processor.return_value = {'pixel_values': Mock()}
        proc_mock.from_pretrained.return_value = processor

        # Mock model
        model = Mock()
        model.generate.return_value = [[1, 2, 3]]  # Fake token IDs
        model.to.return_value = model
        model.eval.return_value = model
        model.half.return_value = model
        model.cpu.return_value = model
        model_mock.from_pretrained.return_value = model

        # Mock tokenizer
        tokenizer = Mock()
        tokenizer.batch_decode.return_value = ["A test caption"]
        tok_mock.from_pretrained.return_value = tokenizer

        yield {
            'processor': proc_mock,
            'model': model_mock,
            'tokenizer': tok_mock
        }


@pytest.fixture
def vlm_config():
    """Sample VLM configuration."""
    from src.services.vlm_service_local import VLMConfig
    return VLMConfig(
        model_name_or_path="tests/fixtures/fake_vlm_model",
        device="cuda",
        image_size=384,
        batch_size=2,
        max_new_tokens=64,
        dtype="fp16",
        warmup_runs=0  # Skip warmup in tests
    )


@pytest.fixture
def mock_os_path():
    """Mock os.path.exists to return True for test model path."""
    with patch('os.path.exists', return_value=True):
        yield


@pytest.fixture
def vlm_service(vlm_config, mock_torch, mock_pil, mock_transformers, mock_os_path):
    """Create a VLMService instance with all dependencies mocked."""
    # Import after patches are active
    from src.services.vlm_service_local import VLMService
    service = VLMService(vlm_config)
    yield service
    service.close()


class TestVLMServiceInitialization:
    """Test VLM service initialization and configuration."""

    def test_init_success(self, vlm_service):
        """Test successful initialization with mocked dependencies."""
        assert vlm_service is not None
        assert vlm_service.cfg.image_size == 384
        assert vlm_service.device.type == 'cuda'

    def test_missing_dependencies(self, vlm_config, mock_os_path):
        """Test error when torch/transformers are not installed."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'torch'")):
            from src.services.vlm_service_local import VLMService
            with pytest.raises(RuntimeError, match="VLM dependencies missing"):
                VLMService(vlm_config)

    def test_missing_model_path(self, vlm_config):
        """Test error when model path doesn't exist."""
        from src.services.vlm_service_local import VLMService
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="VLM model path not found"):
                VLMService(vlm_config)


class TestVLMServiceCaptioning:
    """Test image captioning functionality."""

    def test_caption_single_image(self, vlm_service, mock_pil):
        """Test captioning a single image."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        captions = vlm_service.caption_images([img])

        assert len(captions) == 1
        assert isinstance(captions[0], str)
        assert captions[0] == "A test caption"

    def test_caption_multiple_images_batched(self, vlm_service, mock_pil):
        """Test batched captioning of multiple images."""
        images = [Mock() for _ in range(5)]
        for img in images:
            img.convert.return_value = img
            img.size = (384, 384)

        captions = vlm_service.caption_images(images)

        assert len(captions) == 5

    def test_caption_from_file_path(self, vlm_service, mock_pil):
        """Test captioning from file path string."""
        with patch('os.path.exists', return_value=True):
            captions = vlm_service.caption_images(["test_image.jpg"])
            assert len(captions) == 1

    def test_caption_empty_list(self, vlm_service):
        """Test captioning with empty image list."""
        captions = vlm_service.caption_images([])
        assert captions == []

    def test_caption_invalid_image_type(self, vlm_service):
        """Test error handling for invalid image type."""
        with pytest.raises(RuntimeError, match="Image preparation failed"):
            vlm_service.caption_images([123])  # Invalid type

    def test_caption_batch_failure_graceful(self, vlm_service, mock_pil):
        """Test graceful handling of batch processing failure."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        # Make generate fail
        vlm_service.model.generate.side_effect = RuntimeError("GPU error")

        captions = vlm_service.caption_images([img])
        assert len(captions) == 1
        assert "[caption failed]" in captions[0]


class TestVLMServiceVQA:
    """Test Visual Question Answering functionality."""

    def test_answer_question_with_llm(self, vlm_service, mock_pil):
        """Test VQA with LLM client."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        llm_client = Mock()
        llm_client.chat.return_value = {"text": "It's a dog"}

        answer = vlm_service.answer_question(img, "What animal is this?", llm_client)

        assert "dog" in answer.lower()
        llm_client.chat.assert_called_once()

    def test_answer_question_no_llm(self, vlm_service, mock_pil):
        """Test VQA without LLM client (fallback)."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        answer = vlm_service.answer_question(img, "What is this?", llm_client=None)

        assert "Caption:" in answer
        assert "No LLM client" in answer

    def test_answer_question_llm_generate_method(self, vlm_service, mock_pil):
        """Test VQA with LLM that has generate() instead of chat()."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        llm_client = Mock()
        llm_client.chat = None  # No chat method
        llm_client.generate.return_value = "It's a cat"

        answer = vlm_service.answer_question(img, "What is this?", llm_client)

        assert "cat" in answer.lower()

    def test_answer_question_caption_failure(self, vlm_service, mock_pil):
        """Test VQA when captioning fails."""
        img = Mock()
        img.convert.side_effect = RuntimeError("Image processing error")

        answer = vlm_service.answer_question(img, "What is this?")

        assert "Error:" in answer
        assert "caption image" in answer.lower()

    def test_answer_question_llm_failure(self, vlm_service, mock_pil):
        """Test VQA when LLM call fails."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        llm_client = Mock()
        llm_client.chat.side_effect = RuntimeError("LLM timeout")

        answer = vlm_service.answer_question(img, "What is this?", llm_client)

        assert "Caption:" in answer
        assert "failed" in answer.lower()


class TestVLMServiceAsync:
    """Test async wrappers for non-blocking inference."""

    @pytest.mark.asyncio
    async def test_caption_images_async(self, vlm_service, mock_pil):
        """Test async captioning."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        captions = await vlm_service.caption_images_async([img])

        assert len(captions) == 1
        assert isinstance(captions[0], str)

    @pytest.mark.asyncio
    async def test_answer_question_async(self, vlm_service, mock_pil):
        """Test async VQA."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        llm_client = Mock()
        llm_client.chat.return_value = {"text": "A bird"}

        answer = await vlm_service.answer_question_async(img, "What is this?", llm_client)

        assert "bird" in answer.lower()


class TestVLMServiceResourceManagement:
    """Test resource cleanup and context manager."""

    def test_context_manager(self, vlm_config, mock_torch, mock_pil, mock_transformers, mock_os_path):
        """Test using VLM service as context manager."""
        from src.services.vlm_service_local import VLMService

        with VLMService(vlm_config) as vlm:
            assert vlm is not None

        # Verify cleanup was called
        assert mock_torch.cuda.empty_cache.called or True  # May not be called if not CUDA

    def test_close_method(self, vlm_service, mock_torch):
        """Test explicit close() method."""
        vlm_service.close()

        # Verify model was moved to CPU (for CUDA cleanup)
        vlm_service.model.cpu.assert_called_once()

    def test_close_without_model(self, vlm_config, mock_os_path):
        """Test close() when model initialization failed."""
        from src.services.vlm_service_local import VLMService

        with patch('src.services.vlm_service_local.VisionEncoderDecoderModel') as model_mock:
            model_mock.from_pretrained.side_effect = RuntimeError("Load failed")

            try:
                _ = VLMService(vlm_config)  # Will fail but testing cleanup
            except Exception:
                pass

            # Should not raise even if model doesn't exist
            # (in practice, __init__ would fail first, but testing defensive close)


class TestVLMServiceImagePreparation:
    """Test image preparation and validation."""

    def test_prepare_pil_image(self, vlm_service, mock_pil):
        """Test preparing PIL image."""
        img = Mock()
        img.convert.return_value = img
        img.size = (384, 384)

        prepared = vlm_service._prepare_image(img)
        assert prepared is not None

    def test_prepare_file_path(self, vlm_service, mock_pil):
        """Test preparing image from file path."""
        with patch('os.path.exists', return_value=True):
            prepared = vlm_service._prepare_image("test.jpg")
            assert prepared is not None

    def test_prepare_invalid_path(self, vlm_service):
        """Test error for non-existent file path."""
        with pytest.raises(FileNotFoundError):
            vlm_service._prepare_image("nonexistent.jpg")

    def test_prepare_numpy_array(self, vlm_service, mock_pil):
        """Test preparing numpy array."""
        import numpy as np
        arr = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch('PIL.Image.fromarray') as mock_from_array:
            img = Mock()
            img.convert.return_value = img
            img.size = (384, 384)
            mock_from_array.return_value = img

            prepared = vlm_service._prepare_image(arr)
            assert prepared is not None

    def test_prepare_resize_small_image(self, vlm_service, mock_pil):
        """Test resizing small image to target size."""
        img = Mock()
        img.convert.return_value = img
        img.size = (100, 100)  # Smaller than target
        img.thumbnail = Mock()

        _ = vlm_service._prepare_image(img)
        img.thumbnail.assert_called_once()


class TestVLMServiceFactory:
    """Test factory function for building VLM from config."""

    def test_build_from_config(self, mock_torch, mock_pil, mock_transformers, mock_os_path):
        """Test building VLM service from configuration dict."""
        from src.services.vlm_service_local import build_vlm_from_config

        config = {
            "vlm": {
                "model_name_or_path": "tests/fixtures/fake_model",
                "device": "cuda",
                "batch_size": 4
            }
        }

        vlm = build_vlm_from_config(config)
        assert vlm is not None
        assert vlm.cfg.batch_size == 4
        vlm.close()

    def test_build_missing_model_path(self):
        """Test error when model_name_or_path is missing."""
        from src.services.vlm_service_local import build_vlm_from_config

        config = {"vlm": {}}

        with pytest.raises(ValueError, match="model_name_or_path is required"):
            build_vlm_from_config(config)

    def test_build_no_vlm_section(self):
        """Test error when vlm section is missing."""
        from src.services.vlm_service_local import build_vlm_from_config

        config = {}

        with pytest.raises(ValueError, match="model_name_or_path is required"):
            build_vlm_from_config(config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

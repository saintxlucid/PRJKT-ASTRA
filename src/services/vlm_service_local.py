# SPDX-License-Identifier: MIT
"""
Vision-Language Model (VLM) Service - local-first

This module provides a comprehensive VLM wrapper that supports:
- image captioning (batch, async-capable)
- simple VQA by composing caption + question and forwarding to a text LLM
- robust input handling (PIL, numpy, paths)
- resource cleanup (context manager)
- offline-friendly: accept local model paths (no network download attempts)

Design goals:
- Optional: only loaded when transformers/torch/PIL are installed and local weights exist
- Device-aware: prefer CUDA when available, fallback to CPU
- Smooth runtime: batch inference, half precision on CUDA, no_grad, warm-up
- Production-ready: async wrappers, explicit cleanup, defensive error handling

Usage:
    from services.vlm_service_local import build_vlm_from_config
    
    # Sync usage
    with build_vlm_from_config(conf) as vlm:
        captions = vlm.caption_images([PIL.Image.open('img1.jpg')])
        answer = vlm.answer_question(image, question, llm_client=local_llm_client)
    
    # Async usage in FastAPI
    vlm = build_vlm_from_config(conf)
    captions = await vlm.caption_images_async([img1, img2])
    vlm.close()

Note: For VQA we rely on your provided local LLM (llamacpp) to answer questions given a caption + question prompt.
"""
from __future__ import annotations

import asyncio
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol


class LLMClientProtocol(Protocol):
    """Protocol for LLM clients that can answer VQA prompts."""
    def chat(self, prompt: str, system: str = "") -> dict[str, Any]:
        """Return dict with 'text' key containing the response."""
        ...


@dataclass
class VLMConfig:
    """Configuration for local Vision-Language Model."""
    model_name_or_path: str  # Local path to VisionEncoderDecoder or blip-like model
    device: str | None = None  # 'cuda' | 'cpu' | None (auto)
    image_size: int = 384
    batch_size: int = 4
    max_new_tokens: int = 64
    dtype: str = "fp16"  # fp16 on CUDA, fp32 on CPU
    warmup_runs: int = 1


class VLMService:
    """Local Vision-Language Model service with async support and resource management."""

    def __init__(self, cfg: VLMConfig):
        self.cfg = cfg
        self._executor: ThreadPoolExecutor | None = None

        # Lazy imports to keep project lightweight when not used
        try:
            import torch
            from PIL import Image
            from transformers import (
                AutoProcessor,
                AutoTokenizer,
                VisionEncoderDecoderModel,
            )
        except Exception as e:
            raise RuntimeError(
                "VLM dependencies missing. Install: pip install torch transformers pillow"
            ) from e

        self.torch = torch
        self.Image = Image
        self.AutoProcessor = AutoProcessor
        self.VisionEncoderDecoderModel = VisionEncoderDecoderModel
        self.AutoTokenizer = AutoTokenizer

        # Device selection
        if cfg.device:
            device = cfg.device
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = torch.device(device)

        # Data type selection
        if cfg.dtype == "fp16" and self.device.type == "cuda":
            self.dtype = torch.float16
        else:
            self.dtype = torch.float32

        # Validate model path
        if not os.path.exists(cfg.model_name_or_path):
            raise FileNotFoundError(
                f"VLM model path not found: {cfg.model_name_or_path}.\nProvide a local VisionEncoderDecoder model directory or file."
            )

        # Load processor + model + tokenizer
        self.processor = self.AutoProcessor.from_pretrained(cfg.model_name_or_path)
        self.model = self.VisionEncoderDecoderModel.from_pretrained(cfg.model_name_or_path)
        self.tokenizer = self.AutoTokenizer.from_pretrained(cfg.model_name_or_path)

        # Move model to device
        self.model.to(self.device)
        self.model.eval()

        # If CUDA and dtype is fp16, convert
        if self.device.type == "cuda" and self.dtype == torch.float16:
            try:
                self.model.half()
            except Exception:
                # Not all models support .half(); ignore silently
                pass

        # Warm-up (small dummy forward) to stabilize kernels
        self._warmup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
        return False

    def close(self):
        """Free CUDA memory and cleanup resources."""
        if hasattr(self, 'model'):
            try:
                # Move model to CPU to free CUDA memory
                self.model.cpu()
                del self.model
                if self.device.type == "cuda":
                    self.torch.cuda.empty_cache()
            except Exception as e:
                warnings.warn(f"VLM cleanup warning: {e}", stacklevel=2)

        # Shutdown executor if exists
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def _get_executor(self) -> ThreadPoolExecutor:
        """Lazy-create thread pool executor for async operations."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vlm")
        return self._executor

    def _prepare_image(self, img: Any) -> Any:
        """Convert various image formats to PIL.Image and validate/resize."""
        # Handle string paths
        if isinstance(img, str):
            if not os.path.exists(img):
                raise FileNotFoundError(f"Image file not found: {img}")
            img = self.Image.open(img)

        # Handle numpy arrays
        try:
            import numpy as np
            if isinstance(img, np.ndarray):
                img = self.Image.fromarray(img)
        except ImportError:
            pass

        # Ensure PIL Image
        if not hasattr(img, 'convert'):
            raise TypeError(f"Unsupported image type: {type(img)}. Expected PIL.Image, path string, or numpy array.")

        # Convert to RGB
        img = img.convert("RGB")

        # Resize to target size (center crop if needed)
        target = (self.cfg.image_size, self.cfg.image_size)
        if img.size != target:
            # Use thumbnail to preserve aspect ratio, then paste on square canvas
            img.thumbnail(target, self.Image.Resampling.LANCZOS)
            canvas = self.Image.new("RGB", target, (0, 0, 0))
            offset = ((target[0] - img.size[0]) // 2, (target[1] - img.size[1]) // 2)
            canvas.paste(img, offset)
            img = canvas

        return img

    def _warmup(self):
        # Run a tiny forward pass to initialize CUDA kernels
        try:
            dummy = self.Image.new("RGB", (self.cfg.image_size, self.cfg.image_size), "white")
            with self.torch.no_grad():
                inputs = self.processor(images=[dummy], return_tensors="pt")
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                # Encoder forward
                _ = self.model.generate(**inputs, max_new_tokens=4)
        except Exception:
            # Warmup not critical
            pass

    def caption_images(self, images: list[Any]) -> list[str]:
        """Generate captions for a list of images (batched).

        Args:
            images: List of PIL.Image, file paths, or numpy arrays

        Returns:
            List of caption strings

        Raises:
            TypeError: If image format is unsupported
            FileNotFoundError: If image path doesn't exist
        """
        if not images:
            return []

        captions: list[str] = []
        bs = max(1, self.cfg.batch_size)

        # Prepare all images first (validate and normalize)
        try:
            pil_images = [self._prepare_image(img) for img in images]
        except Exception as e:
            raise RuntimeError(f"Image preparation failed: {e}") from e

        # Process in batches
        for i in range(0, len(pil_images), bs):
            batch = pil_images[i : i + bs]
            try:
                with self.torch.no_grad():
                    inputs = self.processor(images=batch, return_tensors="pt", padding=True)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}

                    gen = self.model.generate(
                        **inputs,
                        max_new_tokens=self.cfg.max_new_tokens,
                        num_beams=3,
                        do_sample=False
                    )

                    texts = self.tokenizer.batch_decode(gen, skip_special_tokens=True)
                    captions.extend([t.strip() for t in texts])
            except Exception as e:
                warnings.warn(f"VLM batch captioning failed for batch {i//bs}: {e}", stacklevel=2)
                # Return empty captions for failed batch
                captions.extend(["[caption failed]"] * len(batch))

        return captions

    async def caption_images_async(self, images: list[Any]) -> list[str]:
        """Async version of caption_images for non-blocking inference.

        Args:
            images: List of PIL.Image, file paths, or numpy arrays

        Returns:
            List of caption strings
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._get_executor(),
            self.caption_images,
            images
        )

    def answer_question(self, image: Any, question: str, llm_client: LLMClientProtocol | None = None) -> str:
        """Answer a question about an image using caption + LLM.

        Strategy:
        1. Caption the image
        2. Compose prompt: "Caption: {caption}\nQuestion: {question}\nAnswer:" and send to LLM client
        3. If no LLM client provided, returns caption + fallback message

        Args:
            image: PIL.Image, file path, or numpy array
            question: User's question about the image
            llm_client: Optional LLM client with chat(prompt, system) method

        Returns:
            Answer string
        """
        try:
            caption = self.caption_images([image])[0]
        except Exception as e:
            return f"Error: Could not caption image. {e}"

        prompt = f"Image caption: {caption}\nUser question: {question}\nAnswer concisely:"

        if llm_client is None:
            # Fallback: return caption plus instruction
            return f"Caption: {caption}\n(No LLM client provided for answering questions)"

        # Use provided LLM client for final answer
        try:
            # Try chat method first (standard)
            if hasattr(llm_client, 'chat'):
                resp = llm_client.chat(
                    prompt=prompt,
                    system="You are a helpful assistant that answers questions about images based on their captions."
                )
                if isinstance(resp, dict):
                    return resp.get("text", str(resp)).strip()
                return str(resp).strip()

            # Fallback to generate method
            elif hasattr(llm_client, 'generate'):
                resp = llm_client.generate(prompt)
                return str(resp).strip()

            else:
                warnings.warn(
                    "LLM client has no chat() or generate() method. Returning caption only.",
                    stacklevel=2
                )
                return f"Caption: {caption}\n(LLM client interface not compatible)"

        except Exception as e:
            warnings.warn(f"VLM->LLM handoff failed: {e}", stacklevel=2)
            return f"Caption: {caption}\n(LLM call failed: {e})"

    async def answer_question_async(
        self,
        image: Any,
        question: str,
        llm_client: LLMClientProtocol | None = None
    ) -> str:
        """Async version of answer_question for non-blocking inference.

        Args:
            image: PIL.Image, file path, or numpy array
            question: User's question about the image
            llm_client: Optional LLM client with chat(prompt, system) method

        Returns:
            Answer string
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._get_executor(),
            self.answer_question,
            image,
            question,
            llm_client
        )


def build_vlm_from_config(conf: dict) -> VLMService:
    """Factory to build VLM service from configuration dict.

    Config example:
    vlm:
      model_name_or_path: "models/vlm/blip2-local"
      device: null
      image_size: 384
      batch_size: 4

    """
    vlm_conf = conf.get("vlm", {})
    model_path = vlm_conf.get("model_name_or_path")
    if not model_path:
        raise ValueError("vlm.model_name_or_path is required in astra.yaml for VLM support")

    cfg = VLMConfig(
        model_name_or_path=model_path,
        device=vlm_conf.get("device"),
        image_size=vlm_conf.get("image_size", 384),
        batch_size=vlm_conf.get("batch_size", 4),
        max_new_tokens=vlm_conf.get("max_new_tokens", 64),
        dtype=vlm_conf.get("dtype", "fp16")
    )

    return VLMService(cfg)

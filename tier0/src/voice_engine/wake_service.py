"""ASTRA Tier-0: Voice Wake Service

Real-time microphone monitoring for wake words using:
- WebRTC VAD (Voice Activity Detection)
- Faster-Whisper (CPU-optimized ASR)
- Offline wake-word patterns

Created: October 18, 2025
"""

import os
import io
import threading
from typing import Optional, Callable, List
from pathlib import Path

import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

try:
    from webrtcvad import Vad
    HAS_VAD = True
except ImportError:
    HAS_VAD = False


# ---- Mini logger ----
class _Logger:
    def info(self, msg: str) -> None:
        print(f"[ASTRA][voice] {msg}")
    
    def warn(self, msg: str) -> None:
        print(f"[ASTRA][voice][WARN] {msg}")
    
    def error(self, msg: str) -> None:
        print(f"[ASTRA][voice][ERR] {msg}")


logger = _Logger()


def _load_wake_words() -> List[str]:
    """Load wake words from config file"""
    config_path = Path(__file__).parent / "wake_words.yaml"
    
    if not config_path.exists():
        logger.warn(f"wake_words.yaml not found at {config_path}")
        return ["astra"]
    
    import yaml
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        phrases = data.get("wake_words", {}).get("phrases", ["astra"])
        return [p.lower() for p in phrases]
    except Exception as e:
        logger.error(f"Failed to load wake words: {e}")
        return ["astra"]


class WakeService:
    """
    Real-time voice wake-word detector.
    
    Features:
    - WebRTC VAD for activity detection
    - Faster-Whisper for accurate transcription
    - Configurable wake words
    - Background monitoring thread
    """
    
    # Audio params
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 512
    VAD_MODE = 2  # 0=most lenient, 3=most strict
    
    def __init__(
        self,
        device: Optional[int] = None,
        model_size: str = "small",
        on_wake: Optional[Callable[[str], None]] = None,
        on_transcript: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize voice service.
        
        Args:
            device: Audio device index (None=default)
            model_size: Whisper model ("tiny", "small", "base", "small.en")
            on_wake: Callback when wake word detected
            on_transcript: Callback for all transcription
        """
        self.device = device
        self.model_size = model_size
        self.on_wake = on_wake or (lambda _: None)
        self.on_transcript = on_transcript or (lambda _: None)
        
        self.wake_words = _load_wake_words()
        self.enabled = os.getenv("ASTRA_VOICE_ENABLED", "true").lower() == "true"
        
        # Initialize whisper
        model_dir = os.getenv("ASTRA_WHISPER_MODEL_DIR", "./models/whisper-small-int8")
        self.whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            model_dir=model_dir,
        )
        
        # Initialize VAD if available
        self.vad = Vad(self.VAD_MODE) if HAS_VAD else None
        
        self.running = False
        self.stream = None
        self.thread = None
        
        logger.info(f"Voice service initialized (model: {model_size})")
        logger.info(f"Wake words: {self.wake_words}")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback"""
        if status:
            logger.warn(f"Audio status: {status}")
        
        audio_data = indata[:, 0]  # Mono
        self._process_audio(audio_data)
    
    def _process_audio(self, audio_chunk: np.ndarray) -> None:
        """
        Process audio chunk for wake words.
        
        Runs VAD first (cheap), then transcribes if activity detected.
        """
        if not self.enabled or not self.running:
            return
        
        # VAD check (if available)
        if self.vad:
            try:
                audio_bytes = (audio_chunk * 32767).astype(np.int16).tobytes()
                has_speech = self.vad.is_speech(audio_bytes, self.SAMPLE_RATE)
                if not has_speech:
                    return
            except Exception as e:
                logger.error(f"VAD error: {e}")
        
        # Transcribe
        try:
            segments, _ = self.whisper_model.transcribe(
                io.BytesIO(audio_chunk),
                language="en",
                task="transcribe",
            )
            
            for segment in segments:
                text = segment.text.strip().lower()
                
                if not text:
                    continue
                
                self.on_transcript(text)
                logger.info(f"Transcribed: {text}")
                
                # Check for wake word
                for wake_word in self.wake_words:
                    if wake_word in text:
                        logger.info(f"WAKE WORD DETECTED: {wake_word}")
                        self.on_wake(wake_word)
                        break
        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
    
    def start(self) -> None:
        """Start listening for wake words"""
        if self.running:
            logger.warn("Already running")
            return
        
        if not self.enabled:
            logger.error("Voice service disabled by policy")
            raise PermissionError("Voice disabled")
        
        self.running = True
        
        # Start audio stream
        self.stream = sd.InputStream(
            device=self.device,
            samplerate=self.SAMPLE_RATE,
            channels=1,
            blocksize=self.CHUNK_SIZE,
            callback=self._audio_callback,
        )
        self.stream.start()
        
        logger.info("Voice service started")
    
    def stop(self) -> None:
        """Stop listening"""
        if not self.running:
            return
        
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        logger.info("Voice service stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()

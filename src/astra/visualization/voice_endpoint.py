"""
Voice endpoint for Whisper 3 Turbo GGUF via subprocess.
POST /api/voice/transcribe -> returns text transcript

Part of ASTRA Ascension Stack V2 Add-ons
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/voice", tags=["voice"])

# Environment configuration
WHISPER_BIN = os.environ.get("WHISPER_BIN", "main.exe")  # whisper.cpp binary
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "models/whisper-turbo.gguf")


class TranscribeResponse(BaseModel):
    """Response from transcription endpoint"""
    text: str
    duration: Optional[float] = None
    language: Optional[str] = None


class TranscribeRequest(BaseModel):
    """Optional parameters for transcription"""
    language: Optional[str] = None
    translate: bool = False


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: Optional[str] = None,
    translate: bool = False
):
    """
    Transcribe audio file using Whisper 3 Turbo GGUF.
    
    Args:
        file: Audio file (wav, mp3, m4a, etc.)
        language: Optional language code (auto-detect if not specified)
        translate: Translate to English if True
        
    Returns:
        TranscribeResponse with text transcript
        
    Environment Variables:
        WHISPER_BIN: Path to whisper.cpp executable (default: main.exe)
        WHISPER_MODEL: Path to GGUF model file (default: models/whisper-turbo.gguf)
    """
    tmp_path = None
    
    try:
        # Validate whisper binary exists
        if not Path(WHISPER_BIN).exists():
            raise HTTPException(
                status_code=500,
                detail=f"Whisper binary not found: {WHISPER_BIN}. Set WHISPER_BIN environment variable."
            )
        
        # Validate model exists
        if not Path(WHISPER_MODEL).exists():
            raise HTTPException(
                status_code=500,
                detail=f"Whisper model not found: {WHISPER_MODEL}. Set WHISPER_MODEL environment variable."
            )
        
        # Save uploaded file to temp
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name
        
        logger.info("voice_transcribe_start", filename=file.filename, size=len(content))
        
        # Build whisper.cpp command
        cmd = [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", tmp_path]
        
        if language:
            cmd.extend(["-l", language])
        
        if translate:
            cmd.append("--translate")
        
        # Execute whisper.cpp
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )
        
        if result.returncode != 0:
            logger.error("whisper_failed", stderr=result.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Whisper failed: {result.stderr}"
            )
        
        # Parse output
        output_lines = result.stdout.strip().splitlines()
        
        # Whisper.cpp outputs timestamps + text on each line
        # Extract just the text portions
        text_parts = []
        for line in output_lines:
            # Skip metadata lines
            if line.startswith("[") or not line.strip():
                continue
            # Remove timestamp prefix if present (format: [00:00.000 --> 00:05.000])
            if "]" in line:
                text = line.split("]", 1)[-1].strip()
            else:
                text = line.strip()
            if text:
                text_parts.append(text)
        
        final_text = " ".join(text_parts)
        
        if not final_text:
            final_text = output_lines[-1] if output_lines else ""
        
        logger.info("voice_transcribe_success", length=len(final_text))
        
        return TranscribeResponse(
            text=final_text,
            language=language
        )
        
    except subprocess.TimeoutExpired:
        logger.error("whisper_timeout")
        raise HTTPException(
            status_code=500,
            detail="Transcription timed out (>60s)"
        )
    except subprocess.CalledProcessError as e:
        logger.error("whisper_process_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Whisper process error: {e}"
        )
    except Exception as e:
        logger.error("voice_transcribe_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Transcription error: {str(e)}"
        )
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning("temp_file_cleanup_failed", path=tmp_path, error=str(e))


@router.get("/config")
def get_voice_config():
    """Get current voice endpoint configuration"""
    return {
        "whisper_bin": WHISPER_BIN,
        "whisper_model": WHISPER_MODEL,
        "whisper_bin_exists": Path(WHISPER_BIN).exists(),
        "whisper_model_exists": Path(WHISPER_MODEL).exists()
    }


@router.get("/health")
def voice_health():
    """Health check for voice endpoint"""
    bin_exists = Path(WHISPER_BIN).exists()
    model_exists = Path(WHISPER_MODEL).exists()
    
    return {
        "status": "ready" if (bin_exists and model_exists) else "not_configured",
        "whisper_bin_ok": bin_exists,
        "whisper_model_ok": model_exists,
        "message": "Voice transcription ready" if (bin_exists and model_exists) else "Configure WHISPER_BIN and WHISPER_MODEL environment variables"
    }

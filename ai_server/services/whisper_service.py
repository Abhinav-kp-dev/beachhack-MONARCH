"""Whisper Transcription Service - Simple and reliable speech-to-text"""
import whisper
import logging
from typing import Dict, Any
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# Global model instance
_model = None

def _load_model():
    """Lazy load Whisper model"""
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {config.WHISPER_MODEL}...")
        _model = whisper.load_model(config.WHISPER_MODEL, device=config.WHISPER_DEVICE)
        logger.info("Whisper model loaded successfully")
"""Whisper Transcription Service - Simple and reliable speech-to-text"""
import whisper
import logging
from typing import Dict, Any
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# Global model instance
_model = None

def _load_model():
    """Lazy load Whisper model"""
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {config.WHISPER_MODEL}...")
        _model = whisper.load_model(config.WHISPER_MODEL, device=config.WHISPER_DEVICE)
        logger.info("Whisper model loaded successfully")
    return _model

def transcribe_audio(audio_path: str, return_timestamps: bool = False) -> Dict[str, Any]:
    """
    Transcribe audio file using Whisper
    
    Args:
        audio_path: Path to audio file
        return_timestamps: If True, return segment-level timestamps (not used for simple version)
        
    Returns:
        Dictionary with 'text', 'language', and 'segments_count'
    """
    try:
        model = _load_model()
        logger.info(f"Transcribing audio: {os.path.basename(audio_path)}")
        
        # Transcribe with Whisper
        result = model.transcribe(audio_path, language="en")
        
        # Extract text
        text = result["text"].strip()
        language = result.get("language", "en")
        segments_count = len(result.get("segments", []))
        
        response = {
            "text": text,
            "language": language,
            "segments_count": segments_count
        }
        
        logger.info(f"Transcription successful: {len(text)} characters, {segments_count} segments")
        return response
        
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}", exc_info=True)
        raise RuntimeError(f"Transcription failed: {str(e)}")

def get_transcriber_info() -> Dict[str, Any]:
    """Get transcriber information"""
    return {
        "model": config.WHISPER_MODEL,
        "device": config.WHISPER_DEVICE,
        "model_loaded": _model is not None
    }


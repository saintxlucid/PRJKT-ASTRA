"""ASTRA Dataset Schema

Standard normalized record format across all datasets.
All values are optional to handle heterogeneous sources.

Created: October 18, 2025
"""

from __future__ import annotations
from typing import TypedDict, Optional, Dict, Any


class Record(TypedDict, total=False):
    """
    Normalized ASTRA dataset record.
    
    Fields:
        audio: Optional audio data with array, path, and sampling rate
        text: Raw or transcribed text
        label: Primary label (intent, class, emotion, etc.)
        meta: Additional metadata (speaker_id, context, etc.)
    """
    audio: Optional[Dict[str, Any]]    # { "array": np.ndarray | None, "path": str | None, "sampling_rate": int | None }
    text: Optional[str]
    label: Optional[str]               # stringifiable label
    meta: Dict[str, Any]               # everything else


# Standard field names
AUDIO = "audio"
TEXT = "text"
LABEL = "label"
META = "meta"

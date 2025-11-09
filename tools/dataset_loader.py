"""ASTRA Dataset Loader

Load local datasets from disk and normalize to standard schema.
Offline-first: uses load_from_disk only, no network access.

Created: October 18, 2025
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, Optional

from datasets import load_from_disk, Dataset, DatasetDict

from .schema import Record, AUDIO, TEXT, LABEL, META


# ---- Configuration ----

DATA_DIR = Path(os.getenv("ASTRA_DATA_DIR", "./data")).resolve()


# ---- Privacy & Security ----

class PrivacyError(RuntimeError):
    """Raised when network access is attempted in offline mode"""
    pass


def require_offline() -> None:
    """
    Enforce offline-only mode.
    
    Raises:
        PrivacyError: If network access is enabled
    """
    if os.getenv("ASTRA_ALLOW_NETWORK", "0") not in ("0", "", "false", "False"):
        raise PrivacyError(
            "Network access is disabled by policy (ASTRA_ALLOW_NETWORK must be 0/false)"
        )


# ---- Dataset Loading ----

def _load_local(name: str) -> Dataset | DatasetDict:
    """
    Load dataset from local disk.
    
    Args:
        name: Dataset name (e.g., "google/speech_commands")
        
    Returns:
        Loaded Dataset or DatasetDict
        
    Raises:
        FileNotFoundError: If dataset not found locally
    """
    path = DATA_DIR / name.replace("/", "__")
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found locally: {path}\n"
            f"Run bootstrap_datasets.py first to download datasets."
        )
    return load_from_disk(str(path))


def _ensure_dataset(ds) -> Dataset:
    """
    Normalize DatasetDict to single Dataset.
    
    Args:
        ds: Dataset or DatasetDict
        
    Returns:
        Single Dataset instance
        
    Raises:
        TypeError: If ds is not Dataset or DatasetDict
    """
    if isinstance(ds, Dataset):
        return ds
    
    if isinstance(ds, DatasetDict):
        # Prefer "data" split (created in bootstrap); else pick first
        if "data" in ds:
            return ds["data"]
        key = next(iter(ds.keys()))
        return ds[key]
    
    raise TypeError(f"Unsupported dataset type: {type(ds)}")


# ---- Normalizers ----
# Each normalizer maps dataset-specific fields to ASTRA Record schema

def norm_speech_commands(row) -> Record:
    """
    Normalize google/speech_commands dataset.
    
    Schema: {audio, label, speaker_id}
    """
    rec: Record = {META: {}}
    
    # Handle audio (dict or path)
    a = row.get("audio")
    if isinstance(a, dict):
        rec[AUDIO] = {
            "array": a.get("array"),
            "path": a.get("path"),
            "sampling_rate": a.get("sampling_rate"),
        }
    else:
        rec[AUDIO] = {
            "array": None,
            "path": row.get("file"),
            "sampling_rate": None,
        }
    
    rec[TEXT] = None
    rec[LABEL] = str(row.get("label", ""))
    rec[META] = {"speaker_id": row.get("speaker_id")}
    
    return rec


def norm_librispeech(row) -> Record:
    """
    Normalize openslr/librispeech_asr dataset.
    
    Schema: {audio, text, id}
    """
    a = row.get("audio", {})
    return {
        AUDIO: {
            "array": a.get("array"),
            "path": a.get("path"),
            "sampling_rate": a.get("sampling_rate"),
        },
        TEXT: row.get("text"),
        LABEL: None,
        META: {"id": row.get("id")},
    }


def norm_clinc150(row) -> Record:
    """
    Normalize contemmcm/clinc150 dataset.
    
    Schema: {text, intent}
    """
    return {
        TEXT: row.get("text"),
        LABEL: row.get("intent"),
        META: {},
    }


def norm_banking77(row) -> Record:
    """
    Normalize PolyAI/banking77 dataset.
    
    Schema: {text, label}
    """
    return {
        TEXT: row.get("text"),
        LABEL: row.get("label"),
        META: {},
    }


def norm_ag_news(row) -> Record:
    """
    Normalize ag_news dataset.
    
    Schema: {text, label}
    """
    return {
        TEXT: row.get("text"),
        LABEL: row.get("label"),
        META: {},
    }


def norm_imdb(row) -> Record:
    """
    Normalize imdb dataset.
    
    Schema: {text, label}
    """
    return {
        TEXT: row.get("text"),
        LABEL: row.get("label"),
        META: {},
    }


def norm_funsd(row) -> Record:
    """
    Normalize docvqa/funsd dataset.
    
    Schema: {image, annotations} - OCR/document understanding
    """
    img = row.get("image")
    meta = {k: row[k] for k in row.keys() if k != "image"}
    return {
        AUDIO: None,
        TEXT: None,
        LABEL: None,
        META: {"image": img, **meta},
    }


def norm_rtp(row) -> Record:
    """
    Normalize allenai/real-toxicity-prompts dataset.
    
    Schema: {prompt, toxicity}
    """
    return {
        TEXT: row.get("prompt", ""),
        LABEL: None,
        META: {"toxicity": row.get("toxicity", None)},
    }


def norm_mbpp(row) -> Record:
    """
    Normalize mbpp (code) dataset.
    
    Schema: {text/prompt, task_id, code}
    """
    return {
        TEXT: row.get("text", row.get("prompt", "")),
        LABEL: row.get("task_id", None),
        META: {"code": row.get("code", "")},
    }


def norm_squad(row) -> Record:
    """
    Normalize squad (QA) dataset.
    
    Schema: {question, context, answers}
    """
    q = row.get("question", "")
    ctx = row.get("context", "")
    ans = row.get("answers", {})
    return {
        TEXT: q,
        LABEL: None,
        META: {"context": ctx, "answers": ans},
    }


def norm_wikitext(row) -> Record:
    """
    Normalize wikitext dataset.
    
    Schema: {text}
    """
    return {
        TEXT: row.get("text", ""),
        LABEL: None,
        META: {},
    }


def norm_snips(row) -> Record:
    """
    Normalize snips_built_in_intents dataset.
    
    Schema: {text, intent, entities}
    """
    return {
        TEXT: row.get("text", ""),
        LABEL: row.get("intent"),
        META: {"entities": row.get("entities", [])},
    }


# ---- Normalizer Registry ----

NORMALIZERS: Dict[str, Callable[[Dict], Record]] = {
    "google__speech_commands": norm_speech_commands,
    "openslr__librispeech_asr": norm_librispeech,
    "contemmcm__clinc150": norm_clinc150,
    "PolyAI__banking77": norm_banking77,
    "ag_news": norm_ag_news,
    "imdb": norm_imdb,
    "docvqa__funsd": norm_funsd,
    "allenai__real-toxicity-prompts": norm_rtp,
    "mbpp": norm_mbpp,
    "squad": norm_squad,
    "wikitext": norm_wikitext,
    "snips_built_in_intents": norm_snips,
}


def _key(name: str) -> str:
    """Normalize dataset name to registry key"""
    return name.replace("/", "__")


# ---- Main API ----

def load_normalized(
    name: str,
    limit: Optional[int] = None,
) -> Iterator[Record]:
    """
    Load and normalize dataset records.
    
    Offline-only: loads from local disk, no network access.
    
    Args:
        name: Dataset name (e.g., "google/speech_commands")
        limit: Max records to yield (None = all)
        
    Yields:
        Normalized Record dicts
        
    Raises:
        FileNotFoundError: If dataset not found locally
        KeyError: If no normalizer registered for dataset
        PrivacyError: If network access is attempted
    """
    require_offline()
    
    ds = _ensure_dataset(_load_local(name))
    key = _key(name)
    norm = NORMALIZERS.get(key)
    
    if not norm:
        raise KeyError(
            f"No normalizer registered for '{name}' (key='{key}')\n"
            f"Available: {list(NORMALIZERS.keys())}"
        )
    
    n = 0
    for row in ds:
        yield norm(row)
        n += 1
        if limit and n >= limit:
            break

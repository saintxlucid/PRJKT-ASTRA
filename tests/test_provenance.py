from provenance import sign_file, verify_signature
from pathlib import Path

def test_sign_and_detect_tamper(tmp_path: Path):
    f = tmp_path / "m.gguf"
    f.write_bytes(b"abc")
    sig = sign_file(str(f), {"test": True})
    assert verify_signature(str(f)) is True
    # tamper one byte
    f.write_bytes(b"abX")
    assert verify_signature(str(f)) is False
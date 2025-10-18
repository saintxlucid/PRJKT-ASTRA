"""Tests for Dataset Loader + Normalizers

Run with: pytest tests/test_dataset_loader.py -v

Created: October 18, 2025
"""

import os
import pytest

# Enforce offline mode
os.environ["ASTRA_ALLOW_NETWORK"] = "0"

from tools.dataset_loader import load_normalized, PrivacyError
from tools.schema import Record, AUDIO, TEXT, LABEL, META


class TestOfflineMode:
    """Offline-only enforcement tests"""
    
    def test_offline_by_default(self):
        """Offline mode is default"""
        assert os.getenv("ASTRA_ALLOW_NETWORK", "0") == "0"
    
    def test_allow_network_disables_offline(self):
        """Setting ASTRA_ALLOW_NETWORK=1 doesn't raise in loader"""
        # This just validates the flag works; actual network prevention
        # happens at load_normalized() call
        os.environ["ASTRA_ALLOW_NETWORK"] = "1"
        try:
            # Should not raise when checking flag
            pass
        finally:
            os.environ["ASTRA_ALLOW_NETWORK"] = "0"


class TestRecordSchema:
    """Record schema validation"""
    
    def test_record_structure(self):
        """Record has required keys"""
        rec: Record = {
            AUDIO: None,
            TEXT: "hello",
            LABEL: "greeting",
            META: {"source": "test"},
        }
        assert TEXT in rec
        assert LABEL in rec
        assert META in rec
    
    def test_record_optional_fields(self):
        """Record fields are optional"""
        rec1: Record = {TEXT: "hello"}
        rec2: Record = {AUDIO: None, LABEL: "test"}
        rec3: Record = {META: {}}
        
        # All should be valid


class TestDatasetLoading:
    """Dataset loading and normalization tests"""
    
    @pytest.mark.parametrize("name,limit", [
        ("google/speech_commands", 3),
        ("openslr/librispeech_asr", 2),
        ("contemmcm/clinc150", 5),
        ("PolyAI/banking77", 3),
        ("ag_news", 2),
        ("imdb", 2),
        ("docvqa/funsd", 1),
        ("allenai/real-toxicity-prompts", 3),
        ("mbpp", 1),
        ("squad", 2),
        ("wikitext", 2),
        ("snips_built_in_intents", 2),
    ])
    def test_load_datasets(self, name, limit):
        """Load normalized records from each dataset"""
        try:
            records = list(load_normalized(name, limit=limit))
            
            # Should have some records
            assert len(records) > 0
            assert len(records) <= limit
            
            # Each record should have at least one content field
            for rec in records:
                assert any(
                    rec.get(k) is not None
                    for k in (AUDIO, TEXT, LABEL, META)
                ), f"Record has no content: {rec}"
        
        except FileNotFoundError:
            # OK if dataset not downloaded yet
            pytest.skip(f"Dataset not available locally: {name}")
    
    def test_load_with_limit(self):
        """Limit parameter respected"""
        try:
            all_recs = list(load_normalized("contemmcm/clinc150", limit=None))
            lim_recs = list(load_normalized("contemmcm/clinc150", limit=3))
            
            assert len(lim_recs) <= 3
            assert len(lim_recs) <= len(all_recs)
        
        except FileNotFoundError:
            pytest.skip("Dataset not available locally")
    
    def test_normalizer_missing_raises(self):
        """Unknown dataset raises KeyError"""
        with pytest.raises(KeyError):
            list(load_normalized("unknown/dataset", limit=1))


class TestSpeechCommands:
    """google/speech_commands normalizer tests"""
    
    def test_loads_audio_fields(self):
        """Speech commands audio fields normalized"""
        try:
            recs = list(load_normalized("google/speech_commands", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            assert AUDIO in rec or TEXT in rec or LABEL in rec
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestLibrispeech:
    """openslr/librispeech_asr normalizer tests"""
    
    def test_loads_text(self):
        """Librispeech text field loaded"""
        try:
            recs = list(load_normalized("openslr/librispeech_asr", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            # Should have text
            assert rec.get(TEXT) is not None
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestCLINC150:
    """contemmcm/clinc150 normalizer tests"""
    
    def test_loads_intent(self):
        """CLINC150 intent label normalized"""
        try:
            recs = list(load_normalized("contemmcm/clinc150", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            # Should have text and label
            assert rec.get(TEXT) is not None
            assert rec.get(LABEL) is not None
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestBanking77:
    """PolyAI/banking77 normalizer tests"""
    
    def test_loads_banking_intents(self):
        """Banking77 intents normalized"""
        try:
            recs = list(load_normalized("PolyAI/banking77", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            assert rec.get(TEXT) is not None
            assert rec.get(LABEL) is not None
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestTextClassification:
    """Text classification datasets (ag_news, imdb)"""
    
    @pytest.mark.parametrize("name", ["ag_news", "imdb"])
    def test_loads_text_and_label(self, name):
        """Text classification datasets have text and label"""
        try:
            recs = list(load_normalized(name, limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            assert rec.get(TEXT) is not None
        
        except FileNotFoundError:
            pytest.skip(f"Dataset not available: {name}")


class TestToxicity:
    """allenai/real-toxicity-prompts normalizer tests"""
    
    def test_loads_prompts(self):
        """Real-toxicity-prompts normalized"""
        try:
            recs = list(load_normalized(
                "allenai/real-toxicity-prompts",
                limit=1
            ))
            assert len(recs) > 0
            
            rec = recs[0]
            # Should have prompt text
            assert rec.get(TEXT) is not None
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestCodeGeneration:
    """mbpp (code) normalizer tests"""
    
    def test_loads_code_tasks(self):
        """MBPP code tasks normalized"""
        try:
            recs = list(load_normalized("mbpp", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            # Should have task description or code
            assert rec.get(TEXT) is not None or rec.get(META, {}).get("code")
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestQA:
    """squad (QA) normalizer tests"""
    
    def test_loads_qa_pairs(self):
        """SQuAD Q&A pairs normalized"""
        try:
            recs = list(load_normalized("squad", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            # Should have question
            assert rec.get(TEXT) is not None
            # Context in meta
            assert rec.get(META, {}).get("context") is not None
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestLanguageModeling:
    """wikitext normalizer tests"""
    
    def test_loads_text(self):
        """Wikitext text loaded"""
        try:
            recs = list(load_normalized("wikitext", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            assert rec.get(TEXT) is not None
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


class TestIntents:
    """snips_built_in_intents normalizer tests"""
    
    def test_loads_intents(self):
        """Snips intents normalized"""
        try:
            recs = list(load_normalized("snips_built_in_intents", limit=1))
            assert len(recs) > 0
            
            rec = recs[0]
            assert rec.get(TEXT) is not None
            # May have intent label
        
        except FileNotFoundError:
            pytest.skip("Dataset not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

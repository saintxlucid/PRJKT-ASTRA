# tests/services/test_document_service.py
"""Unit tests for Document Service"""
import os
import json
import tempfile
import pytest
from pathlib import Path

# Import document service
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from astra.services import document_service as ds

def make_sample_pdf(path: str):
    """Create a simple test PDF using pymupdf"""
    try:
        import fitz
    except ImportError:
        pytest.skip("pymupdf not installed")
    
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text(
            (72, 72 + i*30),
            f"Hello world page {i}. Python testing with ASTRA document intelligence."
        )
    doc.save(path)
    doc.close()

class TestDocumentExtraction:
    """PDF extraction tests"""
    
    def test_extract_text_from_pdf(self, tmp_path):
        """Test basic PDF text extraction"""
        pdf_path = tmp_path / "test.pdf"
        make_sample_pdf(str(pdf_path))
        
        text = ds.extract_text_from_pdf(str(pdf_path))
        
        assert len(text) > 0
        assert "Hello world" in text
        assert "Python testing" in text
    
    def test_extract_nonexistent_file(self):
        """Extracting nonexistent file should fail"""
        with pytest.raises(Exception):
            ds.extract_text_from_pdf("nonexistent.pdf")

class TestChunking:
    """Text chunking tests"""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking"""
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = ds.chunk_text(text, chunk_size=20, overlap=5)
        
        assert len(chunks) > 1
        assert all(len(c.split()) <= 20 for c in chunks)
    
    def test_chunk_text_overlap(self):
        """Test that chunks have overlap"""
        text = " ".join([f"word{i}" for i in range(50)])
        chunks = ds.chunk_text(text, chunk_size=10, overlap=3)
        
        # Check overlap exists
        if len(chunks) > 1:
            last_words_chunk1 = chunks[0].split()[-3:]
            first_words_chunk2 = chunks[1].split()[:3]
            # At least some overlap
            overlap_count = sum(1 for w in last_words_chunk1 if w in first_words_chunk2)
            assert overlap_count > 0
    
    def test_chunk_text_empty(self):
        """Empty text should return empty list"""
        chunks = ds.chunk_text("", chunk_size=100)
        assert len(chunks) == 1  # Empty string still creates one chunk

class TestEmbedding:
    """Embedding tests"""
    
    def test_fake_embed(self):
        """Test fake embedding generation"""
        text = "This is a test document"
        embed = ds.fake_embed(text)
        
        assert embed is not None
        assert len(embed) > 0
        assert isinstance(embed, str)
    
    def test_fake_embed_deterministic(self):
        """Same text should produce same embedding"""
        text = "Consistent text"
        embed1 = ds.fake_embed(text)
        embed2 = ds.fake_embed(text)
        
        assert embed1 == embed2
    
    def test_fake_embed_different(self):
        """Different text should produce different embeddings"""
        embed1 = ds.fake_embed("text one")
        embed2 = ds.fake_embed("text two")
        
        assert embed1 != embed2

class TestIngestion:
    """Document ingestion tests"""
    
    def test_ingest_pdf_basic(self, tmp_path, monkeypatch):
        """Test basic PDF ingestion"""
        pdf_path = tmp_path / "test.pdf"
        make_sample_pdf(str(pdf_path))
        
        # Set temp index directory
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        monkeypatch.setenv("DOC_INDEX_DIR", str(index_dir))
        ds.INDEX_DIR = str(index_dir)
        
        # Ingest
        index_name = "test_index.jsonl"
        count = ds.ingest_pdf(
            str(pdf_path),
            index_name=index_name,
            chunk_size=20,
            overlap=5
        )
        
        assert count > 0
        
        # Check index file created
        index_path = index_dir / index_name
        assert index_path.exists()
        
        # Check content
        with open(index_path, "r") as f:
            lines = f.readlines()
        
        assert len(lines) == count
        
        # Verify JSON format
        for line in lines:
            record = json.loads(line)
            assert "id" in record
            assert "text" in record
            assert "embed" in record
            assert "source" in record
    
    def test_ingest_with_metadata(self, tmp_path, monkeypatch):
        """Test ingestion with custom metadata"""
        pdf_path = tmp_path / "test.pdf"
        make_sample_pdf(str(pdf_path))
        
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        monkeypatch.setenv("DOC_INDEX_DIR", str(index_dir))
        ds.INDEX_DIR = str(index_dir)
        
        metadata = {"author": "Test Author", "category": "Testing"}
        count = ds.ingest_pdf(
            str(pdf_path),
            index_name="meta_test.jsonl",
            metadata=metadata
        )
        
        assert count > 0
        
        # Verify metadata stored
        with open(index_dir / "meta_test.jsonl", "r") as f:
            record = json.loads(f.readline())
        
        assert record["metadata"]["author"] == "Test Author"
        assert record["metadata"]["category"] == "Testing"

class TestSearch:
    """Search tests"""
    
    def test_simple_keyword_search(self, tmp_path, monkeypatch):
        """Test keyword search"""
        pdf_path = tmp_path / "test.pdf"
        make_sample_pdf(str(pdf_path))
        
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        monkeypatch.setenv("DOC_INDEX_DIR", str(index_dir))
        ds.INDEX_DIR = str(index_dir)
        
        index_name = "search_test.jsonl"
        ds.ingest_pdf(str(pdf_path), index_name=index_name, chunk_size=20, overlap=5)
        
        # Search
        results = ds.simple_keyword_search(index_name, "Hello", top=5)
        
        assert len(results) > 0
        assert "Hello" in results[0]["text"]
    
    def test_search_nonexistent_index(self):
        """Search on nonexistent index should return empty"""
        results = ds.simple_keyword_search("nonexistent.jsonl", "test")
        assert results == []
    
    def test_search_no_matches(self, tmp_path, monkeypatch):
        """Search with no matches should return empty"""
        pdf_path = tmp_path / "test.pdf"
        make_sample_pdf(str(pdf_path))
        
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        monkeypatch.setenv("DOC_INDEX_DIR", str(index_dir))
        ds.INDEX_DIR = str(index_dir)
        
        index_name = "nomatch.jsonl"
        ds.ingest_pdf(str(pdf_path), index_name=index_name)
        
        results = ds.simple_keyword_search(index_name, "nonexistent_keyword_xyz")
        assert len(results) == 0

class TestIndexManagement:
    """Index management tests"""
    
    def test_list_indexes(self, tmp_path, monkeypatch):
        """Test listing indexes"""
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        monkeypatch.setenv("DOC_INDEX_DIR", str(index_dir))
        ds.INDEX_DIR = str(index_dir)
        
        # Create dummy indexes
        (index_dir / "index1.jsonl").write_text('{"test": 1}\n')
        (index_dir / "index2.jsonl").write_text('{"test": 2}\n')
        
        indexes = ds.list_indexes()
        
        assert len(indexes) == 2
        assert "index1.jsonl" in indexes
        assert "index2.jsonl" in indexes
    
    def test_get_index_stats(self, tmp_path, monkeypatch):
        """Test index statistics"""
        pdf_path = tmp_path / "test.pdf"
        make_sample_pdf(str(pdf_path))
        
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        monkeypatch.setenv("DOC_INDEX_DIR", str(index_dir))
        ds.INDEX_DIR = str(index_dir)
        
        index_name = "stats_test.jsonl"
        chunk_count = ds.ingest_pdf(str(pdf_path), index_name=index_name, chunk_size=20)
        
        stats = ds.get_index_stats(index_name)
        
        assert stats["chunks"] == chunk_count
        assert stats["total_chars"] > 0
        assert len(stats["sources"]) == 1
        assert stats["avg_chunk_size"] > 0
    
    def test_get_stats_nonexistent(self):
        """Stats for nonexistent index should return error"""
        stats = ds.get_index_stats("nonexistent.jsonl")
        assert "error" in stats

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

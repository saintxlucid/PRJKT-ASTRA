"""Tests for Windows auto-ingestion service."""
import os
import time
import shutil
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
import win32serviceutil

from astra.service.ingest import (
    DocumentProcessor,
    IngestHandler,
    MaintenanceTask,
    ASTRAIngestService
)
from astra.rag.documents import Document
from astra.parse.pdf import PDFChunk, BoundingBox

@pytest.fixture
def test_dirs(tmp_path):
    """Create test directories."""
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    inbox.mkdir()
    processed.mkdir()
    return inbox, processed

@pytest.fixture
def mock_index():
    """Create mock dense index."""
    index = Mock()
    index.get_metrics.return_value = {"docs_indexed": 0}
    return index

@pytest.fixture
def mock_parser():
    """Create mock PDF parser."""
    parser = Mock()
    parser.parse_pdf.return_value = [
        PDFChunk(
            text="Test content",
            bbox=BoundingBox(0, 0, 100, 100, 1)
        )
    ]
    return parser

@pytest.fixture
def mock_chunker():
    """Create mock chunker."""
    return Mock()

@pytest.fixture
def mock_event_logger():
    """Create mock event logger."""
    return Mock()

@pytest.fixture
def processor(
    mock_index,
    mock_parser,
    mock_chunker,
    mock_event_logger,
    test_dirs
):
    """Create document processor."""
    _, processed = test_dirs
    return DocumentProcessor(
        index=mock_index,
        parser=mock_parser,
        chunker=mock_chunker,
        event_logger=mock_event_logger,
        processed_dir=str(processed)
    )

def create_test_pdf(path: Path) -> None:
    """Create dummy PDF file."""
    path.write_bytes(b"%PDF-1.4\n%EOF")  # Minimal valid PDF

def test_processor_init(processor, test_dirs):
    """Test processor initialization."""
    _, processed = test_dirs
    assert Path(processor.processed_dir) == processed
    assert processed.exists()

def test_process_pdf(processor, test_dirs):
    """Test PDF processing."""
    inbox, _ = test_dirs
    pdf_path = inbox / "test.pdf"
    create_test_pdf(pdf_path)
    
    # Process file
    result = processor.process_file(str(pdf_path))
    assert result is True
    
    # Verify processing
    assert not pdf_path.exists()  # Should be moved
    assert (Path(processor.processed_dir) / "test.pdf").exists()
    processor.index.index_documents.assert_called_once()
    processor.event_logger.emit.assert_called_with(
        "ingestion.complete",
        file="test.pdf",
        chunks=1
    )

def test_skip_non_pdf(processor, test_dirs):
    """Test non-PDF handling."""
    inbox, _ = test_dirs
    txt_path = inbox / "test.txt"
    txt_path.write_text("test")
    
    result = processor.process_file(str(txt_path))
    assert result is False
    assert txt_path.exists()  # Should not be moved
    processor.index.index_documents.assert_not_called()

def test_handle_extraction_failure(processor, test_dirs):
    """Test handling of extraction failures."""
    inbox, _ = test_dirs
    pdf_path = inbox / "bad.pdf"
    create_test_pdf(pdf_path)
    
    # Make parser fail
    processor.parser.parse_pdf.side_effect = Exception("Parse failed")
    
    result = processor.process_file(str(pdf_path))
    assert result is False
    assert pdf_path.exists()  # Should not be moved
    processor.index.index_documents.assert_not_called()

def test_ingest_handler(processor, test_dirs):
    """Test file system event handling."""
    inbox, _ = test_dirs
    handler = IngestHandler(processor)
    
    # Create test file
    pdf_path = inbox / "test.pdf"
    create_test_pdf(pdf_path)
    
    # Simulate file creation event
    event = Mock()
    event.is_directory = False
    event.src_path = str(pdf_path)
    
    handler.on_created(event)
    time.sleep(1.5)  # Wait for processing
    
    assert not pdf_path.exists()  # Should be moved
    processor.index.index_documents.assert_called_once()

def test_maintenance_task(mock_event_logger):
    """Test maintenance operations."""
    store = Mock()
    task = MaintenanceTask(
        store=store,
        event_logger=mock_event_logger,
        vacuum_interval=1,
        cache_cleanup_interval=1
    )
    
    # Run maintenance
    task.run()
    store.vacuum.assert_called_once()
    mock_event_logger.emit.assert_called_with(
        "maintenance.vacuum_complete"
    )
    
    # Run again immediately - should not vacuum
    store.reset_mock()
    mock_event_logger.reset_mock()
    task.run()
    store.vacuum.assert_not_called()

@patch('win32serviceutil.ServiceFramework.__init__')
def test_service_initialization(mock_init):
    """Test service initialization."""
    service = ASTRAIngestService(None)
    assert service._svc_name_ == "ASTRAIngest"
    assert not service.running
    
    # Test internal initialization
    with patch.object(service, '_initialize') as mock_init:
        mock_init.return_value = True
        service.SvcDoRun()
        mock_init.assert_called_once()

@patch('win32serviceutil.ServiceFramework.__init__')
def test_service_shutdown(mock_init):
    """Test service shutdown."""
    service = ASTRAIngestService(None)
    
    # Start then stop
    with patch.object(service, '_initialize') as mock_init:
        mock_init.return_value = True
        
        def stop_service():
            time.sleep(0.5)
            service.SvcStop()
            
        import threading
        threading.Thread(target=stop_service).start()
        
        service.SvcDoRun()
        assert not service.running
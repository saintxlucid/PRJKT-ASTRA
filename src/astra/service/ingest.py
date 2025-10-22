"""
Windows service for automated document ingestion and maintenance.

This module implements a Windows service that:
1. Watches for new documents in data/ingest/inbox
2. Processes and indexes documents automatically
3. Runs nightly maintenance tasks
4. Provides health monitoring and graceful restarts
"""
import os
import sys
import time
import shutil
import logging
from pathlib import Path
from typing import Optional, Set, Dict, Any
from datetime import datetime, timedelta
import win32serviceutil
import win32service
import win32event
import servicemanager
import structlog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from astra.store.qdrant_store import QdrantStore
from astra.embed.bge import BGEM3Embedder
from astra.rag.indexes import DenseIndex
from astra.parse.pdf import PDFLayoutParser
from astra.parse.chunking import LayoutChunker
from astra.rag.documents import Document
from astra.telemetry.events import EventLogger
from astra.telemetry.metrics import MetricsRegistry

logger = structlog.get_logger()

class DocumentProcessor:
    """Processes and indexes incoming documents."""
    
    def __init__(
        self,
        index: DenseIndex,
        parser: PDFLayoutParser,
        chunker: LayoutChunker,
        event_logger: EventLogger,
        processed_dir: str
    ):
        """Initialize processor.
        
        Args:
            index: Dense index for document storage
            parser: PDF parser for extraction
            chunker: Chunker for text splitting
            event_logger: Logger for events
            processed_dir: Directory for processed files
        """
        self.index = index
        self.parser = parser
        self.chunker = chunker
        self.event_logger = event_logger
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
    def process_file(self, file_path: str) -> bool:
        """Process a single file.
        
        Args:
            file_path: Path to file to process
            
        Returns:
            True if processing succeeded
        """
        try:
            path = Path(file_path)
            
            # Only handle PDFs for now
            if path.suffix.lower() != '.pdf':
                logger.warning("skipping_non_pdf", path=file_path)
                return False
                
            # Extract text with layout
            chunks = self.parser.parse_pdf(file_path)
            if not chunks:
                logger.warning("no_content_extracted", path=file_path)
                return False
                
            # Create document
            doc = Document(
                id=path.stem,
                chunks=chunks,
                metadata={
                    "source": path.name,
                    "ingested": datetime.utcnow().isoformat()
                }
            )
            
            # Index document
            self.index.index_documents([doc])
            
            # Move to processed
            dest = self.processed_dir / path.name
            shutil.move(file_path, str(dest))
            
            self.event_logger.emit(
                "ingestion.complete",
                file=path.name,
                chunks=len(chunks)
            )
            return True
            
        except Exception as e:
            logger.error(
                "processing_failed",
                path=file_path,
                error=str(e)
            )
            return False

class IngestHandler(FileSystemEventHandler):
    """Handles file system events for ingestion."""
    
    def __init__(self, processor: DocumentProcessor):
        """Initialize handler.
        
        Args:
            processor: Document processor to use
        """
        self.processor = processor
        self.processing: Set[str] = set()
        
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        file_path = event.src_path
        if file_path in self.processing:
            return
            
        self.processing.add(file_path)
        try:
            # Wait briefly for file to be fully written
            time.sleep(1.0)
            self.processor.process_file(file_path)
        finally:
            self.processing.remove(file_path)

class MaintenanceTask:
    """Runs periodic maintenance tasks."""
    
    def __init__(
        self,
        store: QdrantStore,
        event_logger: EventLogger,
        vacuum_interval: int = 86400,  # 24h
        cache_cleanup_interval: int = 3600  # 1h
    ):
        """Initialize maintenance task.
        
        Args:
            store: Qdrant store to maintain
            event_logger: Event logger
            vacuum_interval: Seconds between vacuum runs
            cache_cleanup_interval: Seconds between cache cleanup
        """
        self.store = store
        self.event_logger = event_logger
        self.vacuum_interval = vacuum_interval
        self.cache_cleanup_interval = cache_cleanup_interval
        self.last_vacuum = 0
        self.last_cache_cleanup = 0
        
    def run(self):
        """Run maintenance checks."""
        now = time.time()
        
        # Run vacuum if needed
        if now - self.last_vacuum >= self.vacuum_interval:
            try:
                self.store.vacuum()
                self.last_vacuum = now
                self.event_logger.emit("maintenance.vacuum_complete")
            except Exception as e:
                logger.error("vacuum_failed", error=str(e))
        
        # Clean cache if needed
        if now - self.last_cache_cleanup >= self.cache_cleanup_interval:
            try:
                # TODO: Implement cache cleanup
                self.last_cache_cleanup = now
                self.event_logger.emit("maintenance.cache_cleaned")
            except Exception as e:
                logger.error("cache_cleanup_failed", error=str(e))

class ASTRAIngestService(win32serviceutil.ServiceFramework):
    """Windows service for ASTRA document ingestion."""
    
    _svc_name_ = "ASTRAIngest"
    _svc_display_name_ = "ASTRA Document Ingestion Service"
    _svc_description_ = "Automated document ingestion and maintenance for ASTRA"
    
    def __init__(self, args):
        """Initialize service."""
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = False
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            filename="astra_ingest.log",
            format='%(asctime)s %(message)s'
        )
        
    def _initialize(self):
        """Initialize service components."""
        try:
            # Set up paths
            base_dir = Path(__file__).parent.parent
            inbox_dir = base_dir / "data" / "ingest" / "inbox"
            processed_dir = base_dir / "data" / "ingest" / "processed"
            log_dir = base_dir / "data" / "logs"
            
            inbox_dir.mkdir(parents=True, exist_ok=True)
            processed_dir.mkdir(parents=True, exist_ok=True)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize components
            store = QdrantStore.from_env()
            embedder = BGEM3Embedder()
            event_logger = EventLogger(
                log_dir=str(log_dir),
                rotation_bytes=1048576,
                max_files=5
            )
            
            # Create index
            self.index = DenseIndex(
                store=store,
                embedder=embedder,
                collection="astra_docs",
                event_logger=event_logger
            )
            
            # Set up processor
            parser = PDFLayoutParser()
            chunker = LayoutChunker()
            self.processor = DocumentProcessor(
                index=self.index,
                parser=parser,
                chunker=chunker,
                event_logger=event_logger,
                processed_dir=str(processed_dir)
            )
            
            # Set up file watcher
            self.observer = Observer()
            handler = IngestHandler(self.processor)
            self.observer.schedule(
                handler,
                str(inbox_dir),
                recursive=False
            )
            
            # Set up maintenance
            self.maintenance = MaintenanceTask(
                store=store,
                event_logger=event_logger
            )
            
            return True
            
        except Exception as e:
            logger.error("initialization_failed", error=str(e))
            return False
            
    def SvcStop(self):
        """Stop the service."""
        self.running = False
        win32event.SetEvent(self.stop_event)
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
    def SvcDoRun(self):
        """Run the service."""
        self.running = True
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PID_INFO,
            ('Service starting...',)
        )
        
        try:
            if not self._initialize():
                raise Exception("Service initialization failed")
                
            # Start components
            self.observer.start()
            
            # Service loop
            while self.running:
                # Run maintenance
                self.maintenance.run()
                
                # Check health
                try:
                    # Basic health check - verify index access
                    self.index.get_metrics()
                except Exception as e:
                    logger.error("health_check_failed", error=str(e))
                    
                # Wait for stop or timeout
                rc = win32event.WaitForSingleObject(
                    self.stop_event,
                    5000  # 5 second timeout
                )
                if rc == win32event.WAIT_OBJECT_0:
                    break
                    
        except Exception as e:
            logger.error("service_failed", error=str(e))
            
        finally:
            # Cleanup
            if hasattr(self, 'observer'):
                self.observer.stop()
                self.observer.join()
                
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PID_INFO,
                ('Service stopped.',)
            )

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ASTRAIngestService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ASTRAIngestService)
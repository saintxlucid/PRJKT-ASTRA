"""
Distributed Ingestion Service

This service handles document ingestion in a distributed environment using PostgreSQL
for persistent storage and Redis for caching. It's designed to run in containers
and scale horizontally.

Key Features:
- Containerized service with PostgreSQL and Redis support
- Distributed file monitoring
- Scalable document processing
- Robust error handling and recovery
- Metrics and telemetry for monitoring
"""
import os
import yaml
import json
import shutil
import hashlib
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import structlog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from astra.core.pipeline import IngestionPipeline
from astra.rag.telemetry import TelemetryEmitter
from astra.service.database import db_manager

# Configure logging
logger = structlog.get_logger(__name__)

# Environment-aware paths
DATA_ROOT = Path(os.getenv('ASTRA_DATA', '/data'))
CONFIG_PATH = Path(os.getenv('ASTRA_CONFIG', '/app/config/rag.yaml'))

# Data directories
INBOX_DIR = DATA_ROOT / "ingest/inbox"
PROCESSED_DIR = DATA_ROOT / "ingest/processed"
FAILED_DIR = DATA_ROOT / "ingest/failed"
LOG_DIR = DATA_ROOT / "logs"
TELEMETRY_DIR = DATA_ROOT / "telemetry"

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

class DistributedIngestionHandler(FileSystemEventHandler):
    """Handles file system events with distributed storage support."""

    def __init__(self, pipeline: Optional[IngestionPipeline] = None):
        """Initialize handler with optional pipeline."""
        self.pipeline = None
        self.init_pipeline(pipeline)
        self.telemetry = TelemetryEmitter(output_dir=str(TELEMETRY_DIR))

    def init_pipeline(self, pipeline: Optional[IngestionPipeline] = None):
        """Initialize or reinitialize the pipeline."""
        try:
            self.pipeline = pipeline or IngestionPipeline.from_config(str(CONFIG_PATH))
            logger.info("pipeline_initialized")
            return True
        except Exception as e:
            logger.error("pipeline_init_failed", error=str(e))
            return False

    async def validate_file(self, file_path: Path) -> bool:
        """Validate file before processing."""
        try:
            if not file_path.is_file():
                logger.warning("not_a_file", path=str(file_path))
                return False
                
            if file_path.suffix.lower() not in ['.pdf', '.txt', '.md']:
                logger.warning("unsupported_file_type", 
                             path=str(file_path), 
                             suffix=file_path.suffix)
                return False
                
            if file_path.stat().st_size == 0:
                logger.warning("empty_file", path=str(file_path))
                return False

            # Check if file is already processed
            content_hash = compute_file_hash(file_path)
            status = await db_manager.get_document_status(content_hash)
            if status and status['processing_status'] == 'completed':
                logger.info("file_already_processed", 
                           path=str(file_path),
                           hash=content_hash)
                return False
                
            return True
            
        except Exception as e:
            logger.error("file_validation_failed", 
                        path=str(file_path), 
                        error=str(e))
            return False

    async def move_to_failed(self, file_path: Path, error: Optional[str] = None):
        """Move failed file to failed directory."""
        try:
            destination = FAILED_DIR / file_path.name
            shutil.move(str(file_path), str(destination))
            logger.info("moved_to_failed", 
                       source=str(file_path),
                       destination=str(destination))
            
            if error:
                # Write error details to accompanying .error file
                error_file = destination.with_suffix(destination.suffix + '.error')
                error_file.write_text(error)
                
            # Record failure in database
            await db_manager.record_ingestion_event(
                event_type="file.failed",
                file_path=str(file_path),
                status="failed",
                error_message=error
            )
                
        except Exception as e:
            logger.error("failed_to_move_failed_file",
                        source=str(file_path),
                        error=str(e))

    async def on_created(self, event):
        """Handle new file creation event."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        logger.info("new_file_detected", path=str(file_path))
        
        # Record ingestion start
        await db_manager.record_ingestion_event(
            event_type="ingestion.start",
            file_path=str(file_path),
            status="started"
        )

        # Validate file
        if not await self.validate_file(file_path):
            await self.move_to_failed(file_path, "File validation failed")
            return

        try:
            # Ensure pipeline is initialized
            if not self.pipeline and not self.init_pipeline():
                raise RuntimeError("Pipeline initialization failed")

            # Compute file hash
            content_hash = compute_file_hash(file_path)
            
            # Create document metadata record
            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size': file_path.stat().st_size,
                'content_hash': content_hash,
                'processing_status': 'processing'
            }
            
            # Run the ingestion pipeline
            await self.pipeline.run_async(file_path)

            # Move the processed file
            destination = PROCESSED_DIR / file_path.name
            shutil.move(str(file_path), str(destination))
            
            # Update document status
            metadata['processing_status'] = 'completed'
            await db_manager.record_ingestion_event(
                event_type="ingestion.complete",
                file_path=str(file_path),
                status="completed",
                metadata=metadata
            )
            
            logger.info("file_processed_and_moved", 
                       destination=str(destination),
                       hash=content_hash)

        except Exception as e:
            error_msg = str(e)
            logger.error("ingestion_failed", 
                        path=str(file_path), 
                        error=error_msg)
            await self.move_to_failed(file_path, error_msg)

async def run_maintenance():
    """Run maintenance tasks."""
    logger.info("running_maintenance")
    try:
        # Clean up failed directory
        cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
        async with db_manager.pg_pool.acquire() as conn:
            # Get list of old failed files
            rows = await conn.fetch("""
                SELECT file_path 
                FROM ingestion_events 
                WHERE status = 'failed' 
                AND timestamp < $1
            """, cutoff)
            
            # Remove old failed files
            for row in rows:
                file_path = Path(row['file_path'])
                if file_path.exists():
                    file_path.unlink()
                    
            # Clean up old records
            await conn.execute("""
                DELETE FROM ingestion_events 
                WHERE status = 'failed' 
                AND timestamp < $1
            """, cutoff)
            
        logger.info("maintenance_complete")
        
    except Exception as e:
        logger.error("maintenance_failed", error=str(e))

async def process_existing_files(handler: DistributedIngestionHandler):
    """Process any existing files in the inbox."""
    for file_path in INBOX_DIR.glob('*.*'):
        if await handler.validate_file(file_path):
            await handler.on_created(
                type('Event', (), {
                    'is_directory': False,
                    'src_path': str(file_path)
                })
            )

async def verify_environment():
    """Verify and setup the environment."""
    try:
        # Ensure config exists
        if not CONFIG_PATH.exists():
            raise RuntimeError(f"Configuration file not found: {CONFIG_PATH}")

        # Create required directories
        for directory in [INBOX_DIR, PROCESSED_DIR, FAILED_DIR, 
                         LOG_DIR, TELEMETRY_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

        # Initialize databases
        if not await db_manager.initialize():
            raise RuntimeError("Database initialization failed")

        # Test pipeline initialization
        test_pipeline = IngestionPipeline.from_config(str(CONFIG_PATH))
        if not test_pipeline:
            raise RuntimeError("Failed to initialize test pipeline")

        return True

    except Exception as e:
        logger.error("environment_verification_failed", error=str(e))
        return False

async def async_main():
    """Async main function to start the ingestion service."""
    logger.info("starting_distributed_ingestion_service")
    
    # Verify environment
    if not await verify_environment():
        logger.error("service_startup_failed")
        return

    # Initialize the ingestion pipeline
    try:
        pipeline = IngestionPipeline.from_config(str(CONFIG_PATH))
    except Exception as e:
        logger.error("pipeline_initialization_failed", error=str(e))
        return

    # Set up the watchdog observer
    event_handler = DistributedIngestionHandler(pipeline)
    observer = Observer()
    observer.schedule(event_handler, str(INBOX_DIR), recursive=False)

    try:
        # Start the observer
        observer.start()
        logger.info("file_watcher_started", directory=str(INBOX_DIR))

        # Process existing files
        await process_existing_files(event_handler)

        # Main service loop
        while True:
            # Run maintenance every hour
            await run_maintenance()
            await asyncio.sleep(3600)  # Sleep for 1 hour

    except asyncio.CancelledError:
        logger.info("received_shutdown_signal")
    except Exception as e:
        logger.error("service_critical_error", error=str(e))
    finally:
        # Cleanup
        observer.stop()
        observer.join()
        await db_manager.close()
        logger.info("service_shutdown_complete")

def main():
    """Synchronous entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
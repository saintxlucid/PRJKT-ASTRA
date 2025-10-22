"""
Windows Auto-Ingestion Service

This service monitors a directory for new files and automatically processes them
through the ASTRA ingestion pipeline.

Key Features:
- Watches a directory for new files.
- Parses, embeds, and upserts documents into the dense index.
- Moves processed files to a 'processed' directory.
- Emits 'ingestion.complete' events.
- Includes nightly maintenance tasks.
"""
import yaml
import json
import shutil
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
import logging
import structlog

ASTRA_ROOT = Path("x:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)")
LOG_DIR = ASTRA_ROOT / "data/logs"
LOG_FILE = LOG_DIR / "ingestion.log"
EVENT_FILE = LOG_DIR / "events.jsonl"

def setup_logging():
    """Set up logging directories and configure structlog."""
    try:
        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created/verified log directory: {LOG_DIR}")
        
        # Create log files if they don't exist
        if not LOG_FILE.exists():
            LOG_FILE.touch()
            print(f"Created log file: {LOG_FILE}")
        if not EVENT_FILE.exists():
            EVENT_FILE.touch()
            print(f"Created event file: {EVENT_FILE}")
        
        # Configure structlog with console and file output
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            logger_factory=structlog.PrintLoggerFactory(),
        )
        
        # Add a file handler to the root logger
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()  # Also log to console
            ]
        )
        
        print("Logging system initialized successfully")
        
    except Exception as e:
        print(f"Error setting up logging: {e}")

def emit_event(event_type: str, details: Optional[Dict[str, Any]] = None):
    """Emit an event to the events.jsonl file."""
    event = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "type": event_type,
        **(details or {})
    }
    
    with EVENT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
import time
import schedule
import structlog
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from astra.core.pipeline import IngestionPipeline
from astra.rag.telemetry import TelemetryEmitter

# Initialize telemetry
telemetry = TelemetryEmitter(output_dir=str(ASTRA_ROOT / "data/telemetry"))

# Configure logging
logger = structlog.get_logger(__name__)

# Initialize thread pool for async operations
thread_pool = ThreadPoolExecutor(max_workers=2)  # Limit concurrent processing

# --- Configuration ---
INBOX_DIR = ASTRA_ROOT / "data/ingest/inbox"
PROCESSED_DIR = ASTRA_ROOT / "data/ingest/processed"
FAILED_DIR = ASTRA_ROOT / "data/ingest/failed"
CONFIG_PATH = ASTRA_ROOT / "config/rag.yaml"
POLL_INTERVAL_S = 10

class IngestionHandler(FileSystemEventHandler):
    """Handles file system events for new documents."""

    def __init__(self, pipeline: Optional[IngestionPipeline] = None):
        """Initialize handler with optional pipeline."""
        self.pipeline = None
        self.init_pipeline(pipeline)

    def init_pipeline(self, pipeline: Optional[IngestionPipeline] = None):
        """Initialize or reinitialize the pipeline."""
        try:
            self.pipeline = pipeline or IngestionPipeline.from_config(str(CONFIG_PATH))
            logger.info("pipeline_initialized")
            return True
        except Exception as e:
            logger.error("pipeline_init_failed", error=str(e))
            return False

    def validate_file(self, file_path: Path) -> bool:
        """Validate file before processing."""
        try:
            if not file_path.is_file():
                logger.warning("not_a_file", path=str(file_path))
                return False
                
            if file_path.suffix.lower() != '.pdf':
                logger.warning("unsupported_file_type", 
                             path=str(file_path), 
                             suffix=file_path.suffix)
                return False
                
            if file_path.stat().st_size == 0:
                logger.warning("empty_file", path=str(file_path))
                return False
                
            return True
            
        except Exception as e:
            logger.error("file_validation_failed", 
                        path=str(file_path), 
                        error=str(e))
            return False

    def move_to_failed(self, file_path: Path, error: Optional[str] = None):
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
                
        except Exception as e:
            logger.error("failed_to_move_failed_file",
                        source=str(file_path),
                        error=str(e))

    def on_created(self, event):
        """
        Triggered when a new file is created in the inbox.
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        logger.info("new_file_detected", path=str(file_path))
        emit_event("ingestion.start", {"file": str(file_path)})

        # Validate file first
        if not self.validate_file(file_path):
            self.move_to_failed(file_path, "File validation failed")
            emit_event("ingestion.error", {
                "file": str(file_path),
                "error": "File validation failed"
            })
            return

        try:
            # Ensure pipeline is initialized
            if not self.pipeline and not self.init_pipeline():
                raise RuntimeError("Pipeline initialization failed")

            # Run the ingestion pipeline
            self.pipeline.run(file_path)

            # Move the processed file
            destination = PROCESSED_DIR / file_path.name
            shutil.move(str(file_path), str(destination))
            logger.info("file_processed_and_moved", destination=str(destination))
            
            emit_event("ingestion.complete", {
                "file": str(file_path),
                "destination": str(destination)
            })

        except Exception as e:
            error_msg = str(e)
            logger.error("ingestion_failed", path=str(file_path), error=error_msg)
            self.move_to_failed(file_path, error_msg)
            emit_event("ingestion.error", {
                "file": str(file_path),
                "error": error_msg
            })

async def run_nightly_maintenance(pipeline: IngestionPipeline):
    """
    Runs nightly maintenance tasks, such as VACUUM and cache cleanup.
    """
    logger.info("running_nightly_maintenance")
    try:
        # Maintenance tasks
        tasks = []
        
        # 1. Clean up failed dir - remove files older than 7 days
        logger.debug("cleaning_failed_directory")
        cutoff = time.time() - (7 * 24 * 60 * 60)  # 7 days ago
        try:
            for f in FAILED_DIR.glob("*"):
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    tasks.append(f"removed_old_failed:{f.name}")
        except Exception as e:
            logger.error("failed_dir_cleanup_error", error=str(e))

        # 2. Vacuum index if supported
        logger.debug("vacuuming_index")
        try:
            # This will be a no-op for indexes that don't support vacuum
            if hasattr(pipeline.index, "vacuum"):
                await pipeline.index.vacuum()
                tasks.append("vacuum_index")
        except Exception as e:
            logger.error("index_vacuum_error", error=str(e))

        # 3. Clean up embedding cache
        logger.debug("cleaning_cache")
        try:
            cache_dir = Path("data/cache")
            if cache_dir.exists():
                # Remove files older than 30 days
                cutoff = time.time() - (30 * 24 * 60 * 60)
                for f in cache_dir.glob("**/*"):
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        f.unlink()
                        tasks.append(f"removed_old_cache:{f.name}")
        except Exception as e:
            logger.error("cache_cleanup_error", error=str(e))

        # Record maintenance completion
        telemetry.emit("maintenance.complete", {"tasks": tasks})
        logger.info("nightly_maintenance_complete", tasks=tasks)

    except Exception as e:
        logger.error("nightly_maintenance_failed", error=str(e))
        telemetry.emit("maintenance.failed", {"error": str(e)})

def verify_environment():
    """Verify and setup the environment."""
    try:
        # Ensure config exists
        if not CONFIG_PATH.exists():
            raise RuntimeError(f"Configuration file not found: {CONFIG_PATH}")

        # Ensure all required directories exist
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Verify configuration
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            if not config:
                raise RuntimeError("Empty configuration file")

        # Test pipeline initialization
        test_pipeline = IngestionPipeline.from_config(str(CONFIG_PATH))
        if not test_pipeline:
            raise RuntimeError("Failed to initialize test pipeline")

        return True

    except Exception as e:
        logger.error("environment_verification_failed", error=str(e))
        return False

async def process_existing_files(event_handler: IngestionHandler):
    """Process any existing files in the inbox directory."""
    for existing_file in INBOX_DIR.glob('*.pdf'):
        logger.info("processing_existing_file", file=str(existing_file))
        await event_handler.on_created(
            type('Event', (), {
                'is_directory': False, 
                'src_path': str(existing_file)
            })
        )

async def maintenance_scheduler(pipeline: IngestionPipeline):
    """Run scheduled maintenance tasks."""
    while True:
        try:
            # Run maintenance at 1 AM
            now = datetime.datetime.now()
            next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + datetime.timedelta(days=1)
            
            # Sleep until next maintenance window
            delay = (next_run - now).total_seconds()
            await asyncio.sleep(delay)
            
            # Run maintenance
            await run_nightly_maintenance(pipeline)
            
        except Exception as e:
            logger.error("maintenance_scheduler_error", error=str(e))
            await asyncio.sleep(60)  # Retry in 1 minute

async def async_main():
    """
    Async main function to start the ingestion service.
    """
    # Set up logging first
    setup_logging()
    logger.info("starting_windows_auto_ingestion_service")
    emit_event("service.start")

    # Verify environment
    if not verify_environment():
        logger.error("service_startup_failed")
        emit_event("service.startup.failed")
        return

    # Initialize the ingestion pipeline
    try:
        pipeline = IngestionPipeline.from_config(str(CONFIG_PATH))
    except Exception as e:
        logger.error("pipeline_initialization_failed", error=str(e))
        emit_event("service.startup.failed", {"error": str(e)})
        return

    # Set up the watchdog file observer
    event_handler = IngestionHandler(pipeline)
    observer = Observer()
    observer.schedule(event_handler, str(INBOX_DIR), recursive=False)

    try:
        # Start the observer
        observer.start()
        logger.info("file_watcher_started", directory=str(INBOX_DIR))
        emit_event("service.watcher.started", {"directory": str(INBOX_DIR)})

        # Process existing files
        await process_existing_files(event_handler)

        # Start maintenance scheduler
        maintenance_task = asyncio.create_task(
            maintenance_scheduler(pipeline)
        )

        # Main service loop - keep alive and handle signals
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("received_shutdown_signal")
        emit_event("service.shutdown.initiated")
    except Exception as e:
        logger.error("service_critical_error", error=str(e))
        emit_event("service.critical_error", {"error": str(e)})
    finally:
        # Cleanup
        if 'maintenance_task' in locals():
            maintenance_task.cancel()
        observer.stop()
        observer.join()
        thread_pool.shutdown(wait=True)
        logger.info("shutting_down_ingestion_service")
        emit_event("service.shutdown.complete")

def main():
    """
    Synchronous entry point that runs the async main.
    """
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass  # Handle gracefully

if __name__ == "__main__":
    main()

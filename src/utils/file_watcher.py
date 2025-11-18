"""File system watcher for automatic document indexing."""

import logging
import time
from pathlib import Path
from typing import Set

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from src.ingestion.ingestor import DocumentIngestor
from src.utils.config import get_settings

logger = logging.getLogger(__name__)


class DocumentWatcher(FileSystemEventHandler):
    """Watch directories for file changes and trigger indexing."""

    def __init__(self, ingestor: DocumentIngestor, debounce_delay: int = 2):
        """Initialize document watcher.

        Args:
            ingestor: Document ingestor instance
            debounce_delay: Delay in seconds before processing changes
        """
        super().__init__()
        self.ingestor = ingestor
        self.debounce_delay = debounce_delay
        self.pending_files: Set[str] = set()
        self.last_change_time = 0

    def on_created(self, event: FileSystemEvent):
        """Handle file creation event."""
        if event.is_directory:
            return

        logger.info(f"File created: {event.src_path}")
        self._queue_file(event.src_path)

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification event."""
        if event.is_directory:
            return

        logger.info(f"File modified: {event.src_path}")
        self._queue_file(event.src_path)

    def on_moved(self, event: FileSystemEvent):
        """Handle file move event."""
        if event.is_directory:
            return

        logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
        # Remove old path from index
        # TODO: Implement deletion from index

        # Add new path
        self._queue_file(event.dest_path)

    def _queue_file(self, filepath: str):
        """Queue a file for processing.

        Args:
            filepath: Path to file
        """
        path = Path(filepath)

        # Check if file type is supported
        ext = path.suffix.lower()
        settings = get_settings()

        if ext not in settings.ingestion.supported_extensions:
            logger.debug(f"Skipping unsupported file type: {ext}")
            return

        # Check ignore patterns
        for pattern in settings.ingestion.ignore_patterns:
            if path.match(pattern):
                logger.debug(f"Skipping ignored file: {filepath}")
                return

        # Add to pending files
        self.pending_files.add(str(path.absolute()))
        self.last_change_time = time.time()

    def process_pending_files(self):
        """Process all pending files if debounce delay has passed."""
        if not self.pending_files:
            return

        # Check if debounce delay has passed
        time_since_change = time.time() - self.last_change_time
        if time_since_change < self.debounce_delay:
            return

        logger.info(f"Processing {len(self.pending_files)} pending files")

        # Convert to Path objects
        files = [Path(fp) for fp in self.pending_files]

        # Process files
        try:
            self.ingestor.ingest_files(files, show_progress=False)
            logger.info(f"✓ Processed {len(files)} files")
        except Exception as e:
            logger.error(f"Error processing files: {e}")

        # Clear pending files
        self.pending_files.clear()


class FileWatcherService:
    """Service to manage file watching."""

    def __init__(self, directories: list = None):
        """Initialize file watcher service.

        Args:
            directories: List of directories to watch (default: from config)
        """
        self.settings = get_settings()
        self.directories = directories or self.settings.ingestion.watch_directories
        self.ingestor = DocumentIngestor(
            parallel_workers=self.settings.ingestion.parallel_workers
        )
        self.event_handler = DocumentWatcher(
            ingestor=self.ingestor,
            debounce_delay=self.settings.file_watcher.debounce_delay,
        )
        self.observer = Observer()
        self.is_running = False

    def start(self):
        """Start watching directories."""
        if not self.settings.file_watcher.enabled:
            logger.info("File watcher is disabled in config")
            return

        logger.info("Starting file watcher service")

        # Schedule observers for each directory
        for directory in self.directories:
            dir_path = Path(directory)

            if not dir_path.exists():
                logger.warning(f"Watch directory does not exist: {directory}")
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")

            logger.info(f"Watching directory: {directory}")
            self.observer.schedule(
                self.event_handler, str(dir_path), recursive=True
            )

        # Start observer
        self.observer.start()
        self.is_running = True

        logger.info("✓ File watcher started")

        try:
            # Main loop - check for pending files periodically
            while self.is_running:
                time.sleep(1)
                self.event_handler.process_pending_files()

        except KeyboardInterrupt:
            logger.info("Stopping file watcher (keyboard interrupt)")
            self.stop()

    def stop(self):
        """Stop watching directories."""
        logger.info("Stopping file watcher service")
        self.is_running = False
        self.observer.stop()
        self.observer.join()
        logger.info("✓ File watcher stopped")


def run_file_watcher(directories: list = None):
    """Run the file watcher service.

    Args:
        directories: List of directories to watch (default: from config)
    """
    service = FileWatcherService(directories=directories)
    service.start()


if __name__ == "__main__":
    # Command-line interface for file watcher
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Watch directories for file changes and auto-index"
    )
    parser.add_argument(
        "directories",
        nargs="*",
        help="Directories to watch (default: from config)",
    )

    args = parser.parse_args()

    # Initialize database
    from src.models.database import db_manager

    db_manager.initialize()

    # Run file watcher
    logger.info("Starting Life DB File Watcher")
    run_file_watcher(directories=args.directories if args.directories else None)

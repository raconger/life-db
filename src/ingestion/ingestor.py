"""Main ingestion system for processing and indexing documents."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional

from tqdm import tqdm

from src.ingestion.converters import DocumentConverter
from src.ingestion.email_parser import EmailParser
from src.ingestion.ocr_processor import OCRProcessor
from src.indexing.indexer import Indexer
from src.models.database import db_manager
from src.utils.config import get_settings

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """Main document ingestion pipeline."""

    def __init__(self, parallel_workers: int = 4):
        """Initialize document ingestor.

        Args:
            parallel_workers: Number of parallel workers for processing
        """
        self.settings = get_settings()
        self.parallel_workers = parallel_workers

        # Initialize processors
        self.doc_converter = DocumentConverter()
        self.email_parser = EmailParser()
        self.ocr_processor = OCRProcessor(
            languages=self.settings.ocr.languages,
            use_gpu=self.settings.ocr.gpu,
            min_confidence=self.settings.ocr.min_confidence,
        )

        # Statistics
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "by_type": {},
        }

    def discover_files(
        self, directories: List[str], extensions: Optional[List[str]] = None
    ) -> List[Path]:
        """Discover files to process in directories.

        Args:
            directories: List of directory paths to search
            extensions: List of file extensions to include (default: from config)

        Returns:
            List of file paths
        """
        if extensions is None:
            extensions = self.settings.ingestion.supported_extensions

        files = []
        ignore_patterns = self.settings.ingestion.ignore_patterns

        for directory in directories:
            dir_path = Path(directory)

            if not dir_path.exists():
                logger.warning(f"Directory not found: {directory}")
                continue

            logger.info(f"Scanning directory: {directory}")

            # Walk through directory
            for file_path in dir_path.rglob("*"):
                if not file_path.is_file():
                    continue

                # Check extension
                if file_path.suffix.lower() not in extensions:
                    continue

                # Check ignore patterns
                should_ignore = False
                for pattern in ignore_patterns:
                    if file_path.match(pattern):
                        should_ignore = True
                        break

                if should_ignore:
                    continue

                # Check file size
                max_size = self.settings.ingestion.max_file_size_mb * 1024 * 1024
                if file_path.stat().st_size > max_size:
                    logger.warning(
                        f"Skipping large file: {file_path.name} "
                        f"({file_path.stat().st_size / (1024*1024):.1f} MB)"
                    )
                    continue

                files.append(file_path)

        logger.info(f"Discovered {len(files)} files to process")
        return files

    def process_file(self, filepath: Path) -> Dict[str, Any]:
        """Process a single file.

        Args:
            filepath: Path to file

        Returns:
            Processing result dictionary
        """
        result = {
            "filepath": str(filepath),
            "success": False,
            "error": None,
        }

        try:
            ext = filepath.suffix.lower()
            content = None
            metadata = {}

            # Determine processing method
            if ext in [".msg", ".eml"]:
                # Email processing
                content, metadata = self.email_parser.parse(str(filepath))

            elif self.ocr_processor.is_image_file(str(filepath)) and self.settings.ocr.enabled:
                # OCR processing for images
                content, metadata = self.ocr_processor.process_image(str(filepath))

            else:
                # Standard document conversion with MarkItDown
                if self.doc_converter.is_supported(str(filepath)):
                    content, metadata = self.doc_converter.convert(str(filepath))
                else:
                    result["error"] = f"Unsupported file type: {ext}"
                    return result

            # Index the document
            if content or (metadata and "error" not in metadata):
                # Get database session
                db_session = db_manager.get_session()
                try:
                    indexer = Indexer(db_session)

                    # Auto-generate tags (simple keyword extraction)
                    tags = self._extract_tags(content, metadata)

                    # Index document
                    doc = indexer.index_document(
                        filepath=str(filepath.absolute()),
                        content_markdown=content or "",
                        metadata=metadata,
                        tags=tags,
                    )

                    if doc:
                        result["success"] = True
                        result["document_id"] = doc.id
                finally:
                    db_session.close()
            else:
                result["error"] = metadata.get("error", "No content extracted")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error processing {filepath}: {e}")

        return result

    def _extract_tags(
        self, content: Optional[str], metadata: Dict[str, Any]
    ) -> List[str]:
        """Extract tags from content and metadata.

        Args:
            content: Document content
            metadata: Document metadata

        Returns:
            List of tags
        """
        tags = []

        # Add file type as tag
        if "file_type" in metadata:
            file_type = metadata["file_type"].lstrip(".")
            tags.append(file_type)

        # Add special tags for specific types
        if metadata.get("ocr_enabled"):
            tags.append("ocr")
            tags.append("image")

        if metadata.get("email_type"):
            tags.append("email")

        # Add author as tag if present
        if metadata.get("author"):
            tags.append(f"author:{metadata['author']}")

        # TODO: More sophisticated tag extraction (TF-IDF, NER, etc.)
        # For now, keep it simple

        return list(set(tags))  # Remove duplicates

    def ingest_files(
        self, files: List[Path], show_progress: bool = True
    ) -> Dict[str, Any]:
        """Ingest multiple files in parallel.

        Args:
            files: List of file paths to process
            show_progress: Whether to show progress bar

        Returns:
            Ingestion statistics
        """
        self.stats["total_files"] = len(files)

        if len(files) == 0:
            logger.info("No files to process")
            return self.stats

        logger.info(f"Processing {len(files)} files with {self.parallel_workers} workers")

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.process_file, file): file for file in files
            }

            # Process results with progress bar
            if show_progress:
                pbar = tqdm(total=len(files), desc="Ingesting documents")
            else:
                pbar = None

            for future in as_completed(futures):
                result = future.result()

                if result["success"]:
                    self.stats["processed"] += 1
                elif result.get("error"):
                    self.stats["errors"] += 1
                else:
                    self.stats["skipped"] += 1

                # Track by type
                file_path = Path(result["filepath"])
                file_type = file_path.suffix.lower()
                self.stats["by_type"][file_type] = (
                    self.stats["by_type"].get(file_type, 0) + 1
                )

                if pbar:
                    pbar.update(1)

            if pbar:
                pbar.close()

        # Print summary
        logger.info(f"\nIngestion complete:")
        logger.info(f"  Total files: {self.stats['total_files']}")
        logger.info(f"  Processed: {self.stats['processed']}")
        logger.info(f"  Skipped: {self.stats['skipped']}")
        logger.info(f"  Errors: {self.stats['errors']}")

        return self.stats

    def ingest_directory(
        self, directory: str, recursive: bool = True
    ) -> Dict[str, Any]:
        """Ingest all supported files from a directory.

        Args:
            directory: Directory path
            recursive: Whether to search recursively

        Returns:
            Ingestion statistics
        """
        files = self.discover_files([directory])
        return self.ingest_files(files)


def ingest_documents(
    directories: Optional[List[str]] = None, parallel_workers: int = 4
) -> Dict[str, Any]:
    """Convenience function to ingest documents.

    Args:
        directories: List of directories to process (default: from config)
        parallel_workers: Number of parallel workers

    Returns:
        Ingestion statistics
    """
    settings = get_settings()

    if directories is None:
        directories = settings.ingestion.watch_directories

    ingestor = DocumentIngestor(parallel_workers=parallel_workers)
    files = ingestor.discover_files(directories)
    return ingestor.ingest_files(files)


if __name__ == "__main__":
    # Command-line interface for ingestion
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Ingest documents into Life DB")
    parser.add_argument(
        "directories",
        nargs="+",
        help="Directories to scan for documents",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar",
    )

    args = parser.parse_args()

    # Initialize database
    db_manager.initialize()

    # Run ingestion
    ingestor = DocumentIngestor(parallel_workers=args.workers)
    files = ingestor.discover_files(args.directories)
    stats = ingestor.ingest_files(files, show_progress=not args.no_progress)

    print(f"\n{'='*60}")
    print("Ingestion Summary")
    print(f"{'='*60}")
    print(f"Total files: {stats['total_files']}")
    print(f"Processed: {stats['processed']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print(f"\nBy file type:")
    for file_type, count in sorted(stats["by_type"].items()):
        print(f"  {file_type}: {count}")

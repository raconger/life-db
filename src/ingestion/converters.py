"""Document conversion utilities using MarkItDown and other tools."""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from markitdown import MarkItDown

logger = logging.getLogger(__name__)


class DocumentConverter:
    """Converter for various document formats to markdown."""

    def __init__(self, use_llm: bool = False):
        """Initialize document converter.

        Args:
            use_llm: Whether to use LLM for image descriptions (requires API key)
        """
        self.md_converter = MarkItDown()
        self.use_llm = use_llm

    def convert(
        self, filepath: str
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Convert a document to markdown.

        Args:
            filepath: Path to the document

        Returns:
            Tuple of (markdown_content, metadata_dict)
        """
        path = Path(filepath)

        if not path.exists():
            logger.error(f"File not found: {filepath}")
            return None, {}

        try:
            # Get file metadata
            file_stat = path.stat()
            file_size = file_stat.st_size
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)
            created_time = datetime.fromtimestamp(file_stat.st_ctime)

            # Calculate file hash
            file_hash = self._calculate_file_hash(filepath)

            # Convert using MarkItDown
            logger.info(f"Converting {path.name}...")
            result = self.md_converter.convert(str(path))

            # Extract metadata
            metadata = {
                "file_size": file_size,
                "modified_date": modified_time,
                "created_date": created_time,
                "file_hash": file_hash,
                "file_type": path.suffix.lower(),
                "filename": path.name,
                "filepath": str(path.absolute()),
            }

            # Add MarkItDown extracted metadata if available
            if hasattr(result, "title") and result.title:
                metadata["title"] = result.title

            # Try to extract author from document properties
            # (MarkItDown may extract this for Office documents)
            # For now, we'll leave it to be enhanced later

            markdown_content = result.text_content if result.text_content else ""

            logger.info(
                f"✓ Converted {path.name} ({len(markdown_content)} chars)"
            )

            return markdown_content, metadata

        except Exception as e:
            logger.error(f"Error converting {filepath}: {e}")
            # Return basic metadata even if conversion fails
            return None, {
                "file_size": path.stat().st_size if path.exists() else 0,
                "modified_date": (
                    datetime.fromtimestamp(path.stat().st_mtime)
                    if path.exists()
                    else None
                ),
                "created_date": (
                    datetime.fromtimestamp(path.stat().st_ctime)
                    if path.exists()
                    else None
                ),
                "file_type": path.suffix.lower(),
                "filename": path.name,
                "filepath": str(path.absolute()),
                "error": str(e),
            }

    def _calculate_file_hash(self, filepath: str, algorithm: str = "sha256") -> str:
        """Calculate hash of file for change detection.

        Args:
            filepath: Path to file
            algorithm: Hash algorithm to use

        Returns:
            Hex digest of file hash
        """
        hash_obj = hashlib.new(algorithm)

        try:
            with open(filepath, "rb") as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {filepath}: {e}")
            return ""

    def is_supported(self, filepath: str) -> bool:
        """Check if file type is supported for conversion.

        Args:
            filepath: Path to file

        Returns:
            True if supported, False otherwise
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        # MarkItDown supports these extensions
        supported_extensions = {
            # Office
            ".docx",
            ".doc",
            ".xlsx",
            ".xls",
            ".pptx",
            ".ppt",
            # PDF
            ".pdf",
            # Images
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".tiff",
            # Text
            ".txt",
            ".md",
            ".rst",
            ".rtf",
            # Data
            ".csv",
            ".json",
            ".xml",
            ".html",
            ".htm",
            # Archives
            ".zip",
        }

        return ext in supported_extensions

    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """Get basic file information without converting.

        Args:
            filepath: Path to file

        Returns:
            Dictionary with file info
        """
        path = Path(filepath)

        if not path.exists():
            return {}

        try:
            stat = path.stat()
            return {
                "filename": path.name,
                "filepath": str(path.absolute()),
                "file_type": path.suffix.lower(),
                "file_size": stat.st_size,
                "modified_date": datetime.fromtimestamp(stat.st_mtime),
                "created_date": datetime.fromtimestamp(stat.st_ctime),
                "file_hash": self._calculate_file_hash(filepath),
            }
        except Exception as e:
            logger.error(f"Error getting file info for {filepath}: {e}")
            return {}


def convert_document(filepath: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Convenience function to convert a single document.

    Args:
        filepath: Path to document

    Returns:
        Tuple of (markdown_content, metadata)
    """
    converter = DocumentConverter()
    return converter.convert(filepath)


if __name__ == "__main__":
    # Test conversion
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        converter = DocumentConverter()

        if converter.is_supported(filepath):
            content, metadata = converter.convert(filepath)
            print(f"\n{'='*60}")
            print(f"File: {metadata.get('filename', 'Unknown')}")
            print(f"Type: {metadata.get('file_type', 'Unknown')}")
            print(f"Size: {metadata.get('file_size', 0)} bytes")
            print(f"{'='*60}\n")
            if content:
                print(content[:500])  # First 500 chars
                print(f"\n... (total {len(content)} characters)")
            else:
                print("Failed to convert")
        else:
            print(f"Unsupported file type: {filepath}")
    else:
        print("Usage: python converters.py <filepath>")

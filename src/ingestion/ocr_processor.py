"""OCR processing for images and screenshots."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Optical Character Recognition processor for images."""

    def __init__(
        self,
        languages: List[str] = None,
        use_gpu: bool = False,
        min_confidence: float = 0.3,
    ):
        """Initialize OCR processor.

        Args:
            languages: List of language codes (default: ['en'])
            use_gpu: Whether to use GPU acceleration
            min_confidence: Minimum confidence threshold for OCR results
        """
        self.languages = languages or ["en"]
        self.use_gpu = use_gpu
        self.min_confidence = min_confidence
        self.reader = None
        self.has_easyocr = self._check_easyocr()

    def _check_easyocr(self) -> bool:
        """Check if EasyOCR is available."""
        try:
            import easyocr

            return True
        except ImportError:
            logger.warning("EasyOCR not available, OCR functionality disabled")
            return False

    def _initialize_reader(self):
        """Lazy initialization of EasyOCR reader."""
        if self.reader is None and self.has_easyocr:
            try:
                import easyocr

                logger.info(
                    f"Initializing EasyOCR reader (languages: {self.languages}, "
                    f"GPU: {self.use_gpu})..."
                )
                self.reader = easyocr.Reader(
                    self.languages, gpu=self.use_gpu, verbose=False
                )
                logger.info("✓ EasyOCR reader initialized")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
                self.has_easyocr = False

    def process_image(
        self, filepath: str
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Process an image file with OCR.

        Args:
            filepath: Path to image file

        Returns:
            Tuple of (extracted_text_markdown, metadata)
        """
        if not self.has_easyocr:
            logger.warning(f"EasyOCR not available, skipping OCR for {filepath}")
            return None, {"error": "EasyOCR not available"}

        path = Path(filepath)
        if not path.exists():
            logger.error(f"File not found: {filepath}")
            return None, {"error": "File not found"}

        try:
            # Initialize reader on first use
            self._initialize_reader()

            if self.reader is None:
                return None, {"error": "Failed to initialize OCR reader"}

            logger.info(f"Processing image with OCR: {path.name}")

            # Perform OCR
            results = self.reader.readtext(str(path))

            # Filter by confidence and extract text
            extracted_lines = []
            low_confidence_count = 0
            total_confidence = 0.0

            for detection in results:
                bbox, text, confidence = detection

                if confidence >= self.min_confidence:
                    extracted_lines.append(text)
                    total_confidence += confidence
                else:
                    low_confidence_count += 1

            # Build markdown representation
            if extracted_lines:
                markdown_content = self._build_ocr_markdown(
                    filename=path.name, lines=extracted_lines
                )

                avg_confidence = (
                    total_confidence / len(extracted_lines)
                    if extracted_lines
                    else 0.0
                )

                metadata = {
                    "ocr_enabled": True,
                    "ocr_confidence": round(avg_confidence, 3),
                    "ocr_lines_found": len(extracted_lines),
                    "ocr_lines_rejected": low_confidence_count,
                    "ocr_total_detections": len(results),
                    "title": f"Image: {path.stem}",
                }

                logger.info(
                    f"✓ OCR complete: {len(extracted_lines)} lines "
                    f"(avg confidence: {avg_confidence:.2f})"
                )

                return markdown_content, metadata
            else:
                logger.warning(f"No text found in image: {path.name}")
                return None, {
                    "ocr_enabled": True,
                    "ocr_lines_found": 0,
                    "ocr_total_detections": len(results),
                    "title": f"Image: {path.stem}",
                    "warning": "No text detected",
                }

        except Exception as e:
            logger.error(f"Error processing image {filepath}: {e}")
            return None, {"error": str(e), "ocr_enabled": True}

    def _build_ocr_markdown(self, filename: str, lines: List[str]) -> str:
        """Build markdown representation of OCR results.

        Args:
            filename: Name of image file
            lines: Extracted text lines

        Returns:
            Markdown formatted OCR results
        """
        markdown = f"# OCR: {filename}\n\n"
        markdown += f"*Extracted text from image:*\n\n"
        markdown += "---\n\n"

        # Join lines with newlines, preserving structure
        markdown += "\n\n".join(lines)

        markdown += "\n\n---\n"
        markdown += f"\n*{len(lines)} text lines extracted*\n"

        return markdown

    def is_image_file(self, filepath: str) -> bool:
        """Check if file is an image that can be processed with OCR.

        Args:
            filepath: Path to file

        Returns:
            True if file is a supported image format
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        supported_formats = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".tiff",
            ".tif",
            ".webp",
        }

        return ext in supported_formats


def process_image_ocr(
    filepath: str, languages: List[str] = None, use_gpu: bool = False
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Convenience function to process an image with OCR.

    Args:
        filepath: Path to image file
        languages: List of language codes (default: ['en'])
        use_gpu: Whether to use GPU acceleration

    Returns:
        Tuple of (markdown_content, metadata)
    """
    processor = OCRProcessor(languages=languages, use_gpu=use_gpu)
    return processor.process_image(filepath)


if __name__ == "__main__":
    # Test OCR processing
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        processor = OCRProcessor()

        if processor.is_image_file(filepath):
            content, metadata = processor.process_image(filepath)

            print(f"\n{'='*60}")
            print(f"File: {Path(filepath).name}")
            print(f"Lines found: {metadata.get('ocr_lines_found', 0)}")
            print(
                f"Average confidence: {metadata.get('ocr_confidence', 0):.2f}"
            )
            print(f"{'='*60}\n")

            if content:
                print(content)
            else:
                print("No text extracted")
                if "error" in metadata:
                    print(f"Error: {metadata['error']}")
        else:
            print(f"Not a supported image file: {filepath}")
    else:
        print("Usage: python ocr_processor.py <image_filepath>")
        print("Note: This will download EasyOCR models (~500MB) on first run")

"""Email parsing utilities for MSG and EML files."""

import email
import logging
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class EmailParser:
    """Parser for email files (MSG, EML)."""

    def __init__(self):
        """Initialize email parser."""
        self.has_extract_msg = self._check_extract_msg()

    def _check_extract_msg(self) -> bool:
        """Check if extract-msg is available."""
        try:
            import extract_msg

            return True
        except ImportError:
            logger.warning(
                "extract-msg not available, MSG file support will be limited"
            )
            return False

    def parse_msg(self, filepath: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Parse Outlook MSG file.

        Args:
            filepath: Path to MSG file

        Returns:
            Tuple of (email_content_markdown, metadata)
        """
        if not self.has_extract_msg:
            logger.error("extract-msg not installed, cannot parse MSG files")
            return None, {}

        try:
            import extract_msg

            msg = extract_msg.Message(filepath)

            # Extract basic fields
            subject = msg.subject or "(No Subject)"
            sender = msg.sender or "(Unknown Sender)"
            to_recipients = msg.to or "(Unknown Recipients)"
            date_str = msg.date or ""
            body = msg.body or ""

            # Try to parse date
            email_date = None
            if date_str:
                try:
                    # Various date formats might be used
                    email_date = datetime.strptime(
                        date_str, "%a, %d %b %Y %H:%M:%S %z"
                    )
                except:
                    try:
                        email_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        logger.warning(f"Could not parse date: {date_str}")

            # Build markdown representation
            markdown_content = self._build_email_markdown(
                subject=subject,
                sender=sender,
                recipients=to_recipients,
                date=date_str,
                body=body,
            )

            # Build metadata
            metadata = {
                "title": subject,
                "author": sender,
                "email_to": to_recipients,
                "email_date": email_date,
                "email_type": "msg",
                "has_attachments": len(msg.attachments) > 0,
                "attachment_count": len(msg.attachments),
            }

            # Extract attachment names
            if msg.attachments:
                attachment_names = [att.longFilename or att.shortFilename
                                   for att in msg.attachments]
                metadata["attachments"] = attachment_names

            msg.close()

            logger.info(f"✓ Parsed MSG: {subject}")
            return markdown_content, metadata

        except Exception as e:
            logger.error(f"Error parsing MSG file {filepath}: {e}")
            return None, {"error": str(e)}

    def parse_eml(self, filepath: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Parse EML email file.

        Args:
            filepath: Path to EML file

        Returns:
            Tuple of (email_content_markdown, metadata)
        """
        try:
            with open(filepath, "rb") as f:
                msg = BytesParser(policy=policy.default).parse(f)

            # Extract headers
            subject = msg.get("Subject", "(No Subject)")
            sender = msg.get("From", "(Unknown Sender)")
            to_recipients = msg.get("To", "(Unknown Recipients)")
            date_str = msg.get("Date", "")
            cc = msg.get("Cc", "")

            # Parse date
            email_date = None
            if date_str:
                try:
                    # Use email.utils to parse the date
                    from email.utils import parsedate_to_datetime

                    email_date = parsedate_to_datetime(date_str)
                except Exception as e:
                    logger.warning(f"Could not parse date '{date_str}': {e}")

            # Extract body
            body = self._extract_email_body(msg)

            # Build markdown
            markdown_content = self._build_email_markdown(
                subject=subject,
                sender=sender,
                recipients=to_recipients,
                date=date_str,
                body=body,
                cc=cc,
            )

            # Check for attachments
            attachments = []
            has_attachments = False
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    has_attachments = True
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)

            # Build metadata
            metadata = {
                "title": subject,
                "author": sender,
                "email_to": to_recipients,
                "email_cc": cc,
                "email_date": email_date,
                "email_type": "eml",
                "has_attachments": has_attachments,
                "attachment_count": len(attachments),
            }

            if attachments:
                metadata["attachments"] = attachments

            logger.info(f"✓ Parsed EML: {subject}")
            return markdown_content, metadata

        except Exception as e:
            logger.error(f"Error parsing EML file {filepath}: {e}")
            return None, {"error": str(e)}

    def _extract_email_body(self, msg) -> str:
        """Extract body text from email message.

        Args:
            msg: Email message object

        Returns:
            Body text
        """
        body = ""

        if msg.is_multipart():
            # Get plain text parts
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get_content_disposition()

                # Skip attachments
                if content_disposition == "attachment":
                    continue

                if content_type == "text/plain":
                    try:
                        body = part.get_content()
                        break  # Prefer plain text
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    # Fallback to HTML if no plain text
                    try:
                        html_content = part.get_content()
                        # Basic HTML stripping (MarkItDown can handle this better)
                        body = html_content
                    except:
                        pass
        else:
            # Not multipart, get content directly
            try:
                body = msg.get_content()
            except:
                body = str(msg.get_payload())

        return body

    def _build_email_markdown(
        self,
        subject: str,
        sender: str,
        recipients: str,
        date: str,
        body: str,
        cc: str = "",
    ) -> str:
        """Build markdown representation of email.

        Args:
            subject: Email subject
            sender: Sender address
            recipients: Recipient addresses
            date: Date string
            body: Email body
            cc: CC addresses

        Returns:
            Markdown formatted email
        """
        markdown = f"# {subject}\n\n"
        markdown += "---\n\n"
        markdown += f"**From:** {sender}\n\n"
        markdown += f"**To:** {recipients}\n\n"

        if cc:
            markdown += f"**Cc:** {cc}\n\n"

        markdown += f"**Date:** {date}\n\n"
        markdown += "---\n\n"
        markdown += body

        return markdown

    def parse(self, filepath: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Parse email file (auto-detect MSG or EML).

        Args:
            filepath: Path to email file

        Returns:
            Tuple of (email_content_markdown, metadata)
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".msg":
            return self.parse_msg(filepath)
        elif ext == ".eml":
            return self.parse_eml(filepath)
        else:
            logger.error(f"Unsupported email format: {ext}")
            return None, {"error": f"Unsupported email format: {ext}"}


def parse_email(filepath: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Convenience function to parse an email file.

    Args:
        filepath: Path to email file

    Returns:
        Tuple of (markdown_content, metadata)
    """
    parser = EmailParser()
    return parser.parse(filepath)


if __name__ == "__main__":
    # Test email parsing
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        parser = EmailParser()

        content, metadata = parser.parse(filepath)

        print(f"\n{'='*60}")
        print(f"Subject: {metadata.get('title', 'Unknown')}")
        print(f"From: {metadata.get('author', 'Unknown')}")
        print(f"To: {metadata.get('email_to', 'Unknown')}")
        print(f"Date: {metadata.get('email_date', 'Unknown')}")
        print(f"Attachments: {metadata.get('attachment_count', 0)}")
        print(f"{'='*60}\n")

        if content:
            print(content[:500])  # First 500 chars
            print(f"\n... (total {len(content)} characters)")
        else:
            print("Failed to parse email")
    else:
        print("Usage: python email_parser.py <filepath>")

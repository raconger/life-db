"""Search and indexing functionality using SQLite FTS5."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from src.models.database import Document

logger = logging.getLogger(__name__)


class SearchResult:
    """Represents a search result."""

    def __init__(
        self,
        id: int,
        filename: str,
        filepath: str,
        file_type: str,
        modified_date: Optional[datetime],
        title: Optional[str],
        author: Optional[str],
        snippet: str,
        rank: float,
    ):
        self.id = id
        self.filename = filename
        self.filepath = filepath
        self.file_type = file_type
        self.modified_date = modified_date
        self.title = title
        self.author = author
        self.snippet = snippet
        self.rank = rank

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "filepath": self.filepath,
            "file_type": self.file_type,
            "modified_date": (
                self.modified_date.isoformat() if self.modified_date else None
            ),
            "title": self.title,
            "author": self.author,
            "snippet": self.snippet,
            "rank": self.rank,
        }


class Searcher:
    """Full-text search using SQLite FTS5."""

    def __init__(self, db_path: str = "./db/lifedb.sqlite"):
        """Initialize searcher.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

    def search(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        file_type: Optional[str] = None,
        author: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        snippet_length: int = 64,
    ) -> List[SearchResult]:
        """Search documents using full-text search.

        Args:
            query: Search query
            limit: Maximum number of results
            offset: Number of results to skip
            file_type: Filter by file type (e.g., '.pdf')
            author: Filter by author
            date_from: Filter by minimum date
            date_to: Filter by maximum date
            snippet_length: Length of text snippets

        Returns:
            List of search results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Build query
            sql = """
                SELECT
                    d.id,
                    d.filename,
                    d.filepath,
                    d.file_type,
                    d.modified_date,
                    d.title,
                    d.author,
                    snippet(documents_fts, 1, '<mark>', '</mark>', '...', ?) as snippet,
                    rank as rank_score
                FROM documents_fts
                JOIN documents d ON documents_fts.rowid = d.id
                WHERE documents_fts MATCH ?
            """

            params = [snippet_length, query]

            # Add filters
            if file_type:
                sql += " AND d.file_type = ?"
                params.append(file_type)

            if author:
                sql += " AND d.author LIKE ?"
                params.append(f"%{author}%")

            if date_from:
                sql += " AND d.modified_date >= ?"
                params.append(date_from.isoformat())

            if date_to:
                sql += " AND d.modified_date <= ?"
                params.append(date_to.isoformat())

            # Order by relevance
            sql += " ORDER BY rank LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                # Parse datetime if present
                mod_date = None
                if row[4]:
                    try:
                        mod_date = datetime.fromisoformat(row[4])
                    except:
                        pass

                result = SearchResult(
                    id=row[0],
                    filename=row[1],
                    filepath=row[2],
                    file_type=row[3],
                    modified_date=mod_date,
                    title=row[5],
                    author=row[6],
                    snippet=row[7],
                    rank=row[8],
                )
                results.append(result)

            logger.info(f"Search '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
        finally:
            conn.close()

    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get full document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document dictionary or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT
                    id, filepath, filename, file_type, file_size,
                    created_date, modified_date, indexed_date,
                    content_markdown, author, title, tags, metadata_json
                FROM documents
                WHERE id = ?
            """,
                (doc_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "filepath": row[1],
                "filename": row[2],
                "file_type": row[3],
                "file_size": row[4],
                "created_date": row[5],
                "modified_date": row[6],
                "indexed_date": row[7],
                "content_markdown": row[8],
                "author": row[9],
                "title": row[10],
                "tags": json.loads(row[11]) if row[11] else [],
                "metadata": json.loads(row[12]) if row[12] else {},
            }

        finally:
            conn.close()

    def get_document_by_path(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Get document by file path.

        Args:
            filepath: File path

        Returns:
            Document dictionary or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id FROM documents WHERE filepath = ?", (filepath,)
            )
            row = cursor.fetchone()

            if row:
                return self.get_document_by_id(row[0])
            return None

        finally:
            conn.close()

    def get_facets(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get facets for browsing/filtering.

        Returns:
            Dictionary of facets (file types, authors, date ranges)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            facets = {}

            # File types
            cursor.execute("""
                SELECT file_type, COUNT(*) as count
                FROM documents
                GROUP BY file_type
                ORDER BY count DESC
            """)
            facets["file_types"] = [
                {"value": row[0], "count": row[1]} for row in cursor.fetchall()
            ]

            # Authors
            cursor.execute("""
                SELECT author, COUNT(*) as count
                FROM documents
                WHERE author IS NOT NULL AND author != ''
                GROUP BY author
                ORDER BY count DESC
                LIMIT 50
            """)
            facets["authors"] = [
                {"value": row[0], "count": row[1]} for row in cursor.fetchall()
            ]

            # Date ranges (by year-month)
            cursor.execute("""
                SELECT strftime('%Y-%m', modified_date) as month, COUNT(*) as count
                FROM documents
                WHERE modified_date IS NOT NULL
                GROUP BY month
                ORDER BY month DESC
                LIMIT 24
            """)
            facets["date_ranges"] = [
                {"value": row[0], "count": row[1]} for row in cursor.fetchall()
            ]

            return facets

        finally:
            conn.close()


class Indexer:
    """Index documents into the database."""

    def __init__(self, db_session: Session):
        """Initialize indexer.

        Args:
            db_session: Database session
        """
        self.db = db_session

    def index_document(
        self,
        filepath: str,
        content_markdown: str,
        metadata: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> Optional[Document]:
        """Index a single document.

        Args:
            filepath: Path to document
            content_markdown: Converted markdown content
            metadata: Document metadata
            tags: Optional list of tags

        Returns:
            Document object or None
        """
        try:
            # Check if document already exists
            existing = (
                self.db.query(Document).filter(Document.filepath == filepath).first()
            )

            # Prepare document data
            doc_data = {
                "filepath": filepath,
                "filename": metadata.get("filename", Path(filepath).name),
                "file_type": metadata.get("file_type", ""),
                "file_size": metadata.get("file_size", 0),
                "created_date": metadata.get("created_date"),
                "modified_date": metadata.get("modified_date"),
                "content_markdown": content_markdown,
                "author": metadata.get("author"),
                "title": metadata.get("title"),
                "tags": json.dumps(tags) if tags else None,
                "metadata_json": json.dumps(metadata),
                "file_hash": metadata.get("file_hash"),
            }

            if existing:
                # Update existing document
                for key, value in doc_data.items():
                    setattr(existing, key, value)
                existing.indexed_date = datetime.utcnow()
                doc = existing
                logger.info(f"Updated document: {doc.filename}")
            else:
                # Create new document
                doc = Document(**doc_data)
                self.db.add(doc)
                logger.info(f"Indexed new document: {doc.filename}")

            self.db.commit()
            return doc

        except Exception as e:
            logger.error(f"Error indexing document {filepath}: {e}")
            self.db.rollback()
            return None

    def delete_document(self, filepath: str) -> bool:
        """Delete a document from the index.

        Args:
            filepath: Path to document

        Returns:
            True if deleted, False otherwise
        """
        try:
            doc = self.db.query(Document).filter(Document.filepath == filepath).first()
            if doc:
                self.db.delete(doc)
                self.db.commit()
                logger.info(f"Deleted document: {filepath}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting document {filepath}: {e}")
            self.db.rollback()
            return False


if __name__ == "__main__":
    # Test search functionality
    logging.basicConfig(level=logging.INFO)

    searcher = Searcher()

    # Test search
    results = searcher.search("test", limit=10)
    print(f"\nFound {len(results)} results for 'test'")

    for result in results:
        print(f"  - {result.filename}: {result.snippet[:50]}...")

    # Test facets
    facets = searcher.get_facets()
    print(f"\nFile types:")
    for ft in facets.get("file_types", [])[:5]:
        print(f"  - {ft['value']}: {ft['count']}")

"""Database models and initialization for Life DB."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    BigInteger,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


class Document(Base):
    """Document model representing an indexed file."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filepath = Column(String(1024), unique=True, nullable=False, index=True)
    filename = Column(String(512), nullable=False, index=True)
    file_type = Column(String(50), nullable=False, index=True)
    file_size = Column(BigInteger)
    created_date = Column(DateTime, index=True)
    modified_date = Column(DateTime, index=True)
    indexed_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    content_markdown = Column(Text)
    author = Column(String(256))
    title = Column(String(512), index=True)
    tags = Column(Text)  # JSON array of tags
    metadata_json = Column(Text)  # Additional metadata as JSON
    file_hash = Column(String(64))  # SHA-256 hash for change detection

    def to_dict(self):
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "filepath": self.filepath,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "modified_date": (
                self.modified_date.isoformat() if self.modified_date else None
            ),
            "indexed_date": (
                self.indexed_date.isoformat() if self.indexed_date else None
            ),
            "author": self.author,
            "title": self.title,
            "tags": json.loads(self.tags) if self.tags else [],
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "file_hash": self.file_hash,
        }


class DatabaseManager:
    """Manager for database operations."""

    def __init__(self, db_path: str = "./db/lifedb.sqlite"):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = None
        self.SessionLocal = None

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Initialize database with tables and FTS5 index."""
        # Create engine
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create tables
        Base.metadata.create_all(self.engine)

        # Create FTS5 virtual table and triggers
        self._create_fts5_index()

        print(f"✓ Database initialized at {self.db_path}")

    def _create_fts5_index(self):
        """Create FTS5 virtual table and triggers for full-text search."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Create FTS5 virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    filename,
                    content_markdown,
                    title,
                    tags,
                    author,
                    content='documents',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );
            """)

            # Trigger: Insert
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                    INSERT INTO documents_fts(
                        rowid,
                        filename,
                        content_markdown,
                        title,
                        tags,
                        author
                    )
                    VALUES (
                        new.id,
                        new.filename,
                        new.content_markdown,
                        new.title,
                        new.tags,
                        new.author
                    );
                END;
            """)

            # Trigger: Delete
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                    DELETE FROM documents_fts WHERE rowid = old.id;
                END;
            """)

            # Trigger: Update
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                    UPDATE documents_fts
                    SET filename = new.filename,
                        content_markdown = new.content_markdown,
                        title = new.title,
                        tags = new.tags,
                        author = new.author
                    WHERE rowid = new.id;
                END;
            """)

            conn.commit()
            print("✓ FTS5 index and triggers created")

        except sqlite3.Error as e:
            print(f"Error creating FTS5 index: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy session
        """
        if not self.SessionLocal:
            self.initialize()
        return self.SessionLocal()

    def rebuild_fts_index(self):
        """Rebuild the FTS5 index from scratch."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Clear FTS index
            cursor.execute("DELETE FROM documents_fts;")

            # Rebuild from documents table
            cursor.execute("""
                INSERT INTO documents_fts(
                    rowid,
                    filename,
                    content_markdown,
                    title,
                    tags,
                    author
                )
                SELECT
                    id,
                    filename,
                    content_markdown,
                    title,
                    tags,
                    author
                FROM documents;
            """)

            conn.commit()
            print("✓ FTS index rebuilt successfully")

        except sqlite3.Error as e:
            print(f"Error rebuilding FTS index: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]

            # Total size
            cursor.execute("SELECT SUM(file_size) FROM documents")
            total_size = cursor.fetchone()[0] or 0

            # File types
            cursor.execute("""
                SELECT file_type, COUNT(*) as count
                FROM documents
                GROUP BY file_type
                ORDER BY count DESC
            """)
            file_types = [
                {"type": row[0], "count": row[1]} for row in cursor.fetchall()
            ]

            # Recent documents
            cursor.execute("""
                SELECT COUNT(*)
                FROM documents
                WHERE indexed_date >= datetime('now', '-7 days')
            """)
            recent_count = cursor.fetchone()[0]

            return {
                "total_documents": total_docs,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_types": file_types,
                "indexed_last_week": recent_count,
            }

        finally:
            conn.close()


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Session:
    """Dependency for getting database sessions.

    Yields:
        Database session
    """
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def init_database(db_path: str = "./db/lifedb.sqlite"):
    """Initialize the database.

    Args:
        db_path: Path to database file
    """
    manager = DatabaseManager(db_path)
    manager.initialize()
    return manager


if __name__ == "__main__":
    # Test database initialization
    print("Initializing Life DB database...")
    manager = init_database()

    # Print stats
    stats = manager.get_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    print(f"  File types: {len(stats['file_types'])}")
    print(f"  Indexed last week: {stats['indexed_last_week']}")

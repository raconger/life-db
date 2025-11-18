"""FastAPI application for Life DB."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.indexing.indexer import Searcher
from src.ingestion.ingestor import DocumentIngestor
from src.models.database import db_manager
from src.utils.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

# Initialize database
db_manager.initialize()

# Create FastAPI app
app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="A blazing-fast, local-first searchable database for all your work files",
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
except RuntimeError:
    logger.warning("Static files directory not found")

# Initialize searcher
searcher = Searcher(db_manager.db_path)


# Pydantic models for API
class SearchQuery(BaseModel):
    """Search query request."""

    query: str
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    file_type: Optional[str] = None
    author: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response."""

    results: List[dict]
    total: int
    query: str
    took_ms: float


class IngestRequest(BaseModel):
    """Ingest request."""

    directories: List[str]
    parallel_workers: Optional[int] = 4


class StatsResponse(BaseModel):
    """Statistics response."""

    total_documents: int
    total_size_mb: float
    file_types: List[dict]
    indexed_last_week: int


# Routes


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface."""
    try:
        async with aiofiles.open("web/templates/index.html", "r") as f:
            content = await f.read()
        return content
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Life DB</h1><p>Web interface not found. "
            "Please ensure web/templates/index.html exists.</p>",
            status_code=200,
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app.version}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get database statistics."""
    try:
        stats = db_manager.get_stats()
        return StatsResponse(
            total_documents=stats["total_documents"],
            total_size_mb=stats["total_size_mb"],
            file_types=stats["file_types"],
            indexed_last_week=stats["indexed_last_week"],
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", response_model=SearchResponse)
async def search_documents(query: SearchQuery):
    """Search documents using full-text search."""
    if not query.query or len(query.query) < settings.search.min_query_length:
        raise HTTPException(
            status_code=400,
            detail=f"Query must be at least {settings.search.min_query_length} characters",
        )

    try:
        start_time = datetime.now()

        # Parse dates if provided
        date_from = None
        date_to = None
        if query.date_from:
            try:
                date_from = datetime.fromisoformat(query.date_from)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format")

        if query.date_to:
            try:
                date_to = datetime.fromisoformat(query.date_to)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format")

        # Perform search
        results = searcher.search(
            query=query.query,
            limit=min(query.limit, settings.search.max_results),
            offset=query.offset,
            file_type=query.file_type,
            author=query.author,
            date_from=date_from,
            date_to=date_to,
            snippet_length=settings.search.snippet_length,
        )

        # Calculate time taken
        took_ms = (datetime.now() - start_time).total_seconds() * 1000

        return SearchResponse(
            results=[r.to_dict() for r in results],
            total=len(results),
            query=query.query,
            took_ms=round(took_ms, 2),
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: int):
    """Get full document by ID."""
    try:
        doc = searcher.get_document_by_id(doc_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        return doc

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{doc_id}/download")
async def download_document(doc_id: int):
    """Download original file."""
    try:
        doc = searcher.get_document_by_id(doc_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        filepath = doc["filepath"]

        if not Path(filepath).exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        return FileResponse(
            filepath,
            media_type="application/octet-stream",
            filename=doc["filename"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/facets")
async def get_facets():
    """Get facets for filtering."""
    try:
        facets = searcher.get_facets()
        return facets
    except Exception as e:
        logger.error(f"Error getting facets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest")
async def ingest_documents(request: IngestRequest, background_tasks: BackgroundTasks):
    """Trigger document ingestion (runs in background)."""
    try:

        def run_ingestion():
            """Background task for ingestion."""
            ingestor = DocumentIngestor(parallel_workers=request.parallel_workers)
            files = ingestor.discover_files(request.directories)
            stats = ingestor.ingest_files(files, show_progress=False)
            logger.info(f"Ingestion complete: {stats}")

        background_tasks.add_task(run_ingestion)

        return {
            "status": "started",
            "message": "Ingestion started in background",
            "directories": request.directories,
        }

    except Exception as e:
        logger.error(f"Error starting ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/browse")
async def browse_documents(
    file_type: Optional[str] = None,
    author: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
):
    """Browse documents with filters (no search query)."""
    try:
        # For browsing without search, we'll query directly from the database
        import sqlite3

        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()

        # Build query
        sql = """
            SELECT
                id, filename, filepath, file_type, modified_date,
                title, author, indexed_date
            FROM documents
            WHERE 1=1
        """
        params = []

        if file_type:
            sql += " AND file_type = ?"
            params.append(file_type)

        if author:
            sql += " AND author LIKE ?"
            params.append(f"%{author}%")

        sql += " ORDER BY modified_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        documents = []
        for row in rows:
            documents.append(
                {
                    "id": row[0],
                    "filename": row[1],
                    "filepath": row[2],
                    "file_type": row[3],
                    "modified_date": row[4],
                    "title": row[5],
                    "author": row[6],
                    "indexed_date": row[7],
                }
            )

        conn.close()

        return {"documents": documents, "total": len(documents)}

    except Exception as e:
        logger.error(f"Browse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int):
    """Delete a document from the index."""
    try:
        doc = searcher.get_document_by_id(doc_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from database
        from src.indexing.indexer import Indexer

        db_session = db_manager.get_session()
        try:
            indexer = Indexer(db_session)
            success = indexer.delete_document(doc["filepath"])

            if success:
                return {"status": "deleted", "document_id": doc_id}
            else:
                raise HTTPException(status_code=500, detail="Failed to delete document")
        finally:
            db_session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"Starting {settings.app.name} v{settings.app.version}")
    logger.info(f"Database: {db_manager.db_path}")

    # Print statistics
    stats = db_manager.get_stats()
    logger.info(f"Total documents: {stats['total_documents']}")
    logger.info(f"Total size: {stats['total_size_mb']} MB")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Life DB")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level="info",
    )

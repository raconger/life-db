# Searchable File Database - Project Plan

## Executive Summary

This document outlines a comprehensive plan to build a local, blazing-fast searchable database for Microsoft Office files, emails, PDFs, screenshots, and text documents. The system will run on Mac/Arch Linux with mobile access capabilities and provide intelligent organization and browsing features.

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Sources                         │
│  (PowerPoint, Excel, Word, Outlook, PDF, Images, Text)      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Document Processing Pipeline                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  MarkItDown  │  │  OCR Engine  │  │Email Parsers │     │
│  │  Converter   │  │  (EasyOCR)   │  │(extract-msg) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Metadata Extraction                         │
│     (filename, path, date, author, file type, tags)         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Storage & Indexing Layer                        │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │   SQLite Database    │  │  Full-Text Search    │        │
│  │  (metadata, files)   │  │  Engine (FTS5 or     │        │
│  │                      │  │   Meilisearch)       │        │
│  └──────────────────────┘  └──────────────────────┘        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Search API   │  │  Browse API  │  │  Admin API   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Web UI (HTML/CSS/JavaScript)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Search View  │  │  Browse View │  │ Preview View │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Mobile Access via Tailscale                     │
│           (iOS/Android access from anywhere)                 │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack Recommendations

### Core Technologies

#### 1. Document Processing
- **MarkItDown** (Microsoft's open-source tool)
  - Supports: PDF, PowerPoint, Word, Excel, Images, Audio, HTML, CSV, JSON, XML, ZIP
  - Python 3.10+ required
  - Excellent structure preservation
  - LLM integration for image descriptions (optional)
  - GitHub: ~50k stars, actively maintained

#### 2. Additional Processing Libraries
- **EasyOCR** - OCR for screenshots and scanned documents
  - Deep learning-based, multi-language support
  - Handles printed and handwritten text
- **extract-msg** - Outlook MSG file parsing
  - Extracts emails, attachments, metadata
  - Python 3.8+ compatible
- **libratom** - PST file processing
  - Extracts messages from Outlook PST archives
  - Converts to standard EML format
- **Python email module** (built-in) - EML file parsing
  - Standard library, no dependencies

#### 3. Search Engine Options

**Option A: SQLite FTS5 (Recommended for Phase 1)**
- **Pros:**
  - Zero additional infrastructure
  - Embedded, no separate service
  - Fast for datasets up to millions of documents
  - Built-in to Python
  - Simple deployment
- **Cons:**
  - No BM25 ranking (basic relevance)
  - Limited advanced search features
  - Performance degrades with tens of millions of rows
- **Best for:** Getting started quickly, simpler deployments

**Option B: Meilisearch (Recommended for Phase 2+)**
- **Pros:**
  - Modern, typo-tolerant search
  - 7,600 lines of Rust (lightweight)
  - Excellent relevance ranking
  - Fast indexing and search
  - RESTful API
  - Easy to install (brew install meilisearch)
  - Auto-generated API documentation
- **Cons:**
  - Larger index sizes
  - Requires separate service
- **Best for:** Production use, advanced search features, better UX

**Option C: Tantivy (Advanced Alternative)**
- **Pros:**
  - Rust-based Lucene alternative
  - BM25 ranking, faceted search
  - Extremely fast, multi-threaded indexing
  - Block max WAND support
- **Cons:**
  - Library, not standalone service
  - Requires Rust integration or Python bindings
- **Best for:** Maximum performance at scale

**Recommendation:** Start with SQLite FTS5 for rapid development, migrate to Meilisearch when you need better search quality and have >100k documents.

#### 4. Web Framework
- **FastAPI** (Recommended)
  - Modern, fast (matches Node.js/Go performance)
  - Auto-generated OpenAPI documentation
  - Async support for high concurrency
  - Type hints and validation via Pydantic
  - Easy to learn, production-ready
  - Perfect for API-first architecture

**Alternative:** Flask (if you prefer simplicity over performance)

#### 5. Database
- **SQLite** (Primary storage)
  - Stores metadata (filename, path, dates, file types, tags)
  - Stores converted markdown content
  - Relationships between documents
  - Zero configuration, embedded

#### 6. Mobile Access
- **Tailscale** (Highly Recommended)
  - Zero-config VPN mesh network
  - iOS and Android apps
  - "VPN On Demand" for iOS
  - Secure access from anywhere
  - No port forwarding needed
  - Free for personal use (up to 100 devices)

**Alternatives:**
- WireGuard (more manual setup)
- Local network only (WiFi when home)
- Reverse proxy with authentication (more complex)

## Phase-by-Phase Implementation Plan

### Phase 1: Document Ingestion & Basic Search (Weeks 1-3)

**Goal:** Ingest documents and provide fast full-text search

#### Week 1: Foundation & Setup
1. Set up project structure
   ```
   life-db/
   ├── src/
   │   ├── ingestion/
   │   │   ├── __init__.py
   │   │   ├── converters.py      # MarkItDown integration
   │   │   ├── email_parser.py    # Email extraction
   │   │   └── ocr_processor.py   # Screenshot OCR
   │   ├── indexing/
   │   │   ├── __init__.py
   │   │   └── indexer.py         # FTS5 indexing
   │   ├── api/
   │   │   ├── __init__.py
   │   │   └── main.py            # FastAPI app
   │   ├── models/
   │   │   ├── __init__.py
   │   │   └── database.py        # SQLite models
   │   └── utils/
   │       ├── __init__.py
   │       └── file_watcher.py    # Watch for new files
   ├── web/
   │   ├── static/
   │   │   ├── css/
   │   │   └── js/
   │   └── templates/
   │       └── index.html
   ├── tests/
   ├── data/                      # User's documents
   ├── db/                        # SQLite database
   ├── config/
   │   └── settings.yaml
   ├── requirements.txt
   └── README.md
   ```

2. Install dependencies
   ```bash
   pip install markitdown fastapi uvicorn sqlalchemy aiosqlite
   pip install extract-msg easyocr Pillow pypdf
   pip install python-multipart jinja2
   ```

3. Create SQLite schema
   ```sql
   -- documents table
   CREATE TABLE documents (
       id INTEGER PRIMARY KEY,
       filepath TEXT UNIQUE NOT NULL,
       filename TEXT NOT NULL,
       file_type TEXT NOT NULL,
       file_size INTEGER,
       created_date DATETIME,
       modified_date DATETIME,
       indexed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
       content_markdown TEXT,
       author TEXT,
       title TEXT,
       tags TEXT,
       metadata_json TEXT
   );

   -- full-text search virtual table
   CREATE VIRTUAL TABLE documents_fts USING fts5(
       filename,
       content_markdown,
       tags,
       content='documents',
       content_rowid='id'
   );

   -- triggers to keep FTS in sync
   CREATE TRIGGER documents_ai AFTER INSERT ON documents BEGIN
       INSERT INTO documents_fts(rowid, filename, content_markdown, tags)
       VALUES (new.id, new.filename, new.content_markdown, new.tags);
   END;
   ```

#### Week 2: Document Processing Pipeline
1. Implement MarkItDown converter
   - Handle all Office formats
   - PDF processing
   - Image to markdown with OCR fallback

2. Implement email parsers
   - MSG file extraction (extract-msg)
   - PST file processing (libratom)
   - EML parsing (built-in email module)

3. Implement OCR for screenshots
   - EasyOCR integration
   - Preprocessing with PIL/OpenCV
   - Text extraction and markdown formatting

4. Create batch ingestion script
   - Recursive directory scanning
   - Parallel processing
   - Progress tracking
   - Error handling and logging

#### Week 3: Basic Search & API
1. Implement search functionality
   - Full-text search with FTS5
   - Ranking by relevance
   - Snippet generation (context around matches)
   - Metadata filtering (by date, type, etc.)

2. Build FastAPI endpoints
   ```python
   # Core endpoints
   POST /api/ingest              # Trigger ingestion
   GET  /api/search              # Search documents
   GET  /api/documents/{id}      # Get single document
   GET  /api/documents/{id}/raw  # Download original file
   GET  /api/stats               # Database statistics
   ```

3. Basic web UI
   - Search bar
   - Results list with snippets
   - File type icons
   - Basic filters (date range, file type)

**Deliverable:** Working search system for ingested documents

---

### Phase 2: Intelligent Organization & Filtering (Weeks 4-6)

**Goal:** Add browsing capabilities, smart filtering, and organization

#### Week 4: Metadata Enhancement
1. Enhanced metadata extraction
   - Author detection (Office metadata)
   - Creation/modification dates
   - File size and type
   - Page count for documents
   - Image dimensions for screenshots

2. Auto-tagging system
   - Extract keywords from content
   - TF-IDF based important terms
   - Named entity recognition (optional: spaCy)
   - Category detection (work, personal, technical, etc.)

3. Manual tagging interface
   - Add/remove tags
   - Tag autocomplete
   - Bulk tagging

#### Week 5: Browse & Filter UI
1. Faceted browsing
   - Filter by file type
   - Filter by date (today, this week, this month, this year)
   - Filter by author
   - Filter by tags
   - Filter by size

2. Multiple view modes
   - List view (default)
   - Grid view (for images/screenshots)
   - Timeline view (chronological)
   - Tree view (by folder structure)

3. Sorting options
   - Relevance (default for search)
   - Date modified (newest/oldest)
   - File size
   - Filename (alphabetical)

#### Week 6: Smart Collections & Saved Searches
1. Collections system
   - Create custom collections
   - Add documents to collections
   - Collection sharing (export/import)

2. Saved searches
   - Save common search queries
   - Quick access filters
   - Email-like "smart folders"

3. Related documents
   - Find similar documents (content similarity)
   - Documents from same author
   - Documents created around same time

**Deliverable:** Full browsing and organization system

---

### Phase 3: Web UI & Mobile Access (Weeks 7-8)

**Goal:** Polish the web interface and enable mobile access

#### Week 7: Web UI Enhancement
1. Modern, responsive design
   - Mobile-first CSS
   - Dark mode support
   - Keyboard shortcuts
   - Accessibility (ARIA labels, screen reader support)

2. Advanced features
   - Document preview (markdown rendering)
   - Syntax highlighting for code
   - PDF preview (PDF.js)
   - Image gallery view
   - Export search results

3. Search enhancements
   - Search suggestions/autocomplete
   - Search history
   - Advanced query syntax
     - Quotes for exact phrases: "quarterly report"
     - Exclusion: -draft
     - Field-specific: author:john
     - Boolean: (report OR presentation) AND Q4

#### Week 8: Mobile Access & Deployment
1. Tailscale setup
   - Install on Mac/Arch Linux server
   - Configure subnet routing (optional)
   - Test from iOS/Android devices

2. Mobile-optimized UI
   - Touch-friendly interface
   - Bottom navigation
   - Swipe gestures
   - PWA manifest (install as app)

3. Production setup
   - Systemd service file (for Arch Linux)
   - launchd configuration (for Mac)
   - Automatic startup
   - Log rotation
   - Backup strategy

4. Documentation
   - Installation guide
   - Usage instructions
   - Configuration options
   - Troubleshooting guide

**Deliverable:** Production-ready system with mobile access

---

## Technical Implementation Details

### Document Processing Pipeline

```python
# Example: MarkItDown integration
from markitdown import MarkItDown

def convert_document(filepath: str) -> tuple[str, dict]:
    """Convert any supported document to markdown.

    Returns:
        tuple: (markdown_content, metadata)
    """
    md = MarkItDown()
    result = md.convert(filepath)

    return result.text_content, {
        'title': result.title,
        'author': result.author,
        # Additional metadata
    }
```

### Search Implementation

```python
# Example: FTS5 search
def search_documents(query: str, limit: int = 50) -> list[dict]:
    """Full-text search with snippet generation."""
    sql = """
        SELECT
            d.id,
            d.filename,
            d.filepath,
            d.file_type,
            d.modified_date,
            snippet(documents_fts, 1, '<mark>', '</mark>', '...', 64) as snippet,
            rank
        FROM documents_fts
        JOIN documents d ON documents_fts.rowid = d.id
        WHERE documents_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    # Execute query and return results
```

### Email Processing

```python
# Example: MSG file processing
import extract_msg

def parse_outlook_msg(filepath: str) -> dict:
    """Extract email content and metadata from MSG file."""
    msg = extract_msg.Message(filepath)

    return {
        'subject': msg.subject,
        'sender': msg.sender,
        'date': msg.date,
        'body': msg.body,
        'attachments': [att.save() for att in msg.attachments]
    }
```

## Performance Considerations

### Optimization Strategies

1. **Parallel Processing**
   - Use `multiprocessing` for document conversion
   - Batch insert into database
   - Process 10-50 files concurrently (tune based on CPU cores)

2. **Incremental Indexing**
   - Watch directories for changes (watchdog library)
   - Only reindex modified files
   - Track file hashes to detect changes

3. **Caching**
   - Cache converted markdown in database
   - Cache search results for common queries
   - Use Redis if needed for distributed caching

4. **Database Optimization**
   - Create indexes on frequently queried columns
   - Use ANALYZE to update query planner statistics
   - Vacuum database periodically
   - Consider WAL mode for concurrent access

### Expected Performance

With SQLite FTS5:
- **Indexing:** 10-50 documents/second (depending on size)
- **Search:** <100ms for most queries on databases up to 1M documents
- **Storage:** ~2-3x original file size (markdown + metadata)

With Meilisearch:
- **Indexing:** 50-200 documents/second
- **Search:** <50ms with typo tolerance and better ranking
- **Storage:** ~3-5x original file size

## Migration to Meilisearch (Optional Phase 4)

When to migrate:
- Database grows beyond 500k-1M documents
- Need typo tolerance and better relevance
- Want more advanced filtering
- Need distributed search

Migration steps:
1. Install Meilisearch (`brew install meilisearch`)
2. Update indexing code to push to Meilisearch
3. Update search API to query Meilisearch
4. Keep SQLite for metadata storage
5. Reindex all documents (can run in background)

## Security Considerations

1. **Authentication**
   - Add basic auth if exposed beyond Tailscale
   - Consider OAuth2 for multi-user setups

2. **File Access**
   - Validate file paths to prevent directory traversal
   - Sanitize user inputs
   - Don't expose full filesystem paths in API

3. **Tailscale Benefits**
   - Encrypted tunnel (WireGuard-based)
   - No exposed ports
   - Automatic key rotation
   - Access control via Tailscale admin

## Cost Analysis

**Free/Open Source:**
- MarkItDown: Free (MIT license)
- SQLite/FTS5: Free (Public domain)
- Meilisearch: Free (MIT license)
- FastAPI: Free (MIT license)
- EasyOCR: Free (Apache 2.0)
- extract-msg: Free (GPL)
- Tailscale: Free for personal use (<100 devices)

**Total cost:** $0 for personal use

**Hardware Requirements:**
- Disk: 2-5x your document collection size
- RAM: 2GB minimum, 4-8GB recommended
- CPU: Any modern multi-core processor

## Next Steps

### Immediate Actions:
1. ✅ Review this plan
2. Choose Phase 1 start date
3. Set up development environment
4. Create initial project structure
5. Install dependencies
6. Begin document processing implementation

### Decision Points:
- [ ] Confirm SQLite FTS5 for Phase 1 (vs. starting with Meilisearch)
- [ ] Choose specific file types to prioritize
- [ ] Determine if you want LLM-based image descriptions (requires API key)
- [ ] Decide on initial directory to ingest
- [ ] Confirm Tailscale for mobile access

## Resources & Documentation

- MarkItDown: https://github.com/microsoft/markitdown
- FastAPI: https://fastapi.tiangolo.com/
- SQLite FTS5: https://www.sqlite.org/fts5.html
- Meilisearch: https://www.meilisearch.com/docs
- Tailscale: https://tailscale.com/kb/
- extract-msg: https://pypi.org/project/extract-msg/
- EasyOCR: https://github.com/JaidedAI/EasyOCR

## Conclusion

This plan provides a comprehensive roadmap for building a powerful, local document search system. Starting with Phase 1 gives you a working system in 2-3 weeks, with incremental enhancements in subsequent phases. The architecture is designed to scale from thousands to millions of documents while maintaining blazing-fast search performance.

The choice of proven, actively-maintained open-source technologies ensures long-term viability and community support. Mobile access via Tailscale provides seamless access without complex networking or security concerns.

Ready to begin implementation? Let's start with Phase 1!

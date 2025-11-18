# Quick Start Guide

## Prerequisites

- Python 3.10 or higher
- Mac or Arch Linux
- 4GB+ RAM recommended
- 10GB+ free disk space

## Initial Setup (30 minutes)

### 1. Install System Dependencies

**Mac:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.10+
brew install python@3.11

# Optional: Install Meilisearch (for Phase 2+)
brew install meilisearch
```

**Arch Linux:**
```bash
# Update system
sudo pacman -Syu

# Install Python
sudo pacman -S python python-pip

# Install optional dependencies
sudo pacman -S tesseract tesseract-data-eng
```

### 2. Set Up Python Virtual Environment

```bash
# Navigate to project directory
cd /home/user/life-db

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Mac/Linux

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Python Dependencies

Create `requirements.txt`:
```txt
# Core framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
jinja2==3.1.2

# Database
sqlalchemy==2.0.23
aiosqlite==0.19.0

# Document processing
markitdown==0.0.1a2
extract-msg==0.45.0
pypdf==3.17.1
Pillow==10.1.0

# OCR (optional but recommended)
easyocr==1.7.0

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
watchdog==3.0.0

# Development
pytest==7.4.3
black==23.11.0
```

Install:
```bash
pip install -r requirements.txt
```

**Note:** EasyOCR will download ~500MB of models on first run.

### 4. Create Project Structure

```bash
mkdir -p src/{ingestion,indexing,api,models,utils}
mkdir -p web/{static/{css,js},templates}
mkdir -p tests config data db

# Create __init__.py files
touch src/__init__.py
touch src/ingestion/__init__.py
touch src/indexing/__init__.py
touch src/api/__init__.py
touch src/models/__init__.py
touch src/utils/__init__.py
```

### 5. Create Configuration File

Create `config/settings.yaml`:
```yaml
# Application settings
app:
  name: "Life DB - Searchable File Database"
  version: "0.1.0"
  host: "0.0.0.0"
  port: 8000

# Database settings
database:
  path: "./db/lifedb.sqlite"
  echo: false

# Ingestion settings
ingestion:
  watch_directories:
    - "./data"
  supported_extensions:
    - ".docx"
    - ".xlsx"
    - ".pptx"
    - ".pdf"
    - ".msg"
    - ".eml"
    - ".txt"
    - ".md"
    - ".png"
    - ".jpg"
    - ".jpeg"
  max_file_size_mb: 50
  parallel_workers: 4

# Search settings
search:
  results_per_page: 50
  snippet_length: 64
  enable_typo_tolerance: false  # Requires Meilisearch

# OCR settings
ocr:
  enabled: true
  languages: ["en"]
  gpu: false  # Set to true if you have CUDA-capable GPU
```

### 6. Initialize Database

Create `src/models/database.py`:
```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import sqlite3

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    filepath = Column(String, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer)
    created_date = Column(DateTime)
    modified_date = Column(DateTime)
    indexed_date = Column(DateTime, default=datetime.utcnow)
    content_markdown = Column(Text)
    author = Column(String)
    title = Column(String)
    tags = Column(String)
    metadata_json = Column(Text)

def init_database(db_path: str = "./db/lifedb.sqlite"):
    """Initialize SQLite database with FTS5 support."""
    # Create tables
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)

    # Create FTS5 virtual table and triggers
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create FTS5 table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            filename,
            content_markdown,
            tags,
            content='documents',
            content_rowid='id'
        );
    """)

    # Create triggers
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts(rowid, filename, content_markdown, tags)
            VALUES (new.id, new.filename, new.content_markdown, new.tags);
        END;
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
            DELETE FROM documents_fts WHERE rowid = old.id;
        END;
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
            UPDATE documents_fts
            SET filename = new.filename,
                content_markdown = new.content_markdown,
                tags = new.tags
            WHERE rowid = new.id;
        END;
    """)

    conn.commit()
    conn.close()

    print(f"Database initialized at {db_path}")
    return engine

if __name__ == "__main__":
    init_database()
```

Run initialization:
```bash
python src/models/database.py
```

### 7. Create Basic FastAPI Application

Create `src/api/main.py`:
```python
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
from typing import Optional, List

app = FastAPI(title="Life DB", version="0.1.0")

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 50
    file_type: Optional[str] = None

class SearchResult(BaseModel):
    id: int
    filename: str
    filepath: str
    file_type: str
    modified_date: Optional[str]
    snippet: str

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface."""
    with open("web/templates/index.html") as f:
        return f.read()

@app.get("/api/stats")
async def get_stats():
    """Get database statistics."""
    conn = sqlite3.connect("./db/lifedb.sqlite")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT file_type) FROM documents")
    file_types = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(file_size) FROM documents")
    total_size = cursor.fetchone()[0] or 0

    conn.close()

    return {
        "total_documents": total_docs,
        "file_types": file_types,
        "total_size_mb": round(total_size / (1024 * 1024), 2)
    }

@app.post("/api/search", response_model=List[SearchResult])
async def search_documents(query: SearchQuery):
    """Search documents using full-text search."""
    conn = sqlite3.connect("./db/lifedb.sqlite")
    cursor = conn.cursor()

    sql = """
        SELECT
            d.id,
            d.filename,
            d.filepath,
            d.file_type,
            d.modified_date,
            snippet(documents_fts, 1, '<mark>', '</mark>', '...', 64) as snippet
        FROM documents_fts
        JOIN documents d ON documents_fts.rowid = d.id
        WHERE documents_fts MATCH ?
    """

    params = [query.query]

    if query.file_type:
        sql += " AND d.file_type = ?"
        params.append(query.file_type)

    sql += " ORDER BY rank LIMIT ?"
    params.append(query.limit)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()

    return [
        SearchResult(
            id=row[0],
            filename=row[1],
            filepath=row[2],
            file_type=row[3],
            modified_date=row[4],
            snippet=row[5]
        )
        for row in results
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 8. Create Simple Web Interface

Create `web/templates/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Life DB - Search Your Files</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { margin-bottom: 30px; color: #333; }
        .search-box {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        input[type="search"] {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 4px;
        }
        .stats {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 20px;
        }
        .stat { flex: 1; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #007AFF; }
        .stat-label { color: #666; font-size: 14px; }
        .results { background: white; border-radius: 8px; padding: 20px; }
        .result-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }
        .result-item:hover { background: #f9f9f9; }
        .result-filename { font-weight: bold; color: #333; margin-bottom: 5px; }
        .result-snippet { color: #666; line-height: 1.5; }
        .result-meta { font-size: 12px; color: #999; margin-top: 5px; }
        mark { background: #ffeb3b; padding: 2px 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Life DB</h1>

        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="total-docs">0</div>
                <div class="stat-label">Documents</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="file-types">0</div>
                <div class="stat-label">File Types</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="total-size">0 MB</div>
                <div class="stat-label">Total Size</div>
            </div>
        </div>

        <div class="search-box">
            <input type="search" id="search-input" placeholder="Search your documents...">
        </div>

        <div class="results" id="results">
            <p style="color: #999; text-align: center;">Enter a search query to get started</p>
        </div>
    </div>

    <script>
        // Load stats
        async function loadStats() {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            document.getElementById('total-docs').textContent = stats.total_documents;
            document.getElementById('file-types').textContent = stats.file_types;
            document.getElementById('total-size').textContent = stats.total_size_mb + ' MB';
        }

        // Search function
        async function search(query) {
            if (!query) {
                document.getElementById('results').innerHTML =
                    '<p style="color: #999; text-align: center;">Enter a search query to get started</p>';
                return;
            }

            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, limit: 50 })
            });

            const results = await response.json();
            const resultsDiv = document.getElementById('results');

            if (results.length === 0) {
                resultsDiv.innerHTML = '<p style="color: #999; text-align: center;">No results found</p>';
                return;
            }

            resultsDiv.innerHTML = results.map(result => `
                <div class="result-item">
                    <div class="result-filename">${result.filename}</div>
                    <div class="result-snippet">${result.snippet}</div>
                    <div class="result-meta">
                        ${result.file_type} • ${result.modified_date || 'Unknown date'}
                    </div>
                </div>
            `).join('');
        }

        // Set up search input
        const searchInput = document.getElementById('search-input');
        let searchTimeout;

        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => search(e.target.value), 300);
        });

        // Load stats on page load
        loadStats();
    </script>
</body>
</html>
```

### 9. Test the Setup

```bash
# Start the development server
python src/api/main.py

# Or use uvicorn directly:
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser to: http://localhost:8000

You should see the Life DB interface!

### 10. Add Your First Documents

```bash
# Copy some test documents to the data directory
cp ~/Documents/test.docx ./data/
cp ~/Documents/report.pdf ./data/

# Create and run the ingestion script (we'll build this in Phase 1)
# For now, you can manually test MarkItDown:
python3 << EOF
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert("./data/test.docx")
print(result.text_content)
EOF
```

## Next Steps

1. **Read the full PROJECT_PLAN.md** for detailed implementation
2. **Start Phase 1** - Build the ingestion pipeline
3. **Test with your documents** - Start small and iterate
4. **Set up Tailscale** when ready for mobile access

## Troubleshooting

**Issue: EasyOCR fails to install**
- Solution: Install with `pip install easyocr --no-deps` then install dependencies manually

**Issue: Permission denied on Mac**
- Solution: Grant terminal/app Full Disk Access in System Preferences

**Issue: SQLite FTS5 not found**
- Solution: Update SQLite: `brew upgrade sqlite` (Mac) or rebuild Python with FTS5 support

**Issue: Port 8000 already in use**
- Solution: Change port in config or kill process: `lsof -ti:8000 | xargs kill`

## Useful Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run server
uvicorn src.api.main:app --reload

# Run tests
pytest

# Format code
black src/

# Check database
sqlite3 db/lifedb.sqlite "SELECT COUNT(*) FROM documents;"
```

## Resources

- Full documentation: See PROJECT_PLAN.md
- MarkItDown docs: https://github.com/microsoft/markitdown
- FastAPI docs: https://fastapi.tiangolo.com
- SQLite FTS5: https://www.sqlite.org/fts5.html

Happy searching! 🚀

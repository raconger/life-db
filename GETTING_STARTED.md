# Getting Started with Life DB

Welcome to Life DB! This guide will help you get up and running quickly.

## Prerequisites

- **Python 3.10+** (check with `python3 --version`)
- **4GB+ RAM** (8GB recommended for OCR)
- **10GB+ disk space** (for documents and indices)
- **Mac or Arch Linux**

## Quick Setup (5 minutes)

### 1. Clone and Setup

```bash
cd life-db

# Run the setup script
bash setup.sh

# This will:
# - Create a Python virtual environment
# - Install all dependencies
# - Initialize the database
# - Create necessary directories
```

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

You'll need to do this every time you open a new terminal.

### 3. Add Some Documents

Copy your documents to the `data` directory:

```bash
# Create subdirectories if you want
mkdir -p data/work data/personal

# Copy some files
cp ~/Documents/*.pdf data/work/
cp ~/Documents/*.docx data/personal/
```

### 4. Index Your Documents

```bash
# Index all files in the data directory
make ingest

# Or use the Python module directly:
python -m src.ingestion.ingestor ./data

# To index a specific directory:
python -m src.ingestion.ingestor ~/Documents/Reports
```

You should see progress as files are processed.

### 5. Start the Web Server

```bash
make run

# Or:
python -m src.api.main
```

The server will start on `http://localhost:8000`

### 6. Open in Browser

Navigate to: **http://localhost:8000**

You should see the Life DB interface with:
- Statistics about your indexed documents
- A search bar
- Filters for file types and authors

## Using Life DB

### Basic Search

Simply type in the search box. Results appear instantly as you type.

**Examples:**
- `quarterly report` - Search for documents containing these words
- `"Q4 2024"` - Exact phrase search
- `budget -draft` - Find "budget" but exclude "draft"

### Filters

Use the dropdown filters to narrow results:
- **File Type**: Filter by .pdf, .docx, etc.
- **Author**: Filter by document author

### View Documents

Click on any search result to:
- See the full document metadata
- Download the original file

## Automatic File Watching

To automatically index new files as they're added:

```bash
make watch

# Or:
python -m src.utils.file_watcher ./data
```

This will:
- Monitor the `data` directory for changes
- Automatically index new or modified files
- Run in the background until you press Ctrl+C

## Common Tasks

### Reindex All Files

```bash
make ingest
```

### Check Database Statistics

```bash
python -m src.models.database
```

### View Logs

Logs are stored in `logs/lifedb.log` (if configured):

```bash
tail -f logs/lifedb.log
```

## Command Reference

| Command | Description |
|---------|-------------|
| `make setup` | Initial setup (run once) |
| `make run` | Start web server |
| `make ingest` | Index documents from ./data |
| `make watch` | Start file watcher |
| `make test` | Run tests |
| `make clean` | Clean up temporary files |

## Troubleshooting

### Port 8000 already in use

Change the port in `config/settings.yaml`:

```yaml
app:
  port: 8080  # Change to any available port
```

### EasyOCR installation fails

EasyOCR requires ~500MB of models. If installation fails:

```bash
# Install without OCR support
pip install -r requirements.txt --no-deps
pip install markitdown fastapi uvicorn sqlalchemy

# Disable OCR in config/settings.yaml
ocr:
  enabled: false
```

### No results when searching

Make sure you've indexed your documents:

```bash
make ingest
```

Check database stats:

```bash
python -m src.models.database
```

### Permission errors on Mac

Grant Full Disk Access:
1. System Preferences → Security & Privacy
2. Privacy → Full Disk Access
3. Add your Terminal app

## Next Steps

### Phase 1 Complete! 🎉

You now have:
- ✅ Document ingestion (Office, PDF, email, images)
- ✅ Full-text search with SQLite FTS5
- ✅ Web interface
- ✅ Automatic file watching

### What's Next?

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for:
- **Phase 2**: Intelligent organization and advanced filtering
- **Phase 3**: Mobile access with Tailscale
- **Phase 4**: Migration to Meilisearch for better search

## Configuration

Edit `config/settings.yaml` to customize:

```yaml
# Watch different directories
ingestion:
  watch_directories:
    - "./data"
    - "/Users/you/Documents"
    - "/Users/you/Downloads"

# Add more file types
ingestion:
  supported_extensions:
    - ".docx"
    - ".pdf"
    # Add your custom extensions

# Adjust performance
performance:
  parallel_workers: 8  # More workers = faster indexing
```

## Getting Help

- **Documentation**: See [PROJECT_PLAN.md](PROJECT_PLAN.md) for architecture details
- **Quick Reference**: See [QUICK_START.md](QUICK_START.md) for code examples
- **Issues**: Check logs in `logs/lifedb.log`

## Tips & Tricks

### 1. Index Large Document Collections

For thousands of files:

```bash
# Increase parallel workers
python -m src.ingestion.ingestor ~/Documents -w 8
```

### 2. Search Syntax

Advanced search queries:
- `author:john report` - Search by field
- `filetype:.pdf budget` - Specific file type
- `"exact phrase" AND keyword` - Boolean operators

### 3. Run as Background Service

On Linux with systemd:

```bash
# Create service file (see docs for details)
sudo systemctl start lifedb
sudo systemctl enable lifedb
```

### 4. Backup Your Database

```bash
# The database is a single file
cp db/lifedb.sqlite db/lifedb.sqlite.backup

# Restore
cp db/lifedb.sqlite.backup db/lifedb.sqlite
```

## Performance Benchmarks

Expected performance on modern hardware:

| Operation | Speed |
|-----------|-------|
| Indexing | 10-50 docs/second |
| Search | <100ms |
| Full-text search | <50ms (1M docs) |
| OCR processing | 1-5 seconds/image |

## What's Indexed?

Life DB extracts and indexes:
- **Content**: Full document text
- **Metadata**: Title, author, dates
- **File info**: Name, path, type, size
- **Email fields**: Subject, sender, recipients
- **OCR text**: From images and screenshots

## Privacy & Security

- **Local-only**: All data stays on your machine
- **No cloud**: No external services required
- **No tracking**: Zero analytics or telemetry
- **Encrypted access**: Use Tailscale for remote access (Phase 3)

---

**Happy searching!** 🚀

For more details, see:
- [README.md](README.md) - Project overview
- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Complete roadmap
- [QUICK_START.md](QUICK_START.md) - Technical reference

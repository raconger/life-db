# Life DB - Searchable File Database

A blazing-fast, local-first searchable database for all your work files. Index and search Microsoft Office documents, PDFs, emails, screenshots, and more with intelligent organization and mobile access.

## ✨ Features

- **Universal Document Support**: PowerPoint, Word, Excel, Outlook emails, PDFs, screenshots, text files
- **Lightning-Fast Search**: Full-text search with snippet highlighting
- **Intelligent Organization**: Auto-tagging, smart collections, and faceted browsing
- **Mobile Access**: Access your database from iOS/Android via Tailscale
- **Privacy-First**: Runs entirely on your Mac or Arch Linux machine
- **Modern Web UI**: Responsive interface with dark mode support

## 🚀 Quick Start

See [QUICK_START.md](QUICK_START.md) for detailed setup instructions.

```bash
# 1. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database
python src/models/database.py

# 4. Start the server
uvicorn src.api.main:app --reload

# 5. Open in browser
open http://localhost:8000
```

## 📋 Project Plan

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the complete implementation roadmap covering:

- **Phase 1**: Document ingestion & basic search (Weeks 1-3)
- **Phase 2**: Intelligent organization & filtering (Weeks 4-6)
- **Phase 3**: Web UI & mobile access (Weeks 7-8)
- **Phase 4**: Optional migration to Meilisearch for advanced features

## 🏗️ Architecture

```
Documents → MarkItDown Converter → SQLite Database → FastAPI → Web UI
              ↓                           ↓
           OCR Engine              Full-Text Search (FTS5)
              ↓                           ↓
        Email Parsers              Mobile Access (Tailscale)
```

## 🛠️ Technology Stack

- **Document Processing**: MarkItDown, EasyOCR, extract-msg
- **Search Engine**: SQLite FTS5 (Phase 1) or Meilisearch (Phase 2+)
- **Backend**: FastAPI, SQLAlchemy
- **Frontend**: Modern HTML/CSS/JavaScript
- **Mobile Access**: Tailscale VPN mesh network

## 📁 Project Structure

```
life-db/
├── src/
│   ├── ingestion/       # Document converters and processors
│   ├── indexing/        # Search indexing logic
│   ├── api/             # FastAPI application
│   ├── models/          # Database models
│   └── utils/           # Helper utilities
├── web/
│   ├── static/          # CSS, JavaScript
│   └── templates/       # HTML templates
├── data/                # Your documents (not in git)
├── db/                  # SQLite database (not in git)
├── config/              # Configuration files
└── tests/               # Unit and integration tests
```

## 🎯 Supported File Types

- **Office**: `.docx`, `.xlsx`, `.pptx`, `.doc`, `.xls`, `.ppt`
- **Email**: `.msg` (Outlook), `.eml`, `.pst` (archives)
- **Documents**: `.pdf`, `.txt`, `.md`, `.rtf`
- **Images**: `.png`, `.jpg`, `.jpeg` (with OCR)
- **Archives**: `.zip` (content extraction)
- **Data**: `.csv`, `.json`, `.xml`

## 🔍 Search Features

- Full-text search across all document content
- Snippet generation with match highlighting
- Filter by file type, date, author, tags
- Advanced query syntax (phrases, exclusions, boolean operators)
- Typo tolerance (with Meilisearch)
- Search history and saved searches

## 📱 Mobile Access

Access your searchable database from anywhere using Tailscale:

1. Install Tailscale on your Mac/Linux server
2. Install Tailscale app on iOS/Android
3. Access your database via secure encrypted tunnel
4. No port forwarding or complex networking needed

## 🔒 Privacy & Security

- **Local-first**: All data stays on your machine
- **No cloud dependencies**: Works completely offline
- **Encrypted access**: Tailscale uses WireGuard encryption
- **Zero tracking**: No analytics or data collection

## 🚧 Current Status

This project is in the planning phase. The complete implementation plan is documented in [PROJECT_PLAN.md](PROJECT_PLAN.md).

**Ready to build:**
- ✅ Complete architecture design
- ✅ Technology stack selected
- ✅ Phase-by-phase implementation plan
- ✅ Quick start guide and examples
- 🔲 Phase 1 implementation (next step)

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📄 License

[Choose your license - e.g., MIT, GPL, etc.]

## 🙏 Acknowledgments

Built with these amazing open-source projects:
- [MarkItDown](https://github.com/microsoft/markitdown) by Microsoft
- [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez
- [SQLite](https://www.sqlite.org/) by D. Richard Hipp
- [Meilisearch](https://www.meilisearch.com/) by Meilisearch team
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) by JaidedAI
- [Tailscale](https://tailscale.com/) for secure networking

---

**Questions?** Check out the [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed information or [QUICK_START.md](QUICK_START.md) for setup instructions.

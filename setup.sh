#!/bin/bash
# Life DB Setup Script

set -e

echo "🚀 Setting up Life DB..."
echo

# Check Python version
echo "Checking Python version..."
python3 --version

if ! python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
    echo "❌ Error: Python 3.10 or higher is required"
    exit 1
fi

echo "✓ Python version OK"
echo

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

echo "✓ Virtual environment activated"
echo

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "✓ pip upgraded"
echo

# Install dependencies
echo "Installing dependencies..."
echo "(This may take a few minutes, especially for EasyOCR)"
pip install -r requirements.txt --quiet

echo "✓ Dependencies installed"
echo

# Create necessary directories
echo "Creating directories..."
mkdir -p db logs data

echo "✓ Directories created"
echo

# Initialize database
echo "Initializing database..."
python -m src.models.database

echo "✓ Database initialized"
echo

echo "✅ Setup complete!"
echo
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo
echo "  2. Add some documents to the ./data directory"
echo
echo "  3. Index your documents:"
echo "     python -m src.ingestion.ingestor ./data"
echo
echo "  4. Start the web server:"
echo "     python -m src.api.main"
echo
echo "  5. Open your browser to:"
echo "     http://localhost:8000"
echo
echo "For more information, see README.md and QUICK_START.md"

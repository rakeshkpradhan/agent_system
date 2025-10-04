#!/bin/bash
set -e

echo "🚀 Setting up Agentic AI Compliance Verification System"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
echo "⬆️ Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Please edit .env file with your configuration values"
fi

# Create logs directory
mkdir -p logs

echo "✅ Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration values"
echo "2. Place your GCP service account key as service-account-key.json"  
echo "3. Set up GCP Secret Manager with Confluence credentials"
echo "4. Initialize Spanner database and SpannerGraph with policy data"
echo "5. Run the application: python main.py"
echo ""
echo "For production deployment:"
echo "  docker-compose up -d"
echo "  OR"
echo "  gunicorn --config gunicorn.conf.py main:app"

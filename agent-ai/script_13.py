# Create deployment and configuration files
deployment_files = {
    # Docker configuration
    'Dockerfile': '''FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc g++ curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \\
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "300", \\
     "--keep-alive", "2", "--max-requests", "1000", "--worker-class", "gthread", \\
     "--threads", "2", "main:app"]
''',
    
    # Docker Compose for local development
    'docker-compose.yml': '''version: '3.8'

services:
  compliance-api:
    build: 
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - GCP_PROJECT_ID=${GCP_PROJECT_ID}
      - GCP_LOCATION=${GCP_LOCATION:-us-central1}
      - CONFLUENCE_BASE_URL=${CONFLUENCE_BASE_URL}
      - SPANNER_INSTANCE_ID=${SPANNER_INSTANCE_ID}
      - SPANNER_DATABASE_ID=${SPANNER_DATABASE_ID}
      - SPANNER_GRAPH_NAME=${SPANNER_GRAPH_NAME:-PolicyGraph}
      - EMBEDDING_MODEL_NAME=${EMBEDDING_MODEL_NAME:-text-embedding-005}
      - LLM_MODEL_NAME=${LLM_MODEL_NAME:-gemini-2.5-pro}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - FLASK_DEBUG=${FLASK_DEBUG:-false}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json
    volumes:
      - ./service-account-key.json:/app/service-account-key.json:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      - spanner-emulator

  # Spanner emulator for local development
  spanner-emulator:
    image: gcr.io/cloud-spanner-emulator/emulator:latest
    ports:
      - "9010:9010"
      - "9020:9020"
    environment:
      - SPANNER_EMULATOR_HOST=0.0.0.0:9010

volumes:
  logs:
    driver: local
''',
    
    # Environment template
    '.env.template': '''# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Confluence Configuration  
CONFLUENCE_BASE_URL=https://your-company.atlassian.net
# Store confluence-username and confluence-api-token in GCP Secret Manager

# GCP Spanner Configuration
SPANNER_INSTANCE_ID=compliance-instance
SPANNER_DATABASE_ID=compliance-db
SPANNER_VECTOR_TABLE_NAME=evidence_embeddings
SPANNER_GRAPH_NAME=PolicyGraph

# Vertex AI Configuration
EMBEDDING_MODEL_NAME=text-embedding-005
LLM_MODEL_NAME=gemini-2.5-pro

# Application Configuration
MAX_EVIDENCE_CHUNKS=50
SIMILARITY_SEARCH_K=5
EMBEDDING_DIMENSIONS=768
MAX_CHUNK_SIZE=2000
CHUNK_OVERLAP=200

# Flask Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_DEBUG_LOGGING=false
''',

    # Gunicorn production configuration
    'gunicorn.conf.py': '''# Gunicorn configuration for production deployment

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
worker_class = "gthread" 
threads = 2
worker_connections = 1000
timeout = 300
keepalive = 2

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%%(h)s %%(l)s %%(u)s %%(t)s "%%(r)s" %%(s)s %%(b)s "%%(f)s" "%%(a)s" %%(D)s'

# Process naming
proc_name = "agentic-compliance-api"

# Server mechanics
preload_app = True
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Enable stats
statsd_host = None
statsd_prefix = ""
''',

    # Setup script
    'setup.sh': '''#!/bin/bash
set -e

echo "🚀 Setting up Agentic AI Compliance Verification System"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
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
'''
}

# Write all deployment files
for filename, content in deployment_files.items():
    with open(filename, 'w') as f:
        f.write(content)
    
    # Make shell scripts executable
    if filename.endswith('.sh'):
        os.chmod(filename, 0o755)

print("✅ Created deployment and configuration files")
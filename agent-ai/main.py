#!/usr/bin/env python3
"""
Agentic AI Compliance Verification System - Main Entry Point

A comprehensive system for automating compliance verification by fetching evidence 
from Confluence pages and validating it against predefined compliance control policies 
using LangChain, LangGraph, and Google Vertex AI.

System Architecture:
    Data Ingestion → Context Retrieval → Policy Evaluation → Status Update → END

Author: AI Assistant
Version: 1.0.0
License: MIT
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from agentic_compliance_system.api.flask_app import app
    from agentic_compliance_system.core.config import config

except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point."""
    try:
        print("🤖 Agentic AI Compliance Verification System")
        print("=" * 50)
        print(f"Version: 1.0.0")
        print(f"Project: {config.project_id}")
        print(f"Location: {config.vertex_ai_location}")
        print(f"Environment: {'Development' if config.flask_debug else 'Production'}")
        print("=" * 50)

        # Validate configuration
        print("🔧 Validating system configuration...")
        if not config.validate_config():
            print("❌ Configuration validation failed")
            sys.exit(1)
        print("✅ Configuration validation passed")

        # Start the application
        if config.flask_debug:
            print("⚠️  Starting in DEVELOPMENT mode")
            print("   For production, use a WSGI server like Gunicorn")

        print(f"🚀 Starting server on {config.flask_host}:{config.flask_port}")
        print("🔗 Available endpoints:")
        print(f"   Health Check: http://{config.flask_host}:{config.flask_port}/health")
        print(f"   Validation:   http://{config.flask_host}:{config.flask_port}/validate")
        print(f"   Configuration: http://{config.flask_host}:{config.flask_port}/config")
        print(f"   Statistics:   http://{config.flask_host}:{config.flask_port}/stats")
        print("")

        # Run Flask application
        app.run(
            host=config.flask_host,
            port=config.flask_port,
            debug=config.flask_debug,
            threaded=True
        )

    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        print(f"❌ Startup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Create the project structure and main components
import os
import json
from pathlib import Path

# Create the main project directory structure
project_dirs = [
    "agentic_compliance_system",
    "agentic_compliance_system/agents",
    "agentic_compliance_system/core", 
    "agentic_compliance_system/models",
    "agentic_compliance_system/services",
    "agentic_compliance_system/utils",
    "agentic_compliance_system/api",
    "tests",
    "config",
    "scripts",
    "docs"
]

for dir_path in project_dirs:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

print("✅ Created modular project directory structure")

# Create __init__.py files for Python packages
init_files = [
    "agentic_compliance_system/__init__.py",
    "agentic_compliance_system/agents/__init__.py", 
    "agentic_compliance_system/core/__init__.py",
    "agentic_compliance_system/models/__init__.py",
    "agentic_compliance_system/services/__init__.py",
    "agentic_compliance_system/utils/__init__.py",
    "agentic_compliance_system/api/__init__.py",
    "tests/__init__.py"
]

for init_file in init_files:
    Path(init_file).touch()

print("✅ Created package __init__.py files")
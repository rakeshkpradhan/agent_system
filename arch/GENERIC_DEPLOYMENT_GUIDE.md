# Generic Multi-Policy Compliance Validation System - Deployment Guide

## System Overview

Universal Compliance Validation System designed to validate evidence against any compliance policy dynamically loaded from Spanner Graph. The system requires no code changes to support new policies.

### Supported Policy Types (Extensible)
- Policy 101: Test Execution
- Policy 201: Security Compliance
- Policy 301: Deployment Validation  
- Policy 401: Code Review
- Policy 501: Documentation
- Unlimited: Any future policy added to Spanner Graph

## Quick Start

### 1. Environment Setup
```bash
# Set up environment
cp .env_generic.template .env
# Edit .env with your configuration

# Install dependencies
pip install -r requirements_generic.txt
```

### 2. Run the System
```bash
# API server
python generic_compliance_validation_api.py
```

## API Usage

### Universal Compliance Validation
```bash
curl -X POST http://localhost:8080/validate/generic-compliance \
  -H "Content-Type: application/json" \
  -d '{
    "confluence_url": "https://confluence.company.com/display/PROJECT/Evidence",
    "change_request_id": "CHG-2024-001"
  }'
```

### Policy Discovery
```bash
curl -X POST http://localhost:8080/validate/policies/discover \
  -H "Content-Type: application/json" \
  -d '{
    "confluence_url": "https://confluence.company.com/display/PROJECT/Evidence"
  }'
```

### Policy Catalog
```bash
curl -X GET http://localhost:8080/policies/catalog
```

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y build-essential curl
COPY requirements_generic.txt .
RUN pip install --no-cache-dir -r requirements_generic.txt

# Copy application
COPY generic_compliance_validation_system_part1.py .
COPY generic_compliance_validation_system_part2_fixed.py .
COPY generic_compliance_validation_api.py .

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "generic_compliance_validation_api.py"]
```

### Build and Run
```bash
docker build -t generic-compliance-validation .
docker run -p 8080:8080 --env-file .env generic-compliance-validation
```

## Adding New Policies

### Step 1: Define Policy in Spanner Graph
Add new policy to compliance_policy_catalog table

### Step 2: Add Rules
Define rules in generic_compliance_rule table

### Step 3: System Automatically Adapts
No code changes required - system discovers and uses new policy

## Production Features

- Multi-policy support with cross-references
- Auto-detection of applicable policies
- Universal evidence parsing
- Policy-agnostic LLM evaluation
- Comprehensive audit trails
- Horizontal scaling support

This universal system provides unlimited extensibility for compliance validation across any domain while maintaining consistent quality and explainability.

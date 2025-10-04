# Create comprehensive documentation and database initialization scripts
docs_and_scripts = {
    # Database initialization script
    'scripts/init_database.py': '''#!/usr/bin/env python3
"""
Database initialization script for Agentic AI Compliance Verification System.

This script initializes:
1. Spanner vector store tables for evidence embeddings
2. Sample SpannerGraph schema for policy rules
3. Sample policy data for testing

Usage:
    python scripts/init_database.py
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from langchain_google_spanner import SpannerVectorStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_spanner_vector_store():
    """Initialize Spanner vector store tables."""
    try:
        project_id = os.getenv('GCP_PROJECT_ID')
        instance_id = os.getenv('SPANNER_INSTANCE_ID', 'compliance-instance')
        database_id = os.getenv('SPANNER_DATABASE_ID', 'compliance-db')
        
        if not project_id:
            raise ValueError("GCP_PROJECT_ID environment variable must be set")
        
        logger.info(f"Initializing Spanner vector store: {project_id}/{instance_id}/{database_id}")
        
        # Initialize vector store table with metadata columns
        SpannerVectorStore.init_vector_store_table(
            instance_id=instance_id,
            database_id=database_id,
            table_name="evidence_embeddings",
            id_column="langchain_id",
            content_column="content", 
            embedding_column="embedding",
            metadata_columns=[
                {"name": "source_url", "type": "STRING(MAX)"},
                {"name": "section_header", "type": "STRING(500)"},
                {"name": "chunk_id", "type": "STRING(100)"},
                {"name": "extraction_method", "type": "STRING(50)"},
                {"name": "content_type", "type": "STRING(50)"},
                {"name": "validation_status", "type": "STRING(50)"},
                {"name": "policy_name", "type": "STRING(200)"},
                {"name": "timestamp", "type": "TIMESTAMP"},
                {"name": "rule_assessments", "type": "JSON"},
                {"name": "analysis_summary", "type": "STRING(MAX)"},
                {"name": "confidence_score", "type": "FLOAT64"},
                {"name": "updated_at", "type": "TIMESTAMP"}
            ],
            vector_size=768  # text-embedding-005 dimensions
        )
        
        logger.info("✅ Successfully initialized evidence_embeddings table")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Spanner vector store: {str(e)}")
        return False


def create_spanner_graph_schema():
    """Create SpannerGraph schema for policy rules."""
    try:
        project_id = os.getenv('GCP_PROJECT_ID')
        instance_id = os.getenv('SPANNER_INSTANCE_ID', 'compliance-instance')
        database_id = os.getenv('SPANNER_DATABASE_ID', 'compliance-db')
        graph_name = os.getenv('SPANNER_GRAPH_NAME', 'PolicyGraph')
        
        client = spanner.Client(project=project_id)
        instance = client.instance(instance_id)
        database = instance.database(database_id)
        
        logger.info(f"Creating SpannerGraph schema: {graph_name}")
        
        # DDL statements for graph schema
        ddl_statements = [
            # Create Policy node table
            \"\"\"
            CREATE TABLE Policy (
                id STRING(100) NOT NULL,
                name STRING(200) NOT NULL,
                description STRING(MAX),
                version STRING(50),
                effective_date DATE,
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                updated_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true)
            ) PRIMARY KEY (id)
            \"\"\",
            
            # Create Rule node table
            \"\"\"
            CREATE TABLE Rule (
                rule_id STRING(100) NOT NULL,
                description STRING(MAX) NOT NULL,
                type STRING(100),
                severity STRING(50),
                validation_criteria STRING(MAX),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                updated_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true)
            ) PRIMARY KEY (rule_id)
            \"\"\",
            
            # Create Policy-Rule relationship table
            \"\"\"
            CREATE TABLE PolicyHasRule (
                policy_id STRING(100) NOT NULL,
                rule_id STRING(100) NOT NULL,
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                FOREIGN KEY (policy_id) REFERENCES Policy (id),
                FOREIGN KEY (rule_id) REFERENCES Rule (rule_id)
            ) PRIMARY KEY (policy_id, rule_id)
            \"\"\",
            
            # Create Policy-Policy reference table
            \"\"\"
            CREATE TABLE PolicyReferences (
                policy_id STRING(100) NOT NULL,
                referenced_policy_id STRING(100) NOT NULL,
                reference_type STRING(100),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                FOREIGN KEY (policy_id) REFERENCES Policy (id),
                FOREIGN KEY (referenced_policy_id) REFERENCES Policy (id)
            ) PRIMARY KEY (policy_id, referenced_policy_id)
            \"\"\",
            
            # Create the property graph
            f\"\"\"
            CREATE PROPERTY GRAPH {graph_name}
            NODE TABLES (
                Policy,
                Rule
            )
            EDGE TABLES (
                PolicyHasRule 
                    SOURCE KEY (policy_id) REFERENCES Policy (id)
                    DESTINATION KEY (rule_id) REFERENCES Rule (rule_id)
                    LABEL HAS_RULE,
                PolicyReferences
                    SOURCE KEY (policy_id) REFERENCES Policy (id) 
                    DESTINATION KEY (referenced_policy_id) REFERENCES Policy (id)
                    LABEL REFERENCES
            )
            \"\"\"
        ]
        
        # Execute DDL statements
        operation = database.update_ddl(ddl_statements)
        operation.result()
        
        logger.info("✅ Successfully created SpannerGraph schema")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create SpannerGraph schema: {str(e)}")
        return False


def insert_sample_policy_data():
    """Insert sample policy data for testing."""
    try:
        project_id = os.getenv('GCP_PROJECT_ID')
        instance_id = os.getenv('SPANNER_INSTANCE_ID', 'compliance-instance')
        database_id = os.getenv('SPANNER_DATABASE_ID', 'compliance-db')
        
        client = spanner.Client(project=project_id)
        instance = client.instance(instance_id)
        database = instance.database(database_id)
        
        logger.info("Inserting sample policy data")
        
        with database.batch() as batch:
            # Insert sample policies
            batch.insert(
                table='Policy',
                columns=['id', 'name', 'description', 'version', 'effective_date'],
                values=[
                    ('POL_RT', 'Regression Testing Policy', 
                     'Policy defining requirements for regression testing in software releases', 
                     '1.0', '2024-01-01'),
                    ('POL_PT', 'Performance Testing Policy',
                     'Policy defining requirements for performance testing and benchmarking',
                     '1.0', '2024-01-01'),
                    ('POL_TS', 'Testing Strategy Policy',
                     'Overall testing strategy and methodology requirements',
                     '1.0', '2024-01-01'),
                    ('POL_DS', 'Development Strategy Policy',
                     'Development practices and code quality requirements',
                     '1.0', '2024-01-01')
                ]
            )
            
            # Insert sample rules
            batch.insert(
                table='Rule',
                columns=['rule_id', 'description', 'type', 'severity', 'validation_criteria'],
                values=[
                    ('RT-001', 'All critical regression tests must be executed for major releases',
                     'Mandatory', 'High', '100% execution of critical test cases with pass rate >= 95%'),
                    ('RT-002', 'Test results must be documented and signed off by QA Lead',
                     'Documentation', 'High', 'Signed approval from designated QA Lead required'),
                    ('RT-003', 'Regression test suite must include database migration testing',
                     'Technical', 'Medium', 'Evidence of database migration test execution and validation'),
                    
                    ('PT-001', 'Performance benchmarks must meet defined SLA requirements',
                     'Performance', 'High', 'All SLA metrics within acceptable thresholds'),
                    ('PT-002', 'Load testing must be performed under realistic user scenarios',
                     'Performance', 'Medium', 'Evidence of realistic load test execution'),
                    
                    ('TS-001', 'Test strategy must be documented and approved before development',
                     'Process', 'High', 'Approved test strategy document exists'),
                    ('TS-002', 'Test coverage must meet minimum threshold requirements',
                     'Quality', 'Medium', 'Code coverage >= 80% for critical components'),
                    
                    ('DS-001', 'Code must pass static analysis with zero high-severity issues',
                     'Quality', 'High', 'Static analysis report shows no high-severity violations'),
                    ('DS-002', 'All code changes must be peer-reviewed before merge',
                     'Process', 'High', 'Evidence of peer review approval in version control')
                ]
            )
            
            # Insert policy-rule relationships
            batch.insert(
                table='PolicyHasRule',
                columns=['policy_id', 'rule_id'],
                values=[
                    ('POL_RT', 'RT-001'),
                    ('POL_RT', 'RT-002'), 
                    ('POL_RT', 'RT-003'),
                    ('POL_PT', 'PT-001'),
                    ('POL_PT', 'PT-002'),
                    ('POL_TS', 'TS-001'),
                    ('POL_TS', 'TS-002'),
                    ('POL_DS', 'DS-001'),
                    ('POL_DS', 'DS-002')
                ]
            )
            
            # Insert policy references (cross-references)
            batch.insert(
                table='PolicyReferences',
                columns=['policy_id', 'referenced_policy_id', 'reference_type'],
                values=[
                    ('POL_RT', 'POL_TS', 'dependency'),
                    ('POL_PT', 'POL_TS', 'dependency'),
                    ('POL_TS', 'POL_DS', 'reference')
                ]
            )
        
        logger.info("✅ Successfully inserted sample policy data")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to insert sample data: {str(e)}")
        return False


def main():
    """Main initialization function."""
    print("🗄️ Initializing Agentic AI Compliance Database Components")
    print("=" * 60)
    
    success_count = 0
    
    # Initialize vector store
    print("1. Initializing Spanner vector store...")
    if init_spanner_vector_store():
        success_count += 1
    
    # Create graph schema  
    print("\\n2. Creating SpannerGraph schema...")
    if create_spanner_graph_schema():
        success_count += 1
    
    # Insert sample data
    print("\\n3. Inserting sample policy data...")
    if insert_sample_policy_data():
        success_count += 1
    
    print("\\n" + "=" * 60)
    print(f"✅ Database initialization completed: {success_count}/3 components successful")
    
    if success_count < 3:
        print("⚠️  Some components failed. Check logs above for details.")
        sys.exit(1)
    else:
        print("🎉 All database components initialized successfully!")


if __name__ == "__main__":
    main()
''',

    # README.md documentation
    'README.md': '''# Agentic AI Compliance Verification System

A comprehensive, production-ready system for automating compliance verification by fetching evidence from Confluence pages and validating it against predefined compliance control policies using **LangChain**, **LangGraph**, and **Google Vertex AI**.

## 🏗️ System Architecture

The system implements a **LangGraph state machine** that orchestrates collaboration between specialized AI agents:

```
Data Ingestion → Context Retrieval → Policy Evaluation → Status Update → END
```

### 🤖 Specialized Agents

1. **EvidenceSummarizerAgent** - Fetches and processes evidence from Confluence using multi-strategy parsing
2. **ControlRetrievalAgent** - Retrieves policy rules from SpannerGraph and finds similar historical evidence  
3. **PolicyEvaluationAgent** - Uses Gemini 2.5 Pro for compliance evaluation with structured JSON output
4. **StatusUpdateAgent** - Persists results and generates final compliance decision

### 🏢 Modular Architecture

```
agentic_compliance_system/
├── agents/                 # Specialized AI agents
├── api/                   # Flask REST API
├── core/                  # Configuration and workflow orchestration
├── models/                # Data models and schemas
├── services/              # External service integrations
└── utils/                 # Content parsing utilities
```

## 🚀 Key Features

- **🔄 State Machine Workflow**: Robust LangGraph orchestration with error handling
- **🔐 Secure Integration**: GCP Secret Manager for credentials, secure Confluence API access
- **📊 Multi-Strategy Parsing**: BeautifulSoup, Trafilatura, and Confluence-specific parsing
- **🧠 Knowledge Graph**: SpannerGraph for complex policy rule relationships
- **🔍 Vector Similarity**: Spanner vector store for historical evidence analysis
- **🤖 Advanced LLM**: Gemini 2.5 Pro with structured JSON output and validation
- **🌐 Production API**: Flask with comprehensive error handling and monitoring
- **🐳 Containerized**: Docker deployment with health checks and auto-scaling

## 📋 Prerequisites

- **Python 3.11+**
- **Google Cloud Platform account** with Vertex AI enabled
- **Confluence Cloud** instance with API access
- **GCP Spanner** instance for vector storage and graph database
- **Service account key** with appropriate permissions

## ⚙️ Installation

### 1. Quick Setup

```bash
git clone <repository>
cd agentic-compliance-system
chmod +x setup.sh
./setup.sh
```

### 2. Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp .env.template .env
# Edit .env with your values
```

### 3. Configuration

Set up your environment variables in `.env`:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1

# Confluence Configuration  
CONFLUENCE_BASE_URL=https://your-company.atlassian.net

# Spanner Configuration
SPANNER_INSTANCE_ID=compliance-instance
SPANNER_DATABASE_ID=compliance-db
```

### 4. Secrets Setup

Store sensitive values in GCP Secret Manager:
- `confluence-username`: Your Confluence email
- `confluence-api-token`: Confluence API token

### 5. Database Initialization

```bash
python scripts/init_database.py
```

## 🏃 Running the Application

### Development Mode
```bash
python main.py
```

### Production with Docker
```bash
docker-compose up -d
```

### Production with Gunicorn
```bash
gunicorn --config gunicorn.conf.py main:app
```

## 📡 API Usage

### Health Check
```bash
curl -X GET http://localhost:8000/health
```

### Compliance Validation
```bash
curl -X POST http://localhost:8000/validate \\
  -H "Content-Type: application/json" \\
  -d '{
    "policy_name": "Regression Testing Policy",
    "evidence_url": "https://your-confluence.atlassian.net/wiki/spaces/PROJ/pages/12345/Evidence"
  }'
```

### Response Format
```json
{
  "policy_name": "Regression Testing Policy",
  "decision": "Compliant",
  "confidence_score": 0.95,
  "analysis_summary": "Evidence confirms all critical regression tests executed...",
  "rule_assessments": [
    {
      "rule_id": "RT-001",
      "rule_description": "All critical regression tests must be executed",
      "status": "Compliant", 
      "evidence_quote": "Execution of all 15 critical regression tests completed...",
      "confidence_score": 0.98
    }
  ],
  "evidence_id": "evidence-uuid",
  "timestamp": "2024-03-15T10:30:00Z",
  "processing_time_seconds": 12.45
}
```

## 🔧 System Components

### Content Parsing Strategies

The system uses multiple parsing strategies for robust content extraction:

1. **Trafilatura**: Clean text extraction with noise filtering
2. **BeautifulSoup**: Structured HTML parsing for tables, lists, sections
3. **Confluence-Specific**: Macro parsing, page properties, panels

### Data Storage

**Vector Store (Spanner)**:
- Document embeddings with text-embedding-005
- Metadata for source tracking and validation status
- Similarity search for historical evidence

**Knowledge Graph (SpannerGraph)**:
- Policy nodes with descriptions and versions
- Rule nodes with validation criteria and severity
- Relationships for policy-rule mappings and cross-references

### LLM Integration

**Gemini 2.5 Pro Features**:
- Structured JSON output with schema validation
- Zero-shot compliance evaluation prompts
- Confidence scoring and evidence quotation
- Error handling and response validation

## 🐳 Production Deployment

### Docker Deployment
```bash
# Build and run
docker build -t compliance-api .
docker run -p 8000:8000 compliance-api
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compliance-api
  template:
    spec:
      containers:
      - name: api
        image: gcr.io/PROJECT_ID/compliance-api
        ports:
        - containerPort: 8000
        env:
        - name: GCP_PROJECT_ID
          value: "your-project-id"
```

### GCP Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/compliance-api
gcloud run deploy compliance-api \\
  --image gcr.io/PROJECT_ID/compliance-api \\
  --platform managed \\
  --region us-central1
```

## 🔍 Monitoring and Observability

### Health Checks
- `/health` - System health and component status
- `/config` - Configuration validation  
- `/stats` - Agent and workflow statistics

### Logging
- Structured logging with correlation IDs
- Agent-level performance metrics
- Error tracking and stack traces
- Processing time monitoring

### Metrics
- Request duration and throughput
- Compliance decision distribution
- LLM confidence score trends
- Vector similarity search performance

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=agentic_compliance_system tests/

# Integration tests
pytest tests/integration/
```

## 🛠️ Development

### Code Quality
```bash
# Format code
black agentic_compliance_system/
isort agentic_compliance_system/

# Lint code  
flake8 agentic_compliance_system/
```

### Adding New Policies

1. **Define Policy in SpannerGraph**:
```sql
INSERT INTO Policy (id, name, description, version, effective_date)
VALUES ('POL_NEW', 'New Policy Name', 'Description', '1.0', '2024-01-01');
```

2. **Add Policy Rules**:
```sql
INSERT INTO Rule (rule_id, description, type, severity, validation_criteria)
VALUES ('NP-001', 'Rule description', 'Mandatory', 'High', 'Criteria');

INSERT INTO PolicyHasRule (policy_id, rule_id)
VALUES ('POL_NEW', 'NP-001');
```

3. **Test with API**:
```bash
curl -X POST http://localhost:8000/validate \\
  -H "Content-Type: application/json" \\
  -d '{"policy_name": "New Policy Name", "evidence_url": "..."}'
```

## 🔒 Security

- **Credential Management**: GCP Secret Manager integration
- **API Security**: Request validation and rate limiting
- **Network Security**: Container isolation and firewall rules
- **Data Encryption**: TLS in transit, encrypted at rest
- **Access Control**: IAM with least privilege principle

## 📈 Performance

- **Concurrent Processing**: Multi-threaded request handling
- **Caching**: Vector similarity result caching
- **Batch Operations**: Efficient database operations
- **Auto-scaling**: Kubernetes HPA and Cloud Run scaling
- **Resource Optimization**: Memory and CPU tuning

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes with tests
4. Run code quality checks
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**"Workflow not initialized" Error**
- Verify all environment variables are set
- Check GCP service account permissions
- Validate Secret Manager access

**Confluence Authentication Failed**
- Verify API token is valid and not expired
- Check username format (email address)
- Ensure user has read permissions

**SpannerGraph Connection Failed**
- Verify Spanner instance and database exist
- Run database initialization script
- Check IAM permissions for Spanner access

**Vector Store Errors**
- Confirm Spanner vector table exists
- Validate embedding model availability
- Check Vertex AI API quotas

### Logs and Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export ENABLE_DEBUG_LOGGING=true

# View application logs
tail -f logs/application.log

# Check container logs
docker logs compliance-api
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting guide above
2. Review system logs for error details  
3. Verify GCP permissions and quotas
4. Test with sample policy data

---

**Built with ❤️ using LangChain, LangGraph, and Google Vertex AI**
'''
}

# Create scripts directory
os.makedirs('scripts', exist_ok=True)

# Write documentation and scripts
for filepath, content in docs_and_scripts.items():
    with open(filepath, 'w') as f:
        f.write(content)
    
    # Make Python scripts executable
    if filepath.endswith('.py'):
        os.chmod(filepath, 0o755)

print("✅ Created comprehensive documentation and database initialization scripts")
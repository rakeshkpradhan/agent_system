# Agentic AI Compliance Verification System

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
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
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
gcloud run deploy compliance-api \
  --image gcr.io/PROJECT_ID/compliance-api \
  --platform managed \
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
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
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

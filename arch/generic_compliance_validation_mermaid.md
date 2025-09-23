
# Generic Compliance Validation System - Complete Mermaid Architecture

## System Overview
**Universal Multi-Policy Compliance Validation System** designed to handle any compliance policy dynamically loaded from Spanner Graph. 

**Example Policies Supported:**
- **Policy 101 - Test Execution**: Test scripts, data, plans, outcomes, defects
- **Policy 201 - Security Compliance**: Security scans, vulnerability assessments, pen testing
- **Policy 301 - Deployment Validation**: Deployment procedures, rollback plans, monitoring
- **Policy 401 - Code Review**: Code quality, peer reviews, static analysis
- **Policy 501 - Documentation**: Technical documentation, API docs, user guides
- **...and any future policies added to Spanner Graph**

## 1. Generic System Architecture

```mermaid
graph TD
    %% External Systems & Triggers
    CMS[Change Management System<br/>Policy-Agnostic Triggers]:::external
    CONF[Confluence Evidence Repository<br/>Multi-Format Evidence<br/>- Test Documentation<br/>- Security Reports<br/>- Deployment Logs<br/>- Code Reviews]:::input

    %% LangGraph Generic Orchestration Layer
    subgraph "LangGraph Generic Compliance Validation Workflow"
        WFC[Workflow Controller<br/>Policy-Aware State Management]:::orchestrator

        subgraph "Generic Agent Pipeline"
            ESA[Evidence Summarizer Agent<br/>Universal Content Parser]:::agent
            PDA[Policy Discovery Agent<br/>Dynamic Rule Retrieval]:::agent
            CRA[Compliance Retrieval Agent<br/>Hybrid Context Builder]:::agent
            GEA[Generic Evaluation Agent<br/>Policy-Agnostic Assessment]:::agent
        end
    end

    %% Generic Knowledge Architecture
    subgraph "Multi-Policy Knowledge Store"
        SG[(Spanner Graph<br/>Generic Compliance Framework<br/>- Multiple Policies<br/>- Dynamic Rules<br/>- Policy Hierarchies<br/>- Cross-References)]:::database
        ADB[(AlloyDB Vector Store<br/>Multi-Domain Embeddings<br/>- Historical Evidence<br/>- Policy Examples<br/>- Domain Patterns)]:::database
    end

    %% AI/ML Services Layer
    subgraph "AI Services"
        EMB[Vertex AI Embeddings<br/>Multi-Domain Text Processing]:::aiservice
        GEMINI[Gemini 2.5 Pro<br/>Generic Compliance Reasoning]:::aiservice
    end

    %% Generic Policy Processing Pipeline
    subgraph "Dynamic Policy Processing"
        PID[Policy Identification<br/>Auto-Detection]:::policy
        RLD[Rule Loading<br/>Dynamic Retrieval]:::policy
        VCG[Validation Criteria<br/>Generation]:::policy
        AEF[Assessment Framework<br/>Policy-Specific]:::policy
    end

    %% Generic Output & Decision Layer
    subgraph "Universal Validation Results"
        GCD{Generic Compliance Decision<br/>COMPLIANT/NON_COMPLIANT/REVIEW}:::decision
        PER[Policy-Specific Evidence Report]:::output
        CAR[Compliance Assessment Report<br/>- Rule Analysis<br/>- Evidence Mapping<br/>- Recommendations]:::output
        ART[Audit Trail<br/>Multi-Policy History]:::output
    end

    %% Data Flow Connections
    CMS -->|Policy Context + Evidence URL| WFC
    CONF -->|Multi-Format Evidence| ESA

    %% Agent Workflow
    WFC -->|Initialize with Policy Context| ESA
    ESA -->|Parsed Evidence| PDA
    PDA -->|Policy Rules| CRA
    CRA -->|Enhanced Context| GEA

    %% Policy Processing
    PDA --> PID
    PID --> RLD
    RLD --> VCG
    VCG --> AEF

    %% Knowledge Retrieval
    PDA -->|Dynamic Policy Query| SG
    CRA -->|Multi-Domain Vector Search| ADB
    ESA -->|Generate Embeddings| EMB
    EMB -->|Store Evidence Vectors| ADB

    %% AI Processing
    GEA -->|Policy-Aware RAG Prompt| GEMINI
    GEMINI -->|Compliance Analysis| GCD

    %% Results Generation
    AEF --> GCD
    GCD -->|Status + Confidence| PER
    GCD -->|Detailed Analysis| CAR
    GCD -->|Compliance History| ART

    %% Styling
    classDef external fill:#e1e1e1,stroke:#333,stroke-width:2px,color:#000
    classDef input fill:#e6f3ff,stroke:#0066cc,stroke-width:2px,color:#000
    classDef orchestrator fill:#f0f8f0,stroke:#009900,stroke-width:3px,color:#000
    classDef agent fill:#e6ffe6,stroke:#00cc00,stroke-width:2px,color:#000
    classDef database fill:#cce6ff,stroke:#0066cc,stroke-width:2px,color:#000
    classDef aiservice fill:#ffe6cc,stroke:#ff6600,stroke-width:2px,color:#000
    classDef policy fill:#f0e6ff,stroke:#9900cc,stroke-width:2px,color:#000
    classDef decision fill:#fffacd,stroke:#daa520,stroke-width:3px,color:#000
    classDef output fill:#f0e6ff,stroke:#9900cc,stroke-width:2px,color:#000
```

**Key Generic Features:**
- **Policy-Agnostic Design**: Dynamically processes any compliance policy from Spanner Graph
- **Universal Evidence Parser**: Handles multi-format evidence (test docs, security reports, deployment logs)
- **Generic Agent Pipeline**: Policy-aware agents that adapt to different compliance domains
- **Multi-Policy Knowledge Store**: Supports unlimited compliance policies with cross-references
- **Dynamic Rule Loading**: Runtime retrieval and processing of policy-specific rules
- **Universal Decision Framework**: Consistent compliance assessment across all policy types

## 2. Generic Multi-Policy Agent Workflow

```mermaid
sequenceDiagram
    participant CMS as Change Management System
    participant WFC as Generic Workflow Controller
    participant ESA as Evidence Summarizer Agent
    participant PDA as Policy Discovery Agent
    participant CRA as Compliance Retrieval Agent
    participant GEA as Generic Evaluation Agent
    participant CONF as Confluence Repository
    participant SG as Spanner Graph (Multi-Policy)
    participant ADB as AlloyDB Vector Store
    participant EMB as Vertex AI Embeddings
    participant GEMINI as Gemini 2.5 Pro

    Note over CMS, GEMINI: Generic Multi-Policy Compliance Validation System

    CMS->>WFC: Trigger validation (Policy ID + Evidence URL)
    Note over WFC: Initialize Generic ValidationState<br/>Policy Context: Dynamic

    WFC->>ESA: Parse evidence content
    ESA->>CONF: Extract multi-format evidence
    CONF-->>ESA: Raw evidence data

    Note over ESA: Universal Content Analysis
    ESA->>ESA: Parse documentation structure
    ESA->>ESA: Extract key components
    ESA->>ESA: Classify evidence types
    ESA->>ESA: Generate content summary

    ESA->>EMB: Generate domain-agnostic embeddings
    EMB-->>ESA: Evidence vectors
    ESA->>WFC: Evidence analysis + embeddings

    WFC->>PDA: Discover applicable policies

    Note over PDA: Dynamic Policy Discovery
    PDA->>SG: Query policy catalog
    Note over SG: Multi-Policy Store<br/>Policy 101: Test Execution<br/>Policy 201: Security<br/>Policy 301: Deployment<br/>Policy 401: Code Review<br/>...Dynamic Policies
    SG-->>PDA: Applicable policies + rules

    PDA->>PDA: Identify policy context
    PDA->>PDA: Load policy-specific rules
    PDA->>WFC: Policy rules + validation criteria

    WFC->>CRA: Build compliance context

    par Hybrid Retrieval Strategy
        CRA->>SG: Query policy-specific rules
        Note over SG: Dynamic Rule Retrieval<br/>Policy-Specific Validation<br/>Cross-Policy References
        SG-->>CRA: Structured compliance rules
    and
        CRA->>ADB: Multi-domain vector search
        Note over ADB: Historical Evidence<br/>Similar Cases<br/>Domain Patterns<br/>Policy Examples
        ADB-->>CRA: Similar evidence patterns
    end

    CRA->>WFC: Hybrid compliance context

    WFC->>GEA: Execute generic evaluation

    Note over GEA: Policy-Agnostic Assessment
    GEA->>GEA: Build policy-aware RAG context
    GEA->>GEA: Generate dynamic evaluation criteria
    GEA->>GEA: Create compliance assessment prompt

    GEA->>GEMINI: Policy-specific compliance query
    Note over GEMINI: Dynamic Rule Analysis<br/>Evidence Mapping<br/>Policy-Specific Reasoning<br/>Cross-Rule Dependencies
    GEMINI-->>GEA: Compliance assessment

    GEA->>GEA: Parse policy-specific results
    GEA->>GEA: Generate recommendations
    GEA->>WFC: Generic compliance decision

    WFC->>CMS: Multi-policy validation results

    Note over CMS: COMPLIANT/NON_COMPLIANT<br/>+ Policy-Specific Analysis<br/>+ Evidence Mappings<br/>+ Remediation Plan
```

**Generic Workflow Steps:**
1. **Dynamic Policy Detection**: Auto-identify applicable compliance policies from context
2. **Universal Evidence Parsing**: Extract and classify evidence regardless of domain
3. **Policy-Specific Rule Loading**: Dynamically fetch relevant rules from Spanner Graph
4. **Multi-Domain Context Building**: Hybrid retrieval across policy domains
5. **Generic Compliance Assessment**: Policy-agnostic evaluation with domain expertise
6. **Universal Result Format**: Consistent output structure for all policy types

## 3. Generic Hybrid RAG Pipeline

```mermaid
graph TB
    subgraph "Multi-Format Evidence Input"
        EI[Evidence Input<br/>Any Policy Context]:::input
        EC[Evidence Content<br/>Universal Parser]:::process
        ET[Evidence Type<br/>Auto-Classification]:::process
    end

    subgraph "Dynamic Policy Context"
        PC[Policy Context<br/>Runtime Identification]:::policy
        PDR[Policy Discovery<br/>Automated Detection]:::policy
        PLC[Policy Loading<br/>Dynamic Rule Retrieval]:::policy
    end

    subgraph "Generic Hybrid Retrieval"
        GVR[Generic Vector Retrieval<br/>Multi-Domain Similarity]:::vector
        GGR[Generic Graph Retrieval<br/>Policy-Agnostic Structure]:::graph
        HRS[Hybrid Retrieval Strategy<br/>Context-Aware Combination]:::hybrid
    end

    subgraph "Multi-Domain Vector Pipeline"
        UVE[Universal Vector Embeddings<br/>Domain-Agnostic Processing]:::process
        MVS[Multi-Domain Vector Search<br/>Cross-Policy Similarity]:::process
        SPE[Similar Policy Evidence<br/>Historical Patterns]:::result
    end

    subgraph "Generic Knowledge Graph Pipeline"
        DGQ[Dynamic Graph Query<br/>Policy-Specific GQL]:::process
        PRT[Policy Rule Traversal<br/>Hierarchical Navigation]:::process
        GCR[Generic Compliance Rules<br/>Policy-Agnostic Structure]:::result
    end

    subgraph "Adaptive Context Integration"
        ACF[Adaptive Context Fusion<br/>Policy-Aware Weighting]:::integration
        DPE[Dynamic Prompt Engineering<br/>Policy-Specific Templates]:::integration
        ERP[Enhanced RAG Prompt<br/>Context + Rules + Examples]:::integration
    end

    subgraph "Generic LLM Processing"
        GLLM[Gemini 2.5 Pro<br/>Multi-Policy Reasoning]:::llm
        PRA[Policy-Specific Rule Analysis<br/>Dynamic Evaluation]:::analysis
        GCD[Generic Compliance Decision<br/>Policy-Agnostic Output]:::decision
    end

    %% Flow connections
    EI --> EC
    EC --> ET
    ET --> UVE

    PC --> PDR
    PDR --> PLC
    PLC --> DGQ

    UVE --> MVS
    MVS --> SPE

    DGQ --> PRT
    PRT --> GCR

    SPE --> ACF
    GCR --> ACF
    ACF --> DPE
    DPE --> ERP
    ERP --> GLLM

    GLLM --> PRA
    PRA --> GCD

    GVR -.-> UVE
    GGR -.-> DGQ
    HRS -.-> ACF

    %% Styling
    classDef input fill:#e6f3ff,stroke:#0066cc,stroke-width:2px
    classDef policy fill:#f0e6ff,stroke:#9900cc,stroke-width:2px
    classDef vector fill:#ffe6e6,stroke:#cc0000,stroke-width:2px
    classDef graph fill:#e6ffe6,stroke:#009900,stroke-width:2px
    classDef hybrid fill:#fff2cc,stroke:#d6b656,stroke-width:2px
    classDef process fill:#fff2e6,stroke:#ff8800,stroke-width:2px
    classDef result fill:#f0e6ff,stroke:#9900cc,stroke-width:2px
    classDef integration fill:#fffacd,stroke:#daa520,stroke-width:2px
    classDef llm fill:#e6f2ff,stroke:#0044cc,stroke-width:3px
    classDef analysis fill:#f5f5dc,stroke:#8b7d6b,stroke-width:2px
    classDef decision fill:#f0f8f0,stroke:#009900,stroke-width:2px
```

**Multi-Policy RAG Features:**
- **Domain-Agnostic Vector Search**: Cross-policy evidence similarity matching
- **Dynamic Graph Traversal**: Policy-specific rule navigation in Spanner Graph
- **Adaptive Context Fusion**: Policy-aware weighting of graph vs vector results
- **Dynamic Prompt Engineering**: Policy-specific assessment templates
- **Multi-Domain Reasoning**: LLM adaptation to different compliance domains

## 4. Generic Multi-Policy Database Schema

```mermaid
erDiagram
    COMPLIANCE_POLICY_CATALOG {
        string policy_id PK
        string policy_number
        string policy_name
        string policy_category
        string description
        string version
        json policy_metadata
        string status
        datetime effective_date
        datetime created_at
        datetime updated_at
    }

    GENERIC_COMPLIANCE_RULE {
        string rule_id PK
        string policy_id FK
        string rule_number
        string rule_name
        string rule_category
        text description
        json validation_criteria
        string severity_level
        json rule_parameters
        string rule_type
        datetime created_at
    }

    POLICY_RULE_HIERARCHY {
        string id PK
        string parent_rule_id FK
        string child_rule_id FK
        string relationship_type
        json dependency_metadata
        datetime created_at
    }

    EVIDENCE_TYPE_MAPPING {
        string id PK
        string policy_id FK
        string evidence_type
        string evidence_category
        json required_attributes
        json validation_patterns
        boolean mandatory
        string extraction_method
    }

    CROSS_POLICY_REFERENCES {
        string id PK
        string source_policy_id FK
        string target_policy_id FK
        string reference_type
        json reference_metadata
        string impact_level
    }

    GENERIC_VALIDATION_CRITERIA {
        string criteria_id PK
        string rule_id FK
        string criteria_name
        text criteria_description
        json validation_logic
        string validation_method
        float threshold_value
        json expected_patterns
    }

    MULTI_DOMAIN_EVIDENCE_EMBEDDINGS {
        int id PK
        text evidence_text
        string evidence_type
        string policy_context
        string domain_category
        string compliance_outcome
        vector embedding
        json evidence_metadata
        json policy_mappings
        string source_url
        datetime created_at
    }

    GENERIC_VALIDATION_HISTORY {
        string validation_id PK
        string change_request_id
        string policy_id FK
        string evidence_url
        string validation_status
        json policy_results
        json rule_assessments
        json evidence_analysis
        float overall_confidence
        json agent_execution_trace
        json recommendations
        datetime validated_at
        datetime completed_at
    }

    POLICY_EVIDENCE_PATTERNS {
        string pattern_id PK
        string policy_id FK
        string pattern_name
        text pattern_description
        json pattern_template
        json matching_criteria
        float success_rate
        json usage_statistics
        datetime created_at
    }

    COMPLIANCE_ASSESSMENT_TEMPLATES {
        string template_id PK
        string policy_id FK
        string template_name
        text prompt_template
        json assessment_criteria
        json output_format
        string llm_parameters
        datetime created_at
    }

    %% Relationships - Spanner Graph Structure
    COMPLIANCE_POLICY_CATALOG ||--o{ GENERIC_COMPLIANCE_RULE : "contains"
    GENERIC_COMPLIANCE_RULE ||--o{ POLICY_RULE_HIERARCHY : "parent_rule"
    GENERIC_COMPLIANCE_RULE ||--o{ POLICY_RULE_HIERARCHY : "child_rule"
    COMPLIANCE_POLICY_CATALOG ||--o{ EVIDENCE_TYPE_MAPPING : "defines_evidence_types"
    COMPLIANCE_POLICY_CATALOG ||--o{ CROSS_POLICY_REFERENCES : "source_policy"
    COMPLIANCE_POLICY_CATALOG ||--o{ CROSS_POLICY_REFERENCES : "target_policy"
    GENERIC_COMPLIANCE_RULE ||--o{ GENERIC_VALIDATION_CRITERIA : "has_criteria"
    COMPLIANCE_POLICY_CATALOG ||--o{ POLICY_EVIDENCE_PATTERNS : "defines_patterns"
    COMPLIANCE_POLICY_CATALOG ||--o{ COMPLIANCE_ASSESSMENT_TEMPLATES : "has_templates"

    %% Relationships - AlloyDB Vector Store
    MULTI_DOMAIN_EVIDENCE_EMBEDDINGS }o--|| COMPLIANCE_POLICY_CATALOG : "belongs_to_policy"
    GENERIC_VALIDATION_HISTORY }o--|| COMPLIANCE_POLICY_CATALOG : "validates_against"
    GENERIC_VALIDATION_HISTORY }o--o{ MULTI_DOMAIN_EVIDENCE_EMBEDDINGS : "analyzes"
```

**Schema Features:**
- **Policy Catalog**: Central registry of all compliance policies
- **Generic Rule Structure**: Flexible rule definition supporting any policy type
- **Policy Hierarchies**: Support for rule dependencies and cross-references
- **Evidence Type Mapping**: Dynamic evidence classification per policy
- **Cross-Policy References**: Links between related policies and rules
- **Multi-Domain Embeddings**: Vector storage for all evidence types
- **Generic Assessment Templates**: LLM prompt templates per policy type

## Multi-Policy Support Examples

### Policy 101 - Test Execution
```json
{
  "policy_id": "POL-101",
  "policy_name": "Test_Execution",
  "rules": [
    {"rule_number": "1", "description": "Test Evidence consists of test scripts, test data and test plan"},
    {"rule_number": "2", "description": "Test executed traceable to functional and non functional requirements"},
    {"rule_number": "3", "description": "Test outcomes includes expected results vs actual results"},
    {"rule_number": "4", "description": "Any deviation from test strategy are documented and approved"},
    {"rule_number": "5", "description": "Identified defects are documented, reviewed and approved"}
  ]
}
```

### Policy 201 - Security Compliance  
```json
{
  "policy_id": "POL-201",
  "policy_name": "Security_Compliance",
  "rules": [
    {"rule_number": "1", "description": "Security scanning completed for all code changes"},
    {"rule_number": "2", "description": "Vulnerability assessment results documented and remediated"},
    {"rule_number": "3", "description": "Penetration testing performed for high-risk changes"},
    {"rule_number": "4", "description": "Security approvals obtained from InfoSec team"},
    {"rule_number": "5", "description": "Compliance with security standards validated"}
  ]
}
```

### Policy 301 - Deployment Validation
```json
{
  "policy_id": "POL-301", 
  "policy_name": "Deployment_Validation",
  "rules": [
    {"rule_number": "1", "description": "Deployment procedures documented and approved"},
    {"rule_number": "2", "description": "Rollback plan tested and verified"},
    {"rule_number": "3", "description": "Production monitoring and alerting configured"},
    {"rule_number": "4", "description": "Database migration scripts validated"},
    {"rule_number": "5", "description": "Performance impact assessment completed"}
  ]
}
```

## Generic Technology Stack

| Component | Technology | Generic Purpose |
|-----------|------------|-----------------|
| **Workflow Engine** | LangGraph | Policy-agnostic multi-agent orchestration |
| **Knowledge Graph** | Spanner Graph | Universal compliance policy and rule storage |
| **Vector Database** | AlloyDB | Multi-domain evidence embeddings and similarity |
| **LLM Engine** | Gemini 2.5 Pro | Generic compliance reasoning across all domains |
| **Embeddings** | Vertex AI | Domain-agnostic text-to-vector transformation |
| **Evidence Source** | Confluence | Universal documentation and evidence repository |

## Extensibility Features

### Adding New Policies
1. **Define Policy Structure** in Spanner Graph with rules and validation criteria
2. **Create Evidence Mappings** for policy-specific evidence types  
3. **Configure Assessment Templates** for LLM evaluation prompts
4. **Add Domain Examples** to AlloyDB vector store for similarity matching
5. **System Automatically Adapts** - no code changes required

### Cross-Policy Support
- **Policy Dependencies**: Rules that reference other policies
- **Shared Evidence**: Evidence that satisfies multiple policies
- **Combined Assessments**: Multi-policy validation in single workflow
- **Policy Conflicts**: Detection and resolution of conflicting requirements

### Domain Expansion
- **New Evidence Types**: Automatic classification and processing
- **Custom Validation Logic**: Policy-specific assessment criteria
- **Domain Expertise**: LLM adaptation to specialized compliance areas
- **Industry Standards**: Support for regulatory and industry-specific policies

This generic architecture provides unlimited scalability for compliance validation across any domain or policy type while maintaining consistent quality and explainability.

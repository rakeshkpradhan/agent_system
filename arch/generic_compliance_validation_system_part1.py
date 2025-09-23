
"""
Generic Multi-Policy Compliance Validation System
Universal Implementation for Dynamic Policy Processing

Supports unlimited compliance policies including:
- Policy 101: Test Execution
- Policy 201: Security Compliance  
- Policy 301: Deployment Validation
- Policy 401: Code Review
- Policy 501: Documentation
- ...Future policies added to Spanner Graph

Architecture: LangGraph + Spanner Graph + AlloyDB + Gemini 2.5 Pro
Design: Policy-agnostic with dynamic rule loading and processing
"""

import os
import asyncio
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from abc import ABC, abstractmethod

# LangGraph and LangChain imports
from langgraph.graph import Graph, StateGraph, START, END
from langgraph.channels import LastValue
from langgraph.checkpoint.memory import MemorySaver
from langchain.embeddings import VertexAIEmbeddings

# Google Cloud and Database imports
import psycopg2
from google.cloud.sql.connector import Connector
from google.cloud import spanner
import vertexai
from vertexai.generative_models import GenerativeModel

# Web scraping and utilities
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ====== ENUMS AND CONSTANTS ======

class ComplianceStatus(Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    ERROR = "ERROR"
    PARTIAL_COMPLIANT = "PARTIAL_COMPLIANT"

class PolicyCategory(Enum):
    TEST_EXECUTION = "test_execution"
    SECURITY_COMPLIANCE = "security_compliance"
    DEPLOYMENT_VALIDATION = "deployment_validation"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    GENERIC = "generic"

class EvidenceType(Enum):
    TEST_DOCUMENTATION = "test_documentation"
    SECURITY_REPORT = "security_report"
    DEPLOYMENT_LOG = "deployment_log"
    CODE_REVIEW_RECORD = "code_review_record"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    UNKNOWN = "unknown"

# ====== CONFIGURATION ======

@dataclass
class GenericComplianceConfig:
    """Universal configuration for multi-policy compliance validation"""

    # Google Cloud Configuration
    project_id: str = os.getenv("GOOGLE_CLOUD_PROJECT")
    location: str = os.getenv("VERTEX_AI_LOCATION", "us-central1")

    # Spanner Graph Configuration - Universal Policy Store
    spanner_instance_id: str = os.getenv("SPANNER_INSTANCE_ID")
    spanner_database_id: str = os.getenv("SPANNER_DATABASE_ID")

    # AlloyDB Configuration - Multi-Domain Vector Store
    alloydb_instance: str = os.getenv("ALLOYDB_INSTANCE")
    alloydb_database: str = os.getenv("ALLOYDB_DATABASE", "generic_compliance_db")
    alloydb_user: str = os.getenv("ALLOYDB_USER", "postgres")
    alloydb_password: str = os.getenv("ALLOYDB_PASSWORD")

    # AI Model Configuration
    embedding_model: str = "text-embedding-004"
    llm_model: str = "gemini-2.5-pro"

    # Generic Validation Configuration
    similarity_threshold: float = 0.75
    max_retrieved_examples: int = 15
    confidence_threshold: float = 0.8

    # Policy Discovery Configuration
    auto_policy_detection: bool = True
    multi_policy_support: bool = True
    cross_policy_validation: bool = True

    # Evidence Processing Configuration
    max_evidence_length: int = 25000
    supported_evidence_formats: List[str] = field(default_factory=lambda: [
        "confluence", "html", "markdown", "pdf", "docx", "txt"
    ])

# Initialize configuration and Vertex AI
config = GenericComplianceConfig()
vertexai.init(project=config.project_id, location=config.location)

# ====== POLICY MODELS ======

@dataclass
class CompliancePolicyModel:
    """Universal model for compliance policies"""
    policy_id: str
    policy_number: str
    policy_name: str
    policy_category: str
    description: str
    version: str
    status: str
    effective_date: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    evidence_types: List[Dict[str, Any]] = field(default_factory=list)
    assessment_template: Dict[str, Any] = field(default_factory=dict)
    cross_references: List[str] = field(default_factory=list)

@dataclass
class ComplianceRuleModel:
    """Universal model for compliance rules"""
    rule_id: str
    rule_number: str
    rule_name: str
    rule_category: str
    description: str
    validation_criteria: Dict[str, Any]
    severity_level: str
    rule_parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

# ====== STATE MANAGEMENT ======

@dataclass
class GenericValidationState:
    """Universal state for multi-policy compliance validation"""

    # Input Information
    confluence_url: str = ""
    change_request_id: str = ""
    requested_policies: List[str] = field(default_factory=list)  # User can specify policies

    # Policy Discovery
    detected_policies: List[CompliancePolicyModel] = field(default_factory=list)
    active_policy: Optional[CompliancePolicyModel] = None
    policy_context: Dict[str, Any] = field(default_factory=dict)

    # Evidence Processing
    raw_evidence: str = ""
    evidence_type: EvidenceType = EvidenceType.UNKNOWN
    evidence_components: Dict[str, str] = field(default_factory=dict)
    evidence_analysis: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Generic Compliance Context
    applicable_rules: List[ComplianceRuleModel] = field(default_factory=list)
    similar_evidence_examples: List[Dict[str, Any]] = field(default_factory=list)
    cross_policy_references: List[Dict[str, Any]] = field(default_factory=list)

    # Rule Validation Results
    rule_assessments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    policy_compliance_results: Dict[str, Any] = field(default_factory=dict)

    # RAG Processing
    rag_context: str = ""
    enhanced_prompt: str = ""
    llm_response: str = ""

    # Final Assessment
    compliance_decision: Dict[str, Any] = field(default_factory=dict)
    final_status: ComplianceStatus = ComplianceStatus.REQUIRES_REVIEW
    confidence_score: float = 0.0

    # Multi-Policy Results
    multi_policy_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Metadata and Tracking
    error_messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamps: Dict[str, str] = field(default_factory=dict)
    agent_traces: Dict[str, Any] = field(default_factory=dict)

# ====== GENERIC AGENT IMPLEMENTATIONS ======

class EvidenceSummarizerAgent:
    """Universal agent for parsing evidence from any source format"""

    def __init__(self, config: GenericComplianceConfig):
        self.config = config
        self.llm = GenerativeModel(config.llm_model)
        self.embeddings = VertexAIEmbeddings(
            model_name=config.embedding_model,
            project=config.project_id
        )

    async def process(self, state: GenericValidationState) -> GenericValidationState:
        """Universal evidence processing for any compliance domain"""

        state.timestamps["evidence_processing_start"] = datetime.now().isoformat()

        try:
            # Step 1: Extract raw content from evidence source
            state.raw_evidence = await self._extract_evidence_content(state.confluence_url)

            # Step 2: Auto-detect evidence type
            state.evidence_type = await self._classify_evidence_type(state.raw_evidence)

            # Step 3: Parse evidence components generically
            state.evidence_components = await self._parse_generic_evidence_components(
                state.raw_evidence, state.evidence_type
            )

            # Step 4: Analyze evidence quality and completeness
            state.evidence_analysis = await self._analyze_evidence_quality(
                state.evidence_components, state.evidence_type
            )

            # Step 5: Store processing trace
            state.agent_traces["evidence_summarizer"] = {
                "content_length": len(state.raw_evidence),
                "evidence_type": state.evidence_type.value,
                "components_found": len(state.evidence_components),
                "components_analyzed": len(state.evidence_analysis),
                "processing_method": "universal_parser",
                "execution_time": datetime.now().isoformat()
            }

            state.timestamps["evidence_processing_complete"] = datetime.now().isoformat()

        except Exception as e:
            error_msg = f"Evidence processing failed: {str(e)}"
            state.error_messages.append(error_msg)
            logger.error(error_msg)

        return state

    async def _extract_evidence_content(self, evidence_url: str) -> str:
        """Universal evidence extraction supporting multiple formats"""

        try:
            headers = {
                'User-Agent': 'GenericComplianceValidator/1.0 (Multi-Policy Support)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }

            response = requests.get(evidence_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Handle different content types
            content_type = response.headers.get('content-type', '').lower()

            if 'html' in content_type:
                return self._parse_html_content(response.content)
            elif 'json' in content_type:
                return self._parse_json_content(response.text)
            elif 'xml' in content_type:
                return self._parse_xml_content(response.content)
            else:
                return self._parse_text_content(response.text)

        except Exception as e:
            raise Exception(f"Failed to extract evidence from {evidence_url}: {str(e)}")

    def _parse_html_content(self, html_content: bytes) -> str:
        """Parse HTML content from Confluence or other web sources"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove non-content elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'sidebar', 'aside']):
            element.decompose()

        # Extract main content
        main_content = (soup.find('div', {'id': 'content'}) or 
                       soup.find('main') or 
                       soup.find('article') or 
                       soup.body or 
                       soup)

        if main_content:
            text_content = main_content.get_text(separator=' ', strip=True)
        else:
            text_content = soup.get_text(separator=' ', strip=True)

        # Clean and normalize
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        clean_content = ' '.join(lines)

        return clean_content[:self.config.max_evidence_length]

    def _parse_json_content(self, json_content: str) -> str:
        """Parse JSON structured evidence"""
        try:
            data = json.loads(json_content)
            return json.dumps(data, indent=2)[:self.config.max_evidence_length]
        except json.JSONDecodeError:
            return json_content[:self.config.max_evidence_length]

    def _parse_xml_content(self, xml_content: bytes) -> str:
        """Parse XML structured evidence"""
        soup = BeautifulSoup(xml_content, 'xml')
        return soup.get_text(separator=' ', strip=True)[:self.config.max_evidence_length]

    def _parse_text_content(self, text_content: str) -> str:
        """Parse plain text evidence"""
        return text_content.strip()[:self.config.max_evidence_length]

    async def _classify_evidence_type(self, content: str) -> EvidenceType:
        """Auto-classify evidence type using content analysis"""

        classification_prompt = f"""
        Analyze the following evidence content and classify its type:

        Content Preview: {content[:2000]}

        Classify into one of these evidence types:
        1. TEST_DOCUMENTATION - Test plans, test cases, test results, test scripts
        2. SECURITY_REPORT - Security scans, vulnerability assessments, security reviews
        3. DEPLOYMENT_LOG - Deployment procedures, deployment results, infrastructure logs
        4. CODE_REVIEW_RECORD - Code reviews, pull requests, static analysis results
        5. TECHNICAL_DOCUMENTATION - API docs, architecture docs, user guides
        6. UNKNOWN - Cannot determine or mixed content

        Look for key indicators:
        - Test keywords: test, testing, cases, scripts, execution, results, defects
        - Security keywords: security, vulnerability, scan, penetration, assessment
        - Deployment keywords: deployment, deploy, release, infrastructure, environment
        - Code review keywords: review, pull request, code quality, static analysis
        - Documentation keywords: documentation, API, architecture, guide, manual

        Response: Return only the classification (e.g., "TEST_DOCUMENTATION")
        """

        try:
            response = await self.llm.generate_content_async(classification_prompt)
            classification = response.text.strip().upper()

            # Map to enum
            classification_mapping = {
                "TEST_DOCUMENTATION": EvidenceType.TEST_DOCUMENTATION,
                "SECURITY_REPORT": EvidenceType.SECURITY_REPORT,
                "DEPLOYMENT_LOG": EvidenceType.DEPLOYMENT_LOG,
                "CODE_REVIEW_RECORD": EvidenceType.CODE_REVIEW_RECORD,
                "TECHNICAL_DOCUMENTATION": EvidenceType.TECHNICAL_DOCUMENTATION,
                "UNKNOWN": EvidenceType.UNKNOWN
            }

            return classification_mapping.get(classification, EvidenceType.UNKNOWN)

        except Exception as e:
            logger.warning(f"Evidence classification failed: {str(e)}")
            return EvidenceType.UNKNOWN

    async def _parse_generic_evidence_components(self, content: str, 
                                               evidence_type: EvidenceType) -> Dict[str, str]:
        """Parse evidence components based on auto-detected type"""

        # Define type-specific component extraction templates
        component_templates = {
            EvidenceType.TEST_DOCUMENTATION: [
                "test_scripts", "test_data", "test_plans", "test_results", 
                "defect_reports", "requirements_mapping", "test_coverage"
            ],
            EvidenceType.SECURITY_REPORT: [
                "vulnerability_scan", "security_assessment", "penetration_testing",
                "security_approvals", "remediation_plan", "compliance_check"
            ],
            EvidenceType.DEPLOYMENT_LOG: [
                "deployment_procedure", "rollback_plan", "environment_config",
                "deployment_results", "monitoring_setup", "performance_metrics"
            ],
            EvidenceType.CODE_REVIEW_RECORD: [
                "code_changes", "review_comments", "static_analysis",
                "code_quality_metrics", "review_approvals", "technical_debt"
            ],
            EvidenceType.TECHNICAL_DOCUMENTATION: [
                "api_documentation", "architecture_design", "user_guides",
                "technical_specifications", "installation_guides", "troubleshooting"
            ],
            EvidenceType.UNKNOWN: [
                "main_content", "supporting_documents", "references",
                "metadata", "attachments", "additional_info"
            ]
        }

        expected_components = component_templates.get(evidence_type, component_templates[EvidenceType.UNKNOWN])

        parsing_prompt = f"""
        Analyze the following evidence content and extract components based on the evidence type: {evidence_type.value}

        Evidence Content:
        {content[:12000]}

        Extract and identify these components if present:
        {', '.join(expected_components)}

        For each component found, provide:
        - Detailed description of what was found
        - Key content and specifics
        - Quality assessment (comprehensive/adequate/incomplete/missing)

        Format your response as:
        COMPONENT_NAME: [detailed findings or "NOT_FOUND"]

        Example format:
        TEST_SCRIPTS: Found automated test scripts using Selenium framework with 45 test cases covering user authentication flows...
        TEST_DATA: Comprehensive test data sets including positive and negative test scenarios...

        If a component is not found, clearly state "NOT_FOUND".
        """

        try:
            response = await self.llm.generate_content_async(parsing_prompt)
            parsed_content = response.text

            # Extract components from LLM response
            components = {}
            current_component = None
            current_content = []

            for line in parsed_content.split('\n'):
                line = line.strip()

                # Check for component headers
                for component_name in expected_components:
                    if line.upper().startswith(f"{component_name.upper()}:"):
                        # Save previous component
                        if current_component and current_content:
                            components[current_component] = ' '.join(current_content)

                        # Start new component
                        current_component = component_name
                        content_part = line.split(':', 1)[1].strip()
                        current_content = [content_part] if content_part else []
                        break
                else:
                    # Continue current component content
                    if current_component and line:
                        current_content.append(line)

            # Save the last component
            if current_component and current_content:
                components[current_component] = ' '.join(current_content)

            return components

        except Exception as e:
            logger.error(f"Generic component parsing failed: {str(e)}")
            return {"main_content": content[:5000]}

    async def _analyze_evidence_quality(self, components: Dict[str, str], 
                                       evidence_type: EvidenceType) -> Dict[str, Dict[str, Any]]:
        """Analyze quality and completeness of evidence components"""

        analysis_results = {}

        for component_name, component_content in components.items():

            if not component_content or component_content.upper() in ['NOT_FOUND', 'MISSING']:
                analysis_results[component_name] = {
                    "present": False,
                    "quality_score": 0.0,
                    "completeness_score": 0.0,
                    "relevance_score": 0.0,
                    "issues": [f"{component_name} is missing or not documented"],
                    "recommendations": [f"Provide comprehensive {component_name} documentation"],
                    "content_summary": "Component not found",
                    "evidence_type_alignment": 0.0
                }
                continue

            # Quality analysis prompt
            quality_prompt = f"""
            Analyze this evidence component for quality and compliance readiness:

            Component: {component_name}
            Evidence Type: {evidence_type.value}
            Content: {component_content[:3000]}

            Evaluate based on these universal criteria:
            1. Quality: Professional standards, clarity, completeness
            2. Completeness: All necessary information present
            3. Relevance: Alignment with component purpose and evidence type
            4. Evidence Type Alignment: How well it fits the detected evidence type

            Provide scores (0.0 to 1.0) and specific feedback:

            QUALITY_SCORE: [0.0-1.0]
            COMPLETENESS_SCORE: [0.0-1.0]
            RELEVANCE_SCORE: [0.0-1.0]
            EVIDENCE_TYPE_ALIGNMENT: [0.0-1.0]

            STRENGTHS: [list key strengths]
            ISSUES: [list specific issues and gaps]
            RECOMMENDATIONS: [specific improvement recommendations]
            CONTENT_SUMMARY: [brief summary of component content]
            """

            try:
                response = await self.llm.generate_content_async(quality_prompt)
                analysis_text = response.text

                # Parse analysis results
                analysis = {
                    "present": True,
                    "content_length": len(component_content),
                    "quality_score": self._extract_score(analysis_text, "QUALITY_SCORE"),
                    "completeness_score": self._extract_score(analysis_text, "COMPLETENESS_SCORE"),
                    "relevance_score": self._extract_score(analysis_text, "RELEVANCE_SCORE"),
                    "evidence_type_alignment": self._extract_score(analysis_text, "EVIDENCE_TYPE_ALIGNMENT"),
                    "strengths": self._extract_list_items(analysis_text, "STRENGTHS"),
                    "issues": self._extract_list_items(analysis_text, "ISSUES"),
                    "recommendations": self._extract_list_items(analysis_text, "RECOMMENDATIONS"),
                    "content_summary": self._extract_section(analysis_text, "CONTENT_SUMMARY")
                }

                analysis_results[component_name] = analysis

            except Exception as e:
                logger.warning(f"Quality analysis failed for {component_name}: {str(e)}")
                analysis_results[component_name] = {
                    "present": True,
                    "content_length": len(component_content),
                    "quality_score": 0.6,
                    "completeness_score": 0.6,
                    "relevance_score": 0.6,
                    "evidence_type_alignment": 0.6,
                    "issues": [f"Quality analysis failed: {str(e)}"],
                    "recommendations": ["Manual review recommended"],
                    "content_summary": component_content[:200] + "...",
                    "analysis_method": "fallback"
                }

        return analysis_results

    def _extract_score(self, text: str, score_name: str) -> float:
        """Extract numerical score from analysis text"""
        pattern = rf'{score_name}:\s*([0-9]*\.?[0-9]+)'
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
        return 0.6  # Default moderate score

    def _extract_list_items(self, text: str, section_name: str) -> List[str]:
        """Extract list items from analysis text"""
        pattern = rf'{section_name}:\s*(.+?)(?=\n[A-Z_]+:|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            items = [item.strip('- ').strip() for item in content.split('\n') 
                    if item.strip() and (item.strip().startswith('-') or item.strip().startswith('•'))]
            return items[:5]  # Limit to 5 items
        return []

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract section content from analysis text"""
        pattern = rf'{section_name}:\s*(.+?)(?=\n[A-Z_]+:|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            return content[:400] + "..." if len(content) > 400 else content
        return "No summary available"


class PolicyDiscoveryAgent:
    """Universal agent for discovering and loading applicable compliance policies"""

    def __init__(self, config: GenericComplianceConfig):
        self.config = config
        self.spanner_client = spanner.Client(project=config.project_id)
        self.llm = GenerativeModel(config.llm_model)

    async def process(self, state: GenericValidationState) -> GenericValidationState:
        """Discover applicable policies and load their rules dynamically"""

        state.timestamps["policy_discovery_start"] = datetime.now().isoformat()

        try:
            # Step 1: Auto-detect applicable policies if not specified
            if not state.requested_policies:
                state.detected_policies = await self._auto_detect_policies(
                    state.raw_evidence, state.evidence_type
                )
            else:
                state.detected_policies = await self._load_requested_policies(state.requested_policies)

            # Step 2: Select primary policy for validation
            if state.detected_policies:
                state.active_policy = state.detected_policies[0]  # Primary policy

            # Step 3: Load policy-specific rules and criteria
            if state.active_policy:
                state.applicable_rules = await self._load_policy_rules(state.active_policy.policy_id)
                state.policy_context = await self._build_policy_context(state.active_policy)

            # Step 4: Handle multi-policy scenarios
            if self.config.multi_policy_support and len(state.detected_policies) > 1:
                state.cross_policy_references = await self._identify_cross_policy_references(
                    state.detected_policies
                )

            # Step 5: Store processing trace
            state.agent_traces["policy_discovery"] = {
                "requested_policies": state.requested_policies,
                "detected_policies_count": len(state.detected_policies),
                "active_policy_id": state.active_policy.policy_id if state.active_policy else None,
                "applicable_rules_count": len(state.applicable_rules),
                "multi_policy_enabled": self.config.multi_policy_support,
                "cross_references_found": len(state.cross_policy_references),
                "execution_time": datetime.now().isoformat()
            }

            state.timestamps["policy_discovery_complete"] = datetime.now().isoformat()

        except Exception as e:
            error_msg = f"Policy discovery failed: {str(e)}"
            state.error_messages.append(error_msg)
            logger.error(error_msg)

        return state

    async def _auto_detect_policies(self, evidence_content: str, 
                                   evidence_type: EvidenceType) -> List[CompliancePolicyModel]:
        """Automatically detect applicable policies based on evidence content"""

        detection_prompt = f"""
        Analyze the evidence content and determine which compliance policies are applicable:

        Evidence Type: {evidence_type.value}
        Evidence Content: {evidence_content[:5000]}

        Available Policy Categories:
        1. TEST_EXECUTION - Test plans, test scripts, test results, defect management
        2. SECURITY_COMPLIANCE - Security scans, vulnerability assessments, security reviews
        3. DEPLOYMENT_VALIDATION - Deployment procedures, rollback plans, infrastructure
        4. CODE_REVIEW - Code reviews, static analysis, code quality
        5. DOCUMENTATION - Technical documentation, API docs, user guides

        Based on the evidence content, identify the most applicable policy categories.
        Consider:
        - Primary content themes
        - Evidence structure and format
        - Domain-specific terminology
        - Process indicators

        Response format (return applicable categories, primary first):
        PRIMARY: [most applicable category]
        SECONDARY: [secondary applicable categories, if any]

        Example:
        PRIMARY: TEST_EXECUTION
        SECONDARY: SECURITY_COMPLIANCE, CODE_REVIEW
        """

        try:
            response = await self.llm.generate_content_async(detection_prompt)
            detection_text = response.text

            # Parse detection results
            primary_policies = []
            secondary_policies = []

            for line in detection_text.split('\n'):
                line = line.strip()
                if line.startswith("PRIMARY:"):
                    primary_category = line.split(":", 1)[1].strip()
                    primary_policies.append(primary_category)
                elif line.startswith("SECONDARY:"):
                    secondary_categories = line.split(":", 1)[1].strip()
                    secondary_policies.extend([cat.strip() for cat in secondary_categories.split(",")])

            # Load detected policies from Spanner Graph
            all_detected = primary_policies + secondary_policies
            policies = []

            for category in all_detected:
                if category:
                    policy_models = await self._load_policies_by_category(category.lower())
                    policies.extend(policy_models)

            return policies

        except Exception as e:
            logger.warning(f"Auto-detection failed: {str(e)}, using evidence type mapping")
            return await self._fallback_policy_detection(evidence_type)

    async def _fallback_policy_detection(self, evidence_type: EvidenceType) -> List[CompliancePolicyModel]:
        """Fallback policy detection based on evidence type mapping"""

        type_to_category_mapping = {
            EvidenceType.TEST_DOCUMENTATION: "test_execution",
            EvidenceType.SECURITY_REPORT: "security_compliance", 
            EvidenceType.DEPLOYMENT_LOG: "deployment_validation",
            EvidenceType.CODE_REVIEW_RECORD: "code_review",
            EvidenceType.TECHNICAL_DOCUMENTATION: "documentation",
            EvidenceType.UNKNOWN: "test_execution"  # Default to test execution
        }

        category = type_to_category_mapping.get(evidence_type, "test_execution")
        return await self._load_policies_by_category(category)

    async def _load_requested_policies(self, requested_policy_ids: List[str]) -> List[CompliancePolicyModel]:
        """Load specifically requested policies by ID"""

        policies = []
        for policy_id in requested_policy_ids:
            try:
                policy = await self._load_policy_by_id(policy_id)
                if policy:
                    policies.append(policy)
            except Exception as e:
                logger.warning(f"Failed to load policy {policy_id}: {str(e)}")

        return policies

    async def _load_policies_by_category(self, category: str) -> List[CompliancePolicyModel]:
        """Load policies from Spanner Graph by category"""

        try:
            instance = self.spanner_client.instance(self.config.spanner_instance_id)
            database = instance.database(self.config.spanner_database_id)

            # GQL query for policies by category
            gql_query = """
            GRAPH ComplianceGraph
            MATCH (policy:CompliancePolicy {policy_category: $category, status: 'ACTIVE'})
            OPTIONAL MATCH (policy)-[:CONTAINS]->(rule:ComplianceRule)
            RETURN 
                policy.policy_id as policy_id,
                policy.policy_number as policy_number,
                policy.policy_name as policy_name,
                policy.policy_category as policy_category,
                policy.description as description,
                policy.version as version,
                policy.status as status,
                policy.effective_date as effective_date,
                COUNT(rule) as rules_count
            ORDER BY policy.policy_number
            """

            with database.snapshot() as snapshot:
                results = snapshot.execute_sql(gql_query, params={"category": category})

                policies = []
                for row in results:
                    policy = CompliancePolicyModel(
                        policy_id=row[0],
                        policy_number=row[1],
                        policy_name=row[2],
                        policy_category=row[3],
                        description=row[4],
                        version=row[5],
                        status=row[6],
                        effective_date=row[7]
                    )
                    policies.append(policy)

                return policies

        except Exception as e:
            logger.warning(f"Spanner Graph query failed for category {category}: {str(e)}")
            return await self._get_default_policies_for_category(category)

    async def _load_policy_by_id(self, policy_id: str) -> Optional[CompliancePolicyModel]:
        """Load specific policy by ID from Spanner Graph"""

        try:
            instance = self.spanner_client.instance(self.config.spanner_instance_id)
            database = instance.database(self.config.spanner_database_id)

            gql_query = """
            GRAPH ComplianceGraph
            MATCH (policy:CompliancePolicy {policy_id: $policy_id})
            RETURN 
                policy.policy_id,
                policy.policy_number,
                policy.policy_name,
                policy.policy_category,
                policy.description,
                policy.version,
                policy.status,
                policy.effective_date
            """

            with database.snapshot() as snapshot:
                results = snapshot.execute_sql(gql_query, params={"policy_id": policy_id})

                for row in results:
                    return CompliancePolicyModel(
                        policy_id=row[0],
                        policy_number=row[1],
                        policy_name=row[2],
                        policy_category=row[3],
                        description=row[4],
                        version=row[5],
                        status=row[6],
                        effective_date=row[7]
                    )

                return None

        except Exception as e:
            logger.error(f"Failed to load policy {policy_id}: {str(e)}")
            return None

    async def _load_policy_rules(self, policy_id: str) -> List[ComplianceRuleModel]:
        """Load all rules for a specific policy"""

        try:
            instance = self.spanner_client.instance(self.config.spanner_instance_id)
            database = instance.database(self.config.spanner_database_id)

            gql_query = """
            GRAPH ComplianceGraph
            MATCH (policy:CompliancePolicy {policy_id: $policy_id})-[:CONTAINS]->(rule:ComplianceRule)
            OPTIONAL MATCH (rule)-[:HAS_CRITERIA]->(criteria:ValidationCriteria)
            RETURN 
                rule.rule_id,
                rule.rule_number,
                rule.rule_name,
                rule.rule_category,
                rule.description,
                rule.validation_criteria,
                rule.severity_level,
                rule.rule_parameters,
                ARRAY_AGG(criteria.criteria_name) as criteria_names
            ORDER BY rule.rule_number
            """

            with database.snapshot() as snapshot:
                results = snapshot.execute_sql(gql_query, params={"policy_id": policy_id})

                rules = []
                for row in results:
                    rule = ComplianceRuleModel(
                        rule_id=row[0],
                        rule_number=row[1],
                        rule_name=row[2],
                        rule_category=row[3],
                        description=row[4],
                        validation_criteria=json.loads(row[5]) if row[5] else {},
                        severity_level=row[6],
                        rule_parameters=json.loads(row[7]) if row[7] else {}
                    )
                    rules.append(rule)

                return rules

        except Exception as e:
            logger.warning(f"Failed to load rules for policy {policy_id}: {str(e)}")
            return await self._get_default_rules_for_policy(policy_id)

    async def _get_default_policies_for_category(self, category: str) -> List[CompliancePolicyModel]:
        """Provide default policies when Spanner Graph is unavailable"""

        default_policies = {
            "test_execution": [
                CompliancePolicyModel(
                    policy_id="POL-101",
                    policy_number="Policy_101",
                    policy_name="Test_Execution",
                    policy_category="test_execution",
                    description="Test Execution Compliance Policy",
                    version="1.0",
                    status="ACTIVE",
                    effective_date="2024-01-01"
                )
            ],
            "security_compliance": [
                CompliancePolicyModel(
                    policy_id="POL-201", 
                    policy_number="Policy_201",
                    policy_name="Security_Compliance",
                    policy_category="security_compliance",
                    description="Security Compliance Policy",
                    version="1.0",
                    status="ACTIVE",
                    effective_date="2024-01-01"
                )
            ],
            "deployment_validation": [
                CompliancePolicyModel(
                    policy_id="POL-301",
                    policy_number="Policy_301",
                    policy_name="Deployment_Validation",
                    policy_category="deployment_validation",
                    description="Deployment Validation Policy",
                    version="1.0",
                    status="ACTIVE",
                    effective_date="2024-01-01"
                )
            ]
        }

        return default_policies.get(category, [])

    async def _get_default_rules_for_policy(self, policy_id: str) -> List[ComplianceRuleModel]:
        """Provide default rules when Spanner Graph is unavailable"""

        # Example default rules for Policy 101 - Test Execution
        if policy_id == "POL-101":
            return [
                ComplianceRuleModel(
                    rule_id="POL-101-R1",
                    rule_number="1",
                    rule_name="Evidence Components",
                    rule_category="evidence_completeness",
                    description="Test Evidence consists of test scripts, test data and test plan",
                    validation_criteria={
                        "required_components": ["test_scripts", "test_data", "test_plan"],
                        "completeness_threshold": 0.8
                    },
                    severity_level="CRITICAL"
                ),
                ComplianceRuleModel(
                    rule_id="POL-101-R2",
                    rule_number="2", 
                    rule_name="Requirements Traceability",
                    rule_category="traceability",
                    description="Test executed traceable to the functional and non functional requirements",
                    validation_criteria={
                        "traceability_types": ["functional", "non_functional"],
                        "coverage_threshold": 0.8
                    },
                    severity_level="HIGH"
                ),
                # Add more default rules as needed
            ]

        return []

    async def _build_policy_context(self, policy: CompliancePolicyModel) -> Dict[str, Any]:
        """Build comprehensive policy context for validation"""

        return {
            "policy_info": {
                "policy_id": policy.policy_id,
                "policy_name": policy.policy_name,
                "policy_category": policy.policy_category,
                "version": policy.version,
                "description": policy.description
            },
            "validation_scope": {
                "evidence_types": policy.evidence_types,
                "rule_count": len(policy.rules),
                "cross_policy_support": self.config.cross_policy_validation
            },
            "processing_metadata": {
                "auto_detected": policy.policy_id not in getattr(self, '_requested_policies', []),
                "discovery_method": "content_analysis",
                "confidence_level": "high"
            }
        }

    async def _identify_cross_policy_references(self, policies: List[CompliancePolicyModel]) -> List[Dict[str, Any]]:
        """Identify cross-references between multiple policies"""

        cross_references = []

        for i, policy1 in enumerate(policies):
            for policy2 in policies[i+1:]:
                # Check for potential cross-references
                if self._policies_have_overlap(policy1, policy2):
                    cross_references.append({
                        "source_policy": policy1.policy_id,
                        "target_policy": policy2.policy_id,
                        "reference_type": "complementary",
                        "relationship": f"{policy1.policy_category} + {policy2.policy_category}"
                    })

        return cross_references

    def _policies_have_overlap(self, policy1: CompliancePolicyModel, 
                              policy2: CompliancePolicyModel) -> bool:
        """Determine if two policies have overlapping scope"""

        # Simple overlap detection based on categories
        overlapping_categories = [
            ("test_execution", "security_compliance"),
            ("deployment_validation", "security_compliance"),
            ("code_review", "test_execution"),
            ("documentation", "code_review")
        ]

        return (policy1.policy_category, policy2.policy_category) in overlapping_categories or \
               (policy2.policy_category, policy1.policy_category) in overlapping_categories


# Note: This is the first part of the implementation. The complete implementation continues with
# ComplianceRetrievalAgent, GenericEvaluationAgent, and the workflow orchestration.
# Due to length constraints, this will be continued in the next part.

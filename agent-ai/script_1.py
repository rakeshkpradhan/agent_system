# Create core data models
data_models_code = '''"""
Core data models for the Agentic AI Compliance Verification System.

This module defines the primary data structures used throughout the system
including request/response models, evidence documents, and compliance results.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from langchain_core.documents import Document


class ComplianceDecision(Enum):
    """Enumeration of possible compliance decisions."""
    COMPLIANT = "Compliant"
    NON_COMPLIANT = "Non-Compliant"
    INDETERMINATE = "Indeterminate"


class ValidationStatus(Enum):
    """Enumeration of validation statuses for evidence."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLIANT = "Compliant"
    NON_COMPLIANT = "Non-Compliant"
    INDETERMINATE = "Indeterminate"
    ERROR = "error"


@dataclass
class ComplianceRequest:
    """Input data model for compliance verification requests."""
    policy_name: str
    evidence_url: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "policy_name": self.policy_name,
            "evidence_url": self.evidence_url,
            "request_id": self.request_id,
            "timestamp": self.timestamp
        }


@dataclass
class RuleAssessment:
    """Individual policy rule assessment result."""
    rule_id: str
    rule_description: str
    status: ComplianceDecision
    evidence_quote: str
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rule_id": self.rule_id,
            "rule_description": self.rule_description,
            "status": self.status.value,
            "evidence_quote": self.evidence_quote,
            "confidence_score": self.confidence_score
        }


@dataclass
class EvidenceMetadata:
    """Metadata for evidence documents."""
    source_url: str
    section_header: Optional[str] = None
    chunk_id: Optional[str] = None
    extraction_method: str = "unknown"
    content_type: str = "text"
    validation_status: ValidationStatus = ValidationStatus.PENDING
    policy_name: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_url": self.source_url,
            "section_header": self.section_header,
            "chunk_id": self.chunk_id,
            "extraction_method": self.extraction_method,
            "content_type": self.content_type,
            "validation_status": self.validation_status.value,
            "policy_name": self.policy_name,
            "timestamp": self.timestamp
        }


@dataclass
class ProcessedDocument:
    """A processed document with content and metadata."""
    content: str
    metadata: EvidenceMetadata
    embedding: Optional[List[float]] = None
    document_id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_langchain_document(self) -> Document:
        """Convert to LangChain Document format."""
        return Document(
            page_content=self.content,
            metadata=self.metadata.to_dict()
        )


@dataclass
class PolicyRule:
    """Policy rule definition."""
    rule_id: str
    rule_description: str
    rule_type: str = "general"
    severity: str = "medium"
    validation_criteria: str = ""
    policy_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rule_id": self.rule_id,
            "rule_description": self.rule_description,
            "rule_type": self.rule_type,
            "severity": self.severity,
            "validation_criteria": self.validation_criteria,
            "policy_name": self.policy_name
        }


@dataclass
class SimilarEvidenceResult:
    """Result from similar evidence search."""
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    validation_status: ValidationStatus
    rule_assessments: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "similarity_score": self.similarity_score,
            "validation_status": self.validation_status.value,
            "rule_assessments": self.rule_assessments
        }


@dataclass
class ComplianceResult:
    """Final compliance verification result."""
    policy_name: str
    decision: ComplianceDecision
    confidence_score: float
    analysis_summary: str
    rule_assessments: List[RuleAssessment]
    evidence_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    processing_time_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "policy_name": self.policy_name,
            "decision": self.decision.value,
            "confidence_score": self.confidence_score,
            "analysis_summary": self.analysis_summary,
            "rule_assessments": [assessment.to_dict() for assessment in self.rule_assessments],
            "evidence_id": self.evidence_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "processing_time_seconds": self.processing_time_seconds
        }


@dataclass
class WorkflowState:
    """State object for LangGraph workflow."""
    request: ComplianceRequest
    evidence_documents: List[ProcessedDocument] = field(default_factory=list)
    evidence_id: Optional[str] = None
    policy_rules: List[PolicyRule] = field(default_factory=list)
    similar_evidences: List[SimilarEvidenceResult] = field(default_factory=list)
    rag_context: str = ""
    llm_evaluation: Dict[str, Any] = field(default_factory=dict)
    final_result: Optional[ComplianceResult] = None
    messages: List[str] = field(default_factory=list)
    error: Optional[str] = None
    processing_start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    
    def add_message(self, message: str) -> None:
        """Add a message to the workflow state."""
        self.messages.append(f"{datetime.utcnow().isoformat()}: {message}")
    
    def set_error(self, error: str) -> None:
        """Set error state."""
        self.error = error
        self.add_message(f"ERROR: {error}")
    
    def get_processing_time(self) -> float:
        """Get total processing time in seconds."""
        return datetime.utcnow().timestamp() - self.processing_start_time
'''

with open("agentic_compliance_system/models/data_models.py", "w") as f:
    f.write(data_models_code)

print("✅ Created comprehensive data models")
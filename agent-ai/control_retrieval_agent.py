"""
Agent 2: Control Retrieval Agent (Context Building RAG Pipeline)

This agent gathers all necessary context for compliance evaluation by:
1. Retrieving policy rules from SpannerGraph knowledge base
2. Finding similar historical evidence from vector store
3. Assembling comprehensive RAG context document
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..models.data_models import WorkflowState, PolicyRule, SimilarEvidenceResult
from ..services.external_services import SpannerGraphService, SpannerVectorService
from ..core.config import config

logger = logging.getLogger(__name__)


class ControlRetrievalAgent:
    """
    Agent responsible for gathering policy rules and similar evidence context.

    This agent performs three main tasks:
    1. Retrieve Policy Rules: Get validation rules from SpannerGraph knowledge base
    2. Retrieve Similar Evidences: Find historical evidence from vector store  
    3. Assemble RAG Context: Combine rules and evidence into comprehensive context
    """

    def __init__(self):
        """Initialize the Control Retrieval Agent."""
        self.graph_service = SpannerGraphService()
        self.vector_service = SpannerVectorService()

        logger.info("Initialized Control Retrieval Agent")

    async def process(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main processing method for Control Retrieval Agent.

        Args:
            state: Current workflow state

        Returns:
            Dictionary with processing results and updated state
        """
        try:
            request = state.request
            evidence_documents = state.evidence_documents

            logger.info(f"Retrieving context for policy: {request.policy_name}")
            state.add_message(f"Starting context retrieval for {request.policy_name}")

            # Task 1: Retrieve Policy Rules from Knowledge Graph
            policy_rules = self._retrieve_policy_rules(request.policy_name)
            state.add_message(f"Retrieved {len(policy_rules)} policy rules")

            # Task 2: Retrieve Similar Evidences from Vector Store
            similar_evidences = self._retrieve_similar_evidences(evidence_documents)
            state.add_message(f"Found {len(similar_evidences)} similar evidence documents")

            # Task 3: Assemble RAG Context
            rag_context = self._assemble_rag_context(policy_rules, similar_evidences)
            state.add_message(f"Assembled RAG context ({len(rag_context)} characters)")

            return {
                'policy_rules': policy_rules,
                'similar_evidences': similar_evidences,
                'rag_context': rag_context,
                'success': True
            }

        except Exception as e:
            error_msg = f"ControlRetrievalAgent failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            return {
                'error': error_msg,
                'success': False
            }

    def _retrieve_policy_rules(self, policy_name: str) -> List[PolicyRule]:
        """
        Task 1: Retrieve Policy Rules from SpannerGraph Knowledge Base.

        Constructs and executes GQL queries to retrieve validation rules for the
        specified policy, including cross-referenced policies.

        Args:
            policy_name: Name of the policy to retrieve rules for

        Returns:
            List of PolicyRule objects
        """
        try:
            logger.info(f"Retrieving policy rules for: {policy_name}")

            # Use SpannerGraph service to get policy rules
            policy_rules = self.graph_service.get_policy_rules(policy_name)

            # Log rule details for debugging
            if policy_rules:
                logger.info(f"Retrieved {len(policy_rules)} rules:")
                for rule in policy_rules[:5]:  # Log first 5 rules
                    logger.debug(f"  - {rule.rule_id}: {rule.rule_description[:100]}...")
            else:
                logger.warning(f"No rules found for policy: {policy_name}")

            return policy_rules

        except Exception as e:
            logger.error(f"Failed to retrieve policy rules for {policy_name}: {str(e)}")
            # Return empty list for graceful degradation
            return []

    def _retrieve_similar_evidences(self, evidence_documents: List[Any]) -> List[SimilarEvidenceResult]:
        """
        Task 2: Retrieve Similar Evidences from Vector Store.

        Performs vector similarity search on the Spanner vector store to find
        historical evidence documents with their validation outcomes.

        Args:
            evidence_documents: Current evidence documents for similarity search

        Returns:
            List of SimilarEvidenceResult objects
        """
        try:
            logger.info("Retrieving similar historical evidence documents")

            if not evidence_documents:
                logger.warning("No evidence documents provided for similarity search")
                return []

            # Use vector service to perform similarity search
            similar_evidences = self.vector_service.similarity_search(
                evidence_documents,
                k=config.similarity_search_k
            )

            # Log similarity results for debugging
            if similar_evidences:
                logger.info(f"Found {len(similar_evidences)} similar evidence documents:")
                for i, evidence in enumerate(similar_evidences[:3]):  # Log first 3
                    logger.debug(f"  - Similarity {evidence.similarity_score:.3f}: "
                               f"{evidence.validation_status.value} "
                               f"({len(evidence.content)} chars)")
            else:
                logger.warning("No similar evidence documents found")

            return similar_evidences

        except Exception as e:
            logger.error(f"Failed to retrieve similar evidences: {str(e)}")
            # Return empty list for graceful degradation
            return []

    def _assemble_rag_context(self, policy_rules: List[PolicyRule], 
                             similar_evidences: List[SimilarEvidenceResult]) -> str:
        """
        Task 3: Assemble RAG Context Document.

        Combines policy rules and similar evidences into a comprehensive
        context document for LLM evaluation.

        Args:
            policy_rules: List of policy rules
            similar_evidences: List of similar evidence results

        Returns:
            Formatted RAG context string
        """
        try:
            logger.info("Assembling comprehensive RAG context document")

            context_parts = []

            # Section 1: Policy Validation Rules
            context_parts.append(self._format_policy_rules_section(policy_rules))

            # Section 2: Similar Past Evidence Examples
            context_parts.append(self._format_similar_evidences_section(similar_evidences))

            # Section 3: Evaluation Guidelines
            context_parts.append(self._format_evaluation_guidelines())

            # Combine all sections
            rag_context = '\n\n'.join([part for part in context_parts if part])

            logger.info(f"Assembled RAG context with {len(rag_context)} characters")
            return rag_context

        except Exception as e:
            logger.error(f"Failed to assemble RAG context: {str(e)}")
            # Return basic context for graceful degradation
            return self._create_fallback_context(policy_rules)

    def _format_policy_rules_section(self, policy_rules: List[PolicyRule]) -> str:
        """Format policy rules section of RAG context."""
        if not policy_rules:
            return """=== POLICY VALIDATION RULES ===
No specific policy rules found. Use general compliance best practices and industry standards for evaluation."""

        sections = ["=== POLICY VALIDATION RULES ==="]

        # Group rules by policy for better organization
        rules_by_policy = {}
        for rule in policy_rules:
            policy_name = rule.policy_name or "Unknown Policy"
            if policy_name not in rules_by_policy:
                rules_by_policy[policy_name] = []
            rules_by_policy[policy_name].append(rule)

        # Format each policy's rules
        for policy_name, rules in rules_by_policy.items():
            sections.append(f"\n--- {policy_name} ---")

            for rule in rules:
                rule_text = f"""
Rule ID: {rule.rule_id}
Description: {rule.rule_description}
Type: {rule.rule_type}
Severity: {rule.severity}
Validation Criteria: {rule.validation_criteria or 'Not specified'}
"""
                sections.append(rule_text.strip())

        return '\n'.join(sections)

    def _format_similar_evidences_section(self, similar_evidences: List[SimilarEvidenceResult]) -> str:
        """Format similar evidences section of RAG context."""
        if not similar_evidences:
            return """=== SIMILAR PAST EVIDENCE EXAMPLES ===
No similar historical evidence found. Base evaluation solely on policy rules and evidence content."""

        sections = ["=== SIMILAR PAST EVIDENCE EXAMPLES ==="]
        sections.append("The following are examples of past compliance evaluations that may provide context:")

        for i, evidence in enumerate(similar_evidences[:3], 1):  # Limit to top 3
            evidence_text = f"""
Example {i}: (Similarity: {evidence.similarity_score:.3f})
Final Status: {evidence.validation_status.value}
Evidence Content: {evidence.content[:800]}{'...' if len(evidence.content) > 800 else ''}
"""

            # Add rule assessments if available
            if evidence.rule_assessments:
                evidence_text += "\nPast Rule Assessments:"
                for assessment in evidence.rule_assessments[:3]:  # Limit assessments
                    if isinstance(assessment, dict):
                        rule_id = assessment.get('rule_id', 'Unknown')
                        status = assessment.get('status', 'Unknown')
                        evidence_text += f"\n  - {rule_id}: {status}"

            sections.append(evidence_text.strip())

        return '\n'.join(sections)

    def _format_evaluation_guidelines(self) -> str:
        """Format evaluation guidelines section."""
        return """=== EVALUATION GUIDELINES ===

When evaluating compliance:

1. PRIMARY EVIDENCE: Base your assessment primarily on the evidence content provided
2. POLICY ADHERENCE: Each rule must be evaluated against specific evidence quotes
3. HISTORICAL CONTEXT: Use similar past examples as reference, not as strict precedent
4. CONFIDENCE SCORING: Assign confidence based on evidence clarity and completeness
5. DECISION CRITERIA:
   - Compliant: Evidence clearly demonstrates rule satisfaction
   - Non-Compliant: Evidence shows rule violation or insufficient compliance  
   - Indeterminate: Insufficient evidence to make a determination

CRITICAL: Only use information explicitly stated in the evidence. Do not make assumptions."""

    def _create_fallback_context(self, policy_rules: List[PolicyRule]) -> str:
        """Create minimal fallback context when full assembly fails."""
        context = "=== BASIC COMPLIANCE EVALUATION CONTEXT ===\n"

        if policy_rules:
            context += f"\nFound {len(policy_rules)} policy rules to evaluate against.\n"
            context += "Evaluate evidence against each rule for compliance.\n"
        else:
            context += "\nNo specific policy rules found.\n"
            context += "Use general compliance best practices for evaluation.\n"

        context += "\nBase assessment on evidence content and industry standards."

        return context

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for monitoring."""
        return {
            'agent_name': 'ControlRetrievalAgent',
            'graph_service': 'SpannerGraph',
            'vector_service': 'SpannerVectorStore',
            'similarity_search_k': config.similarity_search_k
        }

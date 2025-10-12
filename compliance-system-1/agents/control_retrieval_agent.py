"""
Agent 2: Control Retrieval Agent (Context Building RAG Pipeline) - Updated for ParentDocumentRetriever

This agent gathers all necessary context for compliance evaluation by:
1. Retrieving policy rules from SpannerGraph knowledge base
2. Finding similar historical evidence using ParentDocumentRetriever
3. Assembling comprehensive RAG context document
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..models.data_models import WorkflowState, PolicyRule, SimilarEvidenceResult
from ..services.external_services import SpannerGraphService
from ..services.spanner_vector_service import SpannerVectorService
from ..core.config import config

logger = logging.getLogger(__name__)


class ControlRetrievalAgent:
    """
    Agent responsible for gathering policy rules and similar evidence context.
    
    Enhanced to work with ParentDocumentRetriever for better historical evidence retrieval:
    - Searches on small, focused child chunks for precision
    - Returns full parent documents for complete context
    - Maintains document relationships and metadata
    """
    
    def __init__(self):
        """Initialize the Control Retrieval Agent with enhanced retrieval capabilities."""
        self.graph_service = SpannerGraphService()
        self.vector_service = SpannerVectorService()
        
        logger.info("Initialized Control Retrieval Agent with ParentDocumentRetriever support")
    
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
            
            # Task 2: Retrieve Similar Evidences using ParentDocumentRetriever
            similar_evidences = await self._retrieve_similar_evidences_with_retriever(
                evidence_documents, request.policy_name
            )
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
    
    async def _retrieve_similar_evidences_with_retriever(self, evidence_documents: List[Any], 
                                                        policy_name: str) -> List[SimilarEvidenceResult]:
        """
        Task 2: Retrieve Similar Evidences using ParentDocumentRetriever.
        
        Uses enhanced vector search that:
        1. Searches on smaller child chunks for better semantic matching
        2. Returns full parent documents for complete context
        3. Filters by policy and validation status
        
        Args:
            evidence_documents: Current evidence documents for similarity search query
            policy_name: Policy name for filtering historical evidence
            
        Returns:
            List of SimilarEvidenceResult objects with full context
        """
        try:
            logger.info("Retrieving similar historical evidence using ParentDocumentRetriever")
            
            if not evidence_documents:
                logger.warning("No evidence documents provided for similarity search")
                return []
            
            # Create search query from evidence documents
            query_text = self._create_search_query_from_documents(evidence_documents)
            
            # Use enhanced vector service with ParentDocumentRetriever
            similar_evidences = self.vector_service.similarity_search_with_retriever(
                query_text=query_text,
                policy_name=policy_name,
                k=config.similarity_search_k
            )
            
            # Log similarity results for debugging
            if similar_evidences:
                logger.info(f"Found {len(similar_evidences)} similar evidence documents:")
                for i, evidence in enumerate(similar_evidences[:3]):  # Log first 3
                    logger.debug(f"  - Similarity {evidence.similarity_score:.3f}: "
                               f"{evidence.validation_status.value} "
                               f"({len(evidence.content)} chars)")
                    
                    # Log content preview for very high similarity
                    if evidence.similarity_score > 0.8:
                        content_preview = evidence.content[:200].replace('\n', ' ')
                        logger.debug(f"    Preview: {content_preview}...")
            else:
                logger.warning("No similar evidence documents found")
            
            return similar_evidences
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar evidences: {str(e)}")
            # Return empty list for graceful degradation
            return []
    
    def _create_search_query_from_documents(self, evidence_documents: List[Any]) -> str:
        """
        Create an optimized search query from evidence documents.
        
        Extracts key terms and concepts to improve similarity search results.
        
        Args:
            evidence_documents: Evidence documents to extract query terms from
            
        Returns:
            Optimized search query string
        """
        try:
            # Extract content from documents
            content_parts = []
            
            for doc in evidence_documents[:5]:  # Limit to first 5 documents
                if hasattr(doc, 'page_content'):
                    content = doc.page_content
                elif hasattr(doc, 'content'):
                    content = doc.content
                else:
                    continue
                
                # Extract first 300 characters from each document
                content_parts.append(content[:300])
            
            # Combine and clean content
            combined_content = ' '.join(content_parts)
            
            # Extract key terms using basic text processing
            key_terms = self._extract_key_terms(combined_content)
            
            # Create search query prioritizing key terms
            if key_terms:
                search_query = f"{'  '.join(key_terms[:10])} {combined_content[:500]}"
            else:
                search_query = combined_content[:800]
            
            logger.debug(f"Created search query with {len(key_terms)} key terms, "
                        f"{len(search_query)} total characters")
            
            return search_query
            
        except Exception as e:
            logger.error(f"Failed to create search query: {str(e)}")
            # Fallback to simple content combination
            return ' '.join(str(doc)[:200] for doc in evidence_documents[:3])
    
    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key terms from content for better search queries."""
        import re
        
        # Simple keyword extraction (in production, could use more sophisticated NLP)
        # Remove common words and extract meaningful terms
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w{3,}\b', content.lower())
        
        # Common stop words to filter out
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'shall', 'did', 'does'
        }
        
        # Filter out stop words and short words
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Count word frequency
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top terms
        key_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [term[0] for term in key_terms[:15]]
    
    def _assemble_rag_context(self, policy_rules: List[PolicyRule], 
                             similar_evidences: List[SimilarEvidenceResult]) -> str:
        """
        Task 3: Assemble RAG Context Document.
        
        Combines policy rules and similar evidences into a comprehensive
        context document for LLM evaluation, with enhanced formatting for
        ParentDocumentRetriever results.
        
        Args:
            policy_rules: List of policy rules
            similar_evidences: List of similar evidence results (with full parent context)
            
        Returns:
            Formatted RAG context string
        """
        try:
            logger.info("Assembling comprehensive RAG context document")
            
            context_parts = []
            
            # Section 1: Policy Validation Rules
            context_parts.append(self._format_policy_rules_section(policy_rules))
            
            # Section 2: Similar Past Evidence Examples (Enhanced)
            context_parts.append(self._format_enhanced_similar_evidences_section(similar_evidences))
            
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
    
    def _format_enhanced_similar_evidences_section(self, similar_evidences: List[SimilarEvidenceResult]) -> str:
        """Format enhanced similar evidences section with full parent document context."""
        if not similar_evidences:
            return """=== SIMILAR PAST EVIDENCE EXAMPLES ===
No similar historical evidence found. Base evaluation solely on policy rules and evidence content."""
        
        sections = ["=== SIMILAR PAST EVIDENCE EXAMPLES ==="]
        sections.append("The following are examples of past compliance evaluations with full document context:")
        
        for i, evidence in enumerate(similar_evidences[:3], 1):  # Limit to top 3
            # Enhanced formatting with metadata from parent documents
            metadata = evidence.metadata
            
            evidence_text = f"""
Example {i}: (Similarity: {evidence.similarity_score:.3f})
Final Status: {evidence.validation_status.value}
Document Type: {metadata.get('content_group', 'Unknown')}
Source: {metadata.get('source_url', 'Unknown')[:100]}...
Document Size: {len(evidence.content):,} characters
"""
            
            # Add parent document context (truncated for readability)
            content_preview = evidence.content[:1200] if len(evidence.content) > 1200 else evidence.content
            evidence_text += f"\nFull Evidence Content:\n{content_preview}"
            
            if len(evidence.content) > 1200:
                evidence_text += "\n[Content truncated for brevity...]"
            
            # Add rule assessments if available
            if evidence.rule_assessments:
                evidence_text += "\n\nPast Rule Assessments:"
                for assessment in evidence.rule_assessments[:5]:  # Limit assessments
                    if isinstance(assessment, dict):
                        rule_id = assessment.get('rule_id', 'Unknown')
                        status = assessment.get('status', 'Unknown')
                        confidence = assessment.get('confidence_score', 0)
                        evidence_text += f"\n  - {rule_id}: {status} (confidence: {confidence:.2f})"
            
            sections.append(evidence_text.strip())
        
        return '\n'.join(sections)
    
    def _format_evaluation_guidelines(self) -> str:
        """Format evaluation guidelines section."""
        return """=== EVALUATION GUIDELINES ===

When evaluating compliance using the enhanced evidence context:

1. PRIMARY EVIDENCE: Base your assessment primarily on the current evidence content provided
2. POLICY ADHERENCE: Each rule must be evaluated against specific evidence quotes
3. HISTORICAL CONTEXT: Use similar past examples as reference patterns, not strict precedent
4. PARENT DOCUMENT CONTEXT: Consider the full document context from similar evidence examples
5. PATTERN RECOGNITION: Look for similar compliance patterns in historical evidence
6. CONFIDENCE SCORING: Assign confidence based on:
   - Evidence clarity and completeness
   - Consistency with historical patterns
   - Quality of supporting documentation
7. DECISION CRITERIA:
   - Compliant: Evidence clearly demonstrates rule satisfaction with supporting quotes
   - Non-Compliant: Evidence shows rule violation or clearly insufficient compliance  
   - Indeterminate: Insufficient evidence to make a determination

CRITICAL REQUIREMENTS:
- Only use information explicitly stated in the current evidence
- Reference historical patterns for context but don't substitute them for current evidence
- Provide specific quotes from the current evidence for each assessment
- Consider document structure and context when evaluating compliance"""
    
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
        context += "\nParentDocumentRetriever integration available for enhanced context."
        
        return context
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for monitoring."""
        return {
            'agent_name': 'ControlRetrievalAgent',
            'graph_service': 'SpannerGraph',
            'vector_service': 'SpannerVectorStore with ParentDocumentRetriever',
            'similarity_search_k': config.similarity_search_k,
            'enhanced_features': [
                'parent_document_context',
                'child_chunk_search',
                'document_relationship_preservation',
                'key_term_extraction'
            ]
        }

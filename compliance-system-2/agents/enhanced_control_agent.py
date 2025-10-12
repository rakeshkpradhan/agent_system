"""
Enhanced Control Retrieval Agent with spaCy-powered query building.

This agent uses spaCy for intelligent query construction and enhanced
similarity search with semantic understanding.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..models.data_models import WorkflowState, PolicyRule, SimilarEvidenceResult
from ..services.external_services import SpannerGraphService
from ..services.enhanced_spanner_service import EnhancedSpannerVectorService
from ..utils.spacy_processor import text_processor, ProcessedText
from ..core.config import config

logger = logging.getLogger(__name__)


class EnhancedControlRetrievalAgent:
    """
    Enhanced Control Retrieval Agent with spaCy-powered capabilities.
    
    Features:
    - spaCy-enhanced query building from evidence documents
    - Semantic similarity search with entity-aware matching
    - Intelligent context assembly with compliance-specific insights
    - Advanced text processing for better policy rule matching
    """
    
    def __init__(self):
        """Initialize the Enhanced Control Retrieval Agent."""
        self.graph_service = SpannerGraphService()
        self.vector_service = EnhancedSpannerVectorService()
        
        logger.info("Initialized Enhanced Control Retrieval Agent with spaCy integration")
    
    async def process(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main processing method for Enhanced Control Retrieval Agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary with processing results and updated state
        """
        try:
            request = state.request
            evidence_documents = state.evidence_documents
            
            logger.info(f"Retrieving enhanced context for policy: {request.policy_name}")
            state.add_message(f"Starting enhanced context retrieval for {request.policy_name}")
            
            # Task 1: Retrieve Policy Rules from Knowledge Graph
            policy_rules = self._retrieve_policy_rules(request.policy_name)
            state.add_message(f"Retrieved {len(policy_rules)} policy rules")
            
            # Task 2: Retrieve Similar Evidences using spaCy-enhanced search
            similar_evidences = await self._retrieve_similar_evidences_with_spacy(
                evidence_documents, request.policy_name
            )
            state.add_message(f"Found {len(similar_evidences)} similar evidence documents using spaCy")
            
            # Task 3: Assemble Enhanced RAG Context
            rag_context = self._assemble_enhanced_rag_context(policy_rules, similar_evidences)
            state.add_message(f"Assembled enhanced RAG context ({len(rag_context)} characters)")
            
            return {
                'policy_rules': policy_rules,
                'similar_evidences': similar_evidences,
                'rag_context': rag_context,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"Enhanced ControlRetrievalAgent failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            return {
                'error': error_msg,
                'success': False
            }
    
    def _retrieve_policy_rules(self, policy_name: str) -> List[PolicyRule]:
        """
        Task 1: Retrieve Policy Rules from SpannerGraph Knowledge Base.
        
        Args:
            policy_name: Name of the policy to retrieve rules for
            
        Returns:
            List of PolicyRule objects
        """
        try:
            logger.info(f"Retrieving policy rules for: {policy_name}")
            
            # Use SpannerGraph service to get policy rules
            policy_rules = self.graph_service.get_policy_rules(policy_name)
            
            # Enhance rules with spaCy processing for better matching
            enhanced_rules = self._enhance_policy_rules_with_spacy(policy_rules)
            
            # Log rule details for debugging
            if enhanced_rules:
                logger.info(f"Retrieved and enhanced {len(enhanced_rules)} rules:")
                for rule in enhanced_rules[:5]:  # Log first 5 rules
                    logger.debug(f"  - {rule.rule_id}: {rule.rule_description[:100]}...")
            else:
                logger.warning(f"No rules found for policy: {policy_name}")
            
            return enhanced_rules
            
        except Exception as e:
            logger.error(f"Failed to retrieve policy rules for {policy_name}: {str(e)}")
            # Return empty list for graceful degradation
            return []
    
    def _enhance_policy_rules_with_spacy(self, policy_rules: List[PolicyRule]) -> List[PolicyRule]:
        """Enhance policy rules with spaCy processing for better matching."""
        enhanced_rules = []
        
        for rule in policy_rules:
            try:
                # Process rule description with spaCy
                processed_desc = text_processor.process_text(rule.rule_description)
                
                # Extract compliance keywords from validation criteria
                compliance_keywords = text_processor.extract_compliance_keywords(
                    f"{rule.rule_description} {rule.validation_criteria}"
                )
                
                # Store spaCy enhancements in rule metadata (if rule supports it)
                # For now, keep original rule structure but log enhancements
                logger.debug(f"Enhanced rule {rule.rule_id} with {len(processed_desc.key_terms)} key terms")
                
                enhanced_rules.append(rule)
                
            except Exception as e:
                logger.warning(f"Failed to enhance rule {rule.rule_id} with spaCy: {str(e)}")
                enhanced_rules.append(rule)
        
        return enhanced_rules
    
    async def _retrieve_similar_evidences_with_spacy(self, evidence_documents: List[Any], 
                                                    policy_name: str) -> List[SimilarEvidenceResult]:
        """
        Task 2: Retrieve Similar Evidences using spaCy-enhanced query building.
        
        Uses spaCy for intelligent query construction from evidence documents
        with entity extraction and semantic understanding.
        
        Args:
            evidence_documents: Current evidence documents for similarity search query
            policy_name: Policy name for filtering historical evidence
            
        Returns:
            List of SimilarEvidenceResult objects with enhanced semantic matching
        """
        try:
            logger.info("Retrieving similar evidence using spaCy-enhanced queries")
            
            if not evidence_documents:
                logger.warning("No evidence documents provided for similarity search")
                return []
            
            # Create spaCy-enhanced search query from evidence documents
            enhanced_query = await self._create_spacy_enhanced_query(evidence_documents)
            
            # Use enhanced vector service with spaCy-powered search
            similar_evidences = self.vector_service.similarity_search_with_retriever(
                query_text=enhanced_query,
                policy_name=policy_name,
                k=config.similarity_search_k
            )
            
            # Further enhance results with spaCy analysis
            enhanced_results = await self._enhance_similarity_results_with_spacy(
                similar_evidences, enhanced_query
            )
            
            # Log enhanced similarity results for debugging
            if enhanced_results:
                logger.info(f"Found {len(enhanced_results)} spaCy-enhanced similar evidence documents:")
                for i, evidence in enumerate(enhanced_results[:3]):  # Log first 3
                    spacy_entities = len(evidence.metadata.get('spacy_entities', []))
                    compliance_keywords = len(evidence.metadata.get('compliance_keywords', {}))
                    
                    logger.debug(f"  - Similarity {evidence.similarity_score:.3f}: "
                               f"{evidence.validation_status.value} "
                               f"({len(evidence.content)} chars, {spacy_entities} entities, "
                               f"{compliance_keywords} compliance categories)")
            else:
                logger.warning("No similar evidence documents found with spaCy enhancement")
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar evidences with spaCy: {str(e)}")
            # Return empty list for graceful degradation
            return []
    
    async def _create_spacy_enhanced_query(self, evidence_documents: List[Any]) -> str:
        """
        Create spaCy-enhanced search query from evidence documents.
        
        Uses spaCy for entity extraction, key term identification, and
        compliance-specific keyword extraction for optimal query building.
        
        Args:
            evidence_documents: Evidence documents to extract query terms from
            
        Returns:
            Enhanced search query string optimized for semantic similarity
        """
        try:
            logger.info("Creating spaCy-enhanced search query from evidence documents")
            
            # Process evidence documents with spaCy
            processed_texts = []
            
            for doc in evidence_documents[:5]:  # Limit to first 5 documents
                if hasattr(doc, 'page_content'):
                    content = doc.page_content
                elif hasattr(doc, 'content'):
                    content = doc.content
                else:
                    continue
                
                # Process with spaCy
                processed_text = text_processor.process_text(content)
                processed_texts.append(processed_text)
            
            if not processed_texts:
                logger.warning("No valid content found for spaCy query enhancement")
                return ' '.join(str(doc)[:200] for doc in evidence_documents[:3])
            
            # Build enhanced query using spaCy features
            enhanced_query = text_processor.build_similarity_query(
                processed_texts, max_query_length=800
            )
            
            # Log query enhancement details
            total_entities = sum(len(pt.entities) for pt in processed_texts)
            total_key_terms = sum(len(pt.key_terms) for pt in processed_texts)
            total_compliance_entities = sum(len(pt.compliance_entities) for pt in processed_texts)
            
            logger.info(f"Created enhanced query from {len(processed_texts)} documents:")
            logger.info(f"  - Extracted entities: {total_entities}")
            logger.info(f"  - Key terms: {total_key_terms}")
            logger.info(f"  - Compliance entities: {total_compliance_entities}")
            logger.info(f"  - Query length: {len(enhanced_query)} characters")
            
            return enhanced_query
            
        except Exception as e:
            logger.error(f"Failed to create spaCy-enhanced query: {str(e)}")
            # Fallback to simple content combination
            return ' '.join(str(doc)[:300] for doc in evidence_documents[:3])
    
    async def _enhance_similarity_results_with_spacy(self, 
                                                   similar_evidences: List[SimilarEvidenceResult],
                                                   query: str) -> List[SimilarEvidenceResult]:
        """
        Further enhance similarity results using spaCy semantic analysis.
        
        Args:
            similar_evidences: Initial similarity results
            query: Enhanced query used for search
            
        Returns:
            Further enhanced similarity results with spaCy insights
        """
        try:
            enhanced_results = []
            
            for evidence in similar_evidences:
                try:
                    # Calculate spaCy-based semantic similarity
                    spacy_similarity = text_processor.calculate_text_similarity(
                        query, evidence.content[:1000]  # Limit content for performance
                    )
                    
                    # Combine original similarity with spaCy similarity
                    combined_similarity = (evidence.similarity_score * 0.7) + (spacy_similarity * 0.3)
                    
                    # Update similarity score
                    evidence.similarity_score = min(combined_similarity, 1.0)
                    
                    # Add spaCy analysis to metadata if not already present
                    if 'spacy_similarity' not in evidence.metadata:
                        evidence.metadata['spacy_similarity'] = spacy_similarity
                        evidence.metadata['enhanced_with_spacy'] = True
                    
                    enhanced_results.append(evidence)
                    
                except Exception as e:
                    logger.warning(f"Failed to enhance similarity result with spaCy: {str(e)}")
                    enhanced_results.append(evidence)
            
            # Sort by enhanced similarity scores
            enhanced_results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(f"Enhanced {len(enhanced_results)} similarity results with spaCy analysis")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Failed to enhance similarity results with spaCy: {str(e)}")
            return similar_evidences
    
    def _assemble_enhanced_rag_context(self, policy_rules: List[PolicyRule], 
                                     similar_evidences: List[SimilarEvidenceResult]) -> str:
        """
        Task 3: Assemble Enhanced RAG Context with spaCy insights.
        
        Creates comprehensive context document enhanced with spaCy-extracted
        semantic information and compliance-specific insights.
        
        Args:
            policy_rules: List of policy rules
            similar_evidences: List of spaCy-enhanced similar evidence results
            
        Returns:
            Enhanced RAG context string with semantic insights
        """
        try:
            logger.info("Assembling spaCy-enhanced RAG context document")
            
            context_parts = []
            
            # Section 1: Policy Validation Rules (Enhanced)
            context_parts.append(self._format_enhanced_policy_rules_section(policy_rules))
            
            # Section 2: spaCy-Enhanced Similar Evidence Examples
            context_parts.append(self._format_spacy_enhanced_evidences_section(similar_evidences))
            
            # Section 3: Enhanced Evaluation Guidelines with spaCy insights
            context_parts.append(self._format_spacy_evaluation_guidelines())
            
            # Combine all sections
            rag_context = '\n\n'.join([part for part in context_parts if part])
            
            logger.info(f"Assembled spaCy-enhanced RAG context with {len(rag_context)} characters")
            return rag_context
            
        except Exception as e:
            logger.error(f"Failed to assemble enhanced RAG context: {str(e)}")
            # Return basic context for graceful degradation
            return self._create_fallback_context(policy_rules)
    
    def _format_enhanced_policy_rules_section(self, policy_rules: List[PolicyRule]) -> str:
        """Format policy rules section with spaCy enhancements."""
        if not policy_rules:
            return """=== ENHANCED POLICY VALIDATION RULES ===
No specific policy rules found. Use general compliance best practices and industry standards for evaluation.
Consider semantic similarity and entity matching when evaluating evidence."""
        
        sections = ["=== ENHANCED POLICY VALIDATION RULES ==="]
        sections.append("Rules enhanced with semantic analysis and entity extraction:")
        
        # Group rules by policy for better organization
        rules_by_policy = {}
        for rule in policy_rules:
            policy_name = rule.policy_name or "Unknown Policy"
            if policy_name not in rules_by_policy:
                rules_by_policy[policy_name] = []
            rules_by_policy[policy_name].append(rule)
        
        # Format each policy's rules with spaCy enhancements
        for policy_name, rules in rules_by_policy.items():
            sections.append(f"\n--- {policy_name} ---")
            
            for rule in rules:
                # Extract key entities and terms from rule description
                try:
                    processed_rule = text_processor.process_text(rule.rule_description)
                    key_entities = [e['text'] for e in processed_rule.entities[:3]]
                    key_terms = processed_rule.key_terms[:5]
                    
                    rule_text = f"""
Rule ID: {rule.rule_id}
Description: {rule.rule_description}
Type: {rule.rule_type}
Severity: {rule.severity}
Validation Criteria: {rule.validation_criteria or 'Not specified'}
Key Entities: {', '.join(key_entities) if key_entities else 'None identified'}
Key Terms: {', '.join(key_terms) if key_terms else 'None identified'}
"""
                except Exception as e:
                    logger.debug(f"Failed to enhance rule {rule.rule_id}: {str(e)}")
                    rule_text = f"""
Rule ID: {rule.rule_id}
Description: {rule.rule_description}
Type: {rule.rule_type}
Severity: {rule.severity}
Validation Criteria: {rule.validation_criteria or 'Not specified'}
"""
                
                sections.append(rule_text.strip())
        
        return '\n'.join(sections)
    
    def _format_spacy_enhanced_evidences_section(self, similar_evidences: List[SimilarEvidenceResult]) -> str:
        """Format similar evidences section with spaCy enhancements."""
        if not similar_evidences:
            return """=== SPACY-ENHANCED SIMILAR EVIDENCE EXAMPLES ===
No similar historical evidence found. Base evaluation solely on policy rules and evidence content.
Use semantic similarity and entity matching for comprehensive analysis."""
        
        sections = ["=== SPACY-ENHANCED SIMILAR EVIDENCE EXAMPLES ==="]
        sections.append("Similar evidence examples enhanced with semantic analysis and entity extraction:")
        
        for i, evidence in enumerate(similar_evidences[:3], 1):  # Limit to top 3
            # Enhanced formatting with spaCy metadata
            metadata = evidence.metadata
            
            evidence_text = f"""
Example {i}: (Semantic Similarity: {evidence.similarity_score:.3f})
Final Status: {evidence.validation_status.value}
Document Type: {metadata.get('content_group', 'Unknown')}
Source: {metadata.get('source_url', 'Unknown')[:100]}...
Document Size: {len(evidence.content):,} characters
"""
            
            # Add spaCy enhancements if available
            if 'spacy_entities' in metadata:
                try:
                    entities = metadata.get('spacy_entities', [])
                    if isinstance(entities, str):
                        import json
                        entities = json.loads(entities)
                    
                    entity_texts = [e.get('text', str(e)) if isinstance(e, dict) else str(e) 
                                   for e in entities[:5]]
                    evidence_text += f"\nKey Entities: {', '.join(entity_texts)}"
                except Exception as e:
                    logger.debug(f"Failed to parse spaCy entities: {str(e)}")
            
            if 'compliance_keywords' in metadata:
                try:
                    keywords = metadata.get('compliance_keywords', {})
                    if isinstance(keywords, str):
                        import json
                        keywords = json.loads(keywords)
                    
                    if isinstance(keywords, dict):
                        key_terms = keywords.get('key_terms', [])[:5]
                        if key_terms:
                            evidence_text += f"\nCompliance Keywords: {', '.join(str(k) for k in key_terms)}"
                except Exception as e:
                    logger.debug(f"Failed to parse compliance keywords: {str(e)}")
            
            # Add spaCy similarity score if available
            if 'spacy_similarity' in metadata:
                spacy_sim = metadata.get('spacy_similarity', 0.0)
                evidence_text += f"\nspaCy Semantic Score: {spacy_sim:.3f}"
            
            # Add content preview
            content_preview = evidence.content[:1000] if len(evidence.content) > 1000 else evidence.content
            evidence_text += f"\n\nEvidence Content:\n{content_preview}"
            
            if len(evidence.content) > 1000:
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
    
    def _format_spacy_evaluation_guidelines(self) -> str:
        """Format evaluation guidelines enhanced with spaCy capabilities."""
        return """=== SPACY-ENHANCED EVALUATION GUIDELINES ===

When evaluating compliance using spaCy-enhanced evidence context:

1. PRIMARY EVIDENCE: Base assessment on current evidence content with semantic understanding
2. ENTITY MATCHING: Consider named entities and their relationships across evidence and rules
3. SEMANTIC SIMILARITY: Use spaCy-calculated similarity scores for context understanding
4. COMPLIANCE KEYWORDS: Pay attention to compliance-specific terms and entities extracted
5. HISTORICAL PATTERNS: Reference similar evidence patterns with entity and semantic analysis
6. PARENT DOCUMENT CONTEXT: Consider full document context from parent-child relationships

SPACY-ENHANCED ANALYSIS PROCESS:
- Extract and match key entities between evidence and policy rules
- Use semantic similarity for evidence relevance assessment
- Consider compliance-specific keyword patterns
- Analyze sentence structure and linguistic patterns
- Evaluate entity relationships and co-occurrences

CONFIDENCE SCORING WITH SPACY:
- High confidence: Clear entity matches + high semantic similarity + explicit evidence
- Medium confidence: Partial entity matches + moderate similarity + inferential evidence  
- Low confidence: Few entity matches + low similarity + ambiguous evidence

DECISION CRITERIA (Enhanced):
- Compliant: Evidence demonstrates rule satisfaction with supporting entity matches
- Non-Compliant: Evidence shows rule violation with conflicting entity patterns
- Indeterminate: Insufficient entity matches or semantic clarity for determination

CRITICAL REQUIREMENTS:
- Combine rule-based matching with semantic similarity analysis
- Use entity extraction to identify key compliance concepts
- Consider linguistic patterns and sentence structure in evaluation
- Leverage spaCy's semantic understanding for nuanced analysis"""
    
    def _create_fallback_context(self, policy_rules: List[PolicyRule]) -> str:
        """Create enhanced fallback context when full assembly fails."""
        context = "=== ENHANCED COMPLIANCE EVALUATION CONTEXT (FALLBACK) ===\n"
        
        if policy_rules:
            context += f"\nFound {len(policy_rules)} policy rules to evaluate against.\n"
            context += "Evaluate evidence against each rule using semantic similarity and entity matching.\n"
        else:
            context += "\nNo specific policy rules found.\n"
            context += "Use general compliance best practices with spaCy semantic analysis.\n"
        
        context += "\nspaCy enhancements available:"
        context += "\n- Named Entity Recognition for compliance terms"
        context += "\n- Semantic similarity calculation"
        context += "\n- Key term and entity extraction"
        context += "\n- Compliance-specific pattern matching"
        context += "\nBase assessment on evidence content enhanced with semantic understanding."
        
        return context
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get enhanced processing statistics for monitoring."""
        spacy_stats = text_processor.get_processing_stats()
        
        return {
            'agent_name': 'Enhanced ControlRetrievalAgent',
            'graph_service': 'SpannerGraph',
            'vector_service': 'Enhanced SpannerVectorStore with GCS + spaCy',
            'text_processor': spacy_stats,
            'similarity_search_k': config.similarity_search_k,
            'enhancement_features': [
                'spacy_entity_extraction',
                'semantic_query_building', 
                'compliance_keyword_identification',
                'enhanced_similarity_scoring',
                'intelligent_context_assembly'
            ],
            'spacy_integration': {
                'query_enhancement': True,
                'entity_matching': True,
                'semantic_similarity': config.enable_spacy_similarity,
                'compliance_patterns': True
            }
        }

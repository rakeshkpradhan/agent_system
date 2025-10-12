"""
Enhanced Evidence Summarizer Agent with GCS and spaCy integration.

This agent uses GCS-based ParentDocumentRetriever and spaCy-enhanced text processing
for optimal handling of large evidence documents from Confluence.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.retrievers import ParentDocumentRetriever
from langchain_core.documents import Document

from ..models.data_models import WorkflowState, ProcessedDocument, ValidationStatus
from ..services.external_services import ConfluenceService
from ..services.enhanced_spanner_service import EnhancedSpannerVectorService
from ..utils.content_parser import ContentParser, create_parsing_strategies
from ..utils.spacy_processor import text_processor, ProcessedText
from ..core.config import config

logger = logging.getLogger(__name__)


class EnhancedEvidenceSummarizerAgent:
    """
    Enhanced Evidence Summarizer Agent with GCS and spaCy integration.
    
    Features:
    - GCS-based document storage for production persistence
    - spaCy-enhanced text processing and entity extraction
    - Intelligent document grouping with semantic understanding
    - Advanced chunking strategies respecting sentence boundaries
    """
    
    def __init__(self):
        """Initialize the Enhanced Evidence Summarizer Agent."""
        self.confluence_service = ConfluenceService()
        self.vector_service = EnhancedSpannerVectorService()
        
        # Initialize content parser with Confluence-optimized strategy
        strategies = create_parsing_strategies()
        self.content_parser = ContentParser(strategies['confluence_optimized'])
        
        # ParentDocumentRetriever will be initialized per request
        self.parent_retriever = None
        
        logger.info("Initialized Enhanced Evidence Summarizer Agent with GCS and spaCy")
    
    async def process(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main processing method for Enhanced Evidence Summarizer Agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary with processing results and updated state
        """
        try:
            request = state.request
            logger.info(f"Processing evidence from URL: {request.evidence_url}")
            state.add_message(f"Starting enhanced evidence processing for {request.policy_name}")
            
            # Get enhanced ParentDocumentRetriever for this request
            self.parent_retriever = self.vector_service.get_parent_document_retriever(
                request.policy_name, use_spacy_chunking=True
            )
            
            # Task 1: Fetch Content
            html_content = self._fetch_content(request.evidence_url)
            state.add_message(f"Successfully fetched content ({len(html_content)} characters)")
            
            # Task 2: Parse and Structure Content  
            raw_documents = self._parse_and_structure_content(html_content, request.evidence_url)
            state.add_message(f"Parsed content into {len(raw_documents)} raw document segments")
            
            # Task 3: Create Parent Documents with spaCy Enhancement
            parent_documents = await self._create_enhanced_parent_documents(raw_documents, request.policy_name)
            state.add_message(f"Created {len(parent_documents)} spaCy-enhanced parent documents")
            
            # Task 4: Embed and Store using Enhanced ParentDocumentRetriever
            evidence_id = await self._embed_and_store_with_enhanced_retriever(parent_documents, request.policy_name)
            state.add_message(f"Stored documents with evidence ID: {evidence_id}")
            
            return {
                'evidence_documents': parent_documents,
                'evidence_id': evidence_id,
                'parent_retriever': self.parent_retriever,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"Enhanced EvidenceSummarizerAgent failed: {str(e)}"
            logger.error(error_msg)
            state.set_error(error_msg)
            return {
                'error': error_msg,
                'success': False
            }
    
    def _fetch_content(self, evidence_url: str) -> str:
        """
        Task 1: Fetch Content from Confluence with proper authentication.
        
        Args:
            evidence_url: URL of the Confluence page
            
        Returns:
            Raw HTML content of the page
        """
        try:
            logger.info(f"Fetching content from Confluence URL: {evidence_url}")
            
            # Use Confluence service to fetch content
            html_content = self.confluence_service.fetch_page_content(evidence_url)
            
            logger.info(f"Successfully fetched {len(html_content)} characters of content")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to fetch content from {evidence_url}: {str(e)}")
            raise
    
    def _parse_and_structure_content(self, html_content: str, source_url: str) -> List[ProcessedDocument]:
        """
        Task 2: Parse and Structure Content using multiple parsing strategies.
        
        Args:
            html_content: Raw HTML content to parse
            source_url: Source URL for metadata
            
        Returns:
            List of ProcessedDocument objects (raw, before spaCy enhancement)
        """
        try:
            logger.info("Parsing and structuring HTML content")
            
            # Use content parser with multiple strategies
            documents = self.content_parser.parse_html_content(html_content, source_url)
            
            # Additional processing for Confluence-specific elements
            documents = self._post_process_confluence_content(documents)
            
            logger.info(f"Successfully parsed content into {len(documents)} raw document segments")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to parse HTML content: {str(e)}")
            raise
    
    async def _create_enhanced_parent_documents(self, raw_documents: List[ProcessedDocument], 
                                              policy_name: str) -> List[Document]:
        """
        Task 3: Create Parent Documents with spaCy-enhanced intelligent grouping.
        
        Uses spaCy for semantic analysis, entity extraction, and intelligent document grouping.
        
        Args:
            raw_documents: Raw parsed documents
            policy_name: Policy name for metadata
            
        Returns:
            List of enhanced parent Document objects
        """
        try:
            logger.info("Creating spaCy-enhanced parent documents")
            
            # Process documents with spaCy for semantic understanding
            spacy_processed_docs = await self._process_documents_with_spacy(raw_documents)
            
            # Group documents using spaCy semantic analysis
            semantic_groups = self._group_documents_with_spacy_semantics(spacy_processed_docs)
            
            parent_documents = []
            
            for group_key, doc_group in semantic_groups.items():
                # Combine related documents with spaCy-guided structure
                combined_content, combined_metadata = self._combine_document_group_with_spacy(doc_group)
                
                if len(combined_content.strip()) < 100:  # Skip very small groups
                    continue
                
                # Create enhanced parent document with spaCy metadata
                parent_doc = Document(
                    page_content=combined_content,
                    metadata={
                        'source_url': doc_group[0]['raw_doc'].metadata.source_url,
                        'policy_name': policy_name,
                        'content_group': group_key,
                        'document_count': len(doc_group),
                        'parent_id': str(uuid.uuid4()),
                        'timestamp': datetime.utcnow().isoformat(),
                        'validation_status': ValidationStatus.PENDING.value,
                        'total_length': len(combined_content),
                        'is_parent_document': True,
                        **combined_metadata  # Add spaCy-extracted metadata
                    }
                )
                
                parent_documents.append(parent_doc)
            
            logger.info(f"Created {len(parent_documents)} spaCy-enhanced parent documents "
                       f"from {len(raw_documents)} raw documents")
            return parent_documents
            
        except Exception as e:
            logger.error(f"Failed to create enhanced parent documents: {str(e)}")
            raise
    
    async def _process_documents_with_spacy(self, raw_documents: List[ProcessedDocument]) -> List[Dict[str, Any]]:
        """Process raw documents with spaCy for semantic analysis."""
        spacy_processed = []
        
        for doc in raw_documents:
            try:
                # Process text with spaCy
                processed_text = text_processor.process_text(doc.content)
                
                # Extract compliance-specific keywords
                compliance_keywords = text_processor.extract_compliance_keywords(doc.content)
                
                spacy_processed.append({
                    'raw_doc': doc,
                    'processed_text': processed_text,
                    'compliance_keywords': compliance_keywords,
                    'semantic_similarity_ready': True
                })
                
            except Exception as e:
                logger.warning(f"Failed to process document with spaCy: {str(e)}")
                # Add document without spaCy processing
                spacy_processed.append({
                    'raw_doc': doc,
                    'processed_text': None,
                    'compliance_keywords': {},
                    'semantic_similarity_ready': False
                })
        
        return spacy_processed
    
    def _group_documents_with_spacy_semantics(self, spacy_processed_docs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group documents using spaCy semantic analysis."""
        groups = {}
        
        for doc_data in spacy_processed_docs:
            raw_doc = doc_data['raw_doc']
            processed_text = doc_data['processed_text']
            
            # Create base grouping key
            section = raw_doc.metadata.section_header or "general"
            content_type = raw_doc.metadata.content_type or "text"
            
            # Enhance grouping with spaCy semantic information
            if processed_text and doc_data['semantic_similarity_ready']:
                # Use key entities and compliance keywords for grouping
                key_entities = [e['text'].lower() for e in processed_text.entities[:3]]
                compliance_terms = doc_data['compliance_keywords'].get('key_terms', [])[:3]
                
                # Create semantic signature
                semantic_signature = '_'.join(sorted(key_entities + compliance_terms))[:50]
                
                if semantic_signature:
                    group_key = f"{content_type}_{section}_{semantic_signature}"
                else:
                    group_key = f"{content_type}_{section}"
            else:
                # Fallback to basic grouping
                group_key = f"{content_type}_{section}"
            
            # Clean group key
            group_key = group_key.replace(" ", "_").lower()[:100]
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(doc_data)
        
        # Merge small semantic groups
        groups = self._merge_small_semantic_groups(groups)
        
        logger.info(f"Grouped {len(spacy_processed_docs)} documents into {len(groups)} semantic groups")
        return groups
    
    def _merge_small_semantic_groups(self, groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Merge small semantic groups using spaCy similarity."""
        min_group_size = 2
        merged_groups = {}
        small_groups = []
        
        # Separate large and small groups
        for key, docs in groups.items():
            if len(docs) >= min_group_size:
                merged_groups[key] = docs
            else:
                small_groups.extend(docs)
        
        # Group small documents by semantic similarity
        if small_groups:
            similarity_clusters = self._cluster_by_semantic_similarity(small_groups)
            
            for i, cluster in enumerate(similarity_clusters):
                if len(cluster) >= min_group_size:
                    merged_key = f"semantic_cluster_{i}"
                    merged_groups[merged_key] = cluster
                else:
                    # Add to a general miscellaneous group
                    if 'miscellaneous' not in merged_groups:
                        merged_groups['miscellaneous'] = []
                    merged_groups['miscellaneous'].extend(cluster)
        
        return merged_groups
    
    def _cluster_by_semantic_similarity(self, docs: List[Dict[str, Any]], threshold: float = 0.7) -> List[List[Dict[str, Any]]]:
        """Cluster documents by semantic similarity using spaCy."""
        clusters = []
        unclustered = docs.copy()
        
        while unclustered:
            # Start new cluster with first unclustered document
            seed_doc = unclustered.pop(0)
            current_cluster = [seed_doc]
            
            # Find similar documents
            if seed_doc['semantic_similarity_ready']:
                seed_text = seed_doc['raw_doc'].content
                
                similar_docs = []
                remaining_docs = []
                
                for doc in unclustered:
                    if doc['semantic_similarity_ready']:
                        similarity = text_processor.calculate_text_similarity(
                            seed_text, doc['raw_doc'].content
                        )
                        
                        if similarity >= threshold:
                            similar_docs.append(doc)
                        else:
                            remaining_docs.append(doc)
                    else:
                        remaining_docs.append(doc)
                
                current_cluster.extend(similar_docs)
                unclustered = remaining_docs
            
            clusters.append(current_cluster)
            
            # Limit cluster count to prevent over-fragmentation
            if len(clusters) >= 10:
                # Add remaining documents to largest cluster
                if unclustered and clusters:
                    largest_cluster = max(clusters, key=len)
                    largest_cluster.extend(unclustered)
                break
        
        return clusters
    
    def _combine_document_group_with_spacy(self, doc_group: List[Dict[str, Any]]) -> tuple[str, Dict[str, Any]]:
        """Combine document group with spaCy-guided structuring."""
        sections = []
        combined_entities = []
        combined_key_terms = []
        combined_compliance_keywords = {}
        
        # Sort documents by semantic importance
        sorted_docs = self._sort_docs_by_semantic_importance(doc_group)
        
        current_section = None
        section_content = []
        
        for doc_data in sorted_docs:
            raw_doc = doc_data['raw_doc']
            processed_text = doc_data['processed_text']
            
            section_header = raw_doc.metadata.section_header
            
            # Start new section if header changed
            if section_header != current_section and section_header:
                if section_content:
                    sections.append("\n".join(section_content))
                    section_content = []
                
                current_section = section_header
                section_content.append(f"## {section_header}")
            
            # Add document content
            section_content.append(raw_doc.content)
            
            # Collect spaCy metadata
            if processed_text:
                combined_entities.extend([e['text'] for e in processed_text.entities[:5]])
                combined_key_terms.extend(processed_text.key_terms[:10])
            
            # Collect compliance keywords
            compliance_kw = doc_data['compliance_keywords']
            for category, terms in compliance_kw.items():
                if category not in combined_compliance_keywords:
                    combined_compliance_keywords[category] = []
                combined_compliance_keywords[category].extend(terms[:5])
        
        # Add final section
        if section_content:
            sections.append("\n".join(section_content))
        
        # Create combined metadata
        combined_metadata = {
            'spacy_entities': list(set(combined_entities))[:15],
            'spacy_key_terms': list(set(combined_key_terms))[:20],
            'compliance_keywords': {k: list(set(v))[:10] for k, v in combined_compliance_keywords.items()},
            'extraction_methods': list(set(doc_data['raw_doc'].metadata.extraction_method for doc_data in doc_group)),
            'content_types': list(set(doc_data['raw_doc'].metadata.content_type for doc_data in doc_group))
        }
        
        combined_content = "\n\n".join(sections)
        return combined_content, combined_metadata
    
    def _sort_docs_by_semantic_importance(self, doc_group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort documents by semantic importance using spaCy features."""
        def importance_score(doc_data):
            score = 0
            processed_text = doc_data['processed_text']
            
            if processed_text:
                # Score based on entities
                score += len(processed_text.entities) * 0.5
                
                # Score based on key terms
                score += len(processed_text.key_terms) * 0.3
                
                # Score based on compliance entities
                score += len(processed_text.compliance_entities) * 1.0
            
            # Score based on content length (moderate preference for longer content)
            content_length = len(doc_data['raw_doc'].content)
            score += min(content_length / 1000, 2.0)  # Cap at 2.0 points
            
            return score
        
        return sorted(doc_group, key=importance_score, reverse=True)
    
    async def _embed_and_store_with_enhanced_retriever(self, parent_documents: List[Document], 
                                                     policy_name: str) -> str:
        """
        Task 4: Generate embeddings using text-embedding-005 and store with enhanced retriever.
        
        Args:
            parent_documents: List of enhanced parent Document objects
            policy_name: Policy name for evidence type classification
            
        Returns:
            Primary evidence ID for the stored documents
        """
        try:
            logger.info(f"Storing {len(parent_documents)} enhanced parent documents")
            
            # Use enhanced vector service for storage
            evidence_id = self.vector_service.store_documents_with_retriever(parent_documents, policy_name)
            
            # Log enhanced storage statistics
            total_chars = sum(len(doc.page_content) for doc in parent_documents)
            avg_doc_size = total_chars / len(parent_documents) if parent_documents else 0
            
            # Count spaCy enhancements
            docs_with_entities = sum(1 for doc in parent_documents if doc.metadata.get('spacy_entities'))
            docs_with_keywords = sum(1 for doc in parent_documents if doc.metadata.get('compliance_keywords'))
            
            logger.info(f"Successfully stored enhanced documents:")
            logger.info(f"  - Parent documents: {len(parent_documents)}")
            logger.info(f"  - Total characters: {total_chars:,}")
            logger.info(f"  - Average document size: {avg_doc_size:.0f} chars")
            logger.info(f"  - Documents with spaCy entities: {docs_with_entities}")
            logger.info(f"  - Documents with compliance keywords: {docs_with_keywords}")
            logger.info(f"  - Primary evidence ID: {evidence_id}")
            logger.info(f"  - Storage: GCS + Spanner vector store")
            
            return evidence_id
            
        except Exception as e:
            logger.error(f"Failed to store documents with enhanced retriever: {str(e)}")
            raise
    
    def _post_process_confluence_content(self, documents: List[ProcessedDocument]) -> List[ProcessedDocument]:
        """Post-process documents for Confluence-specific optimizations."""
        processed_docs = []
        
        for doc in documents:
            # Clean up Confluence-specific markup artifacts
            cleaned_content = self._clean_confluence_artifacts(doc.content)
            
            # Skip if content becomes too short after cleaning
            if len(cleaned_content.strip()) < 50:
                continue
            
            # Update content
            doc.content = cleaned_content
            processed_docs.append(doc)
        
        return processed_docs
    
    def _clean_confluence_artifacts(self, content: str) -> str:
        """Clean Confluence-specific artifacts from content."""
        import re
        
        # Remove CDATA blocks
        content = re.sub(r'<!\[CDATA\[.*?\]\]>', '', content, flags=re.DOTALL)
        
        # Remove macro references that weren't properly parsed
        content = re.sub(r'</?ac:.*?>', '', content)
        
        # Clean up excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    def get_retriever(self) -> Optional[ParentDocumentRetriever]:
        """Get the enhanced ParentDocumentRetriever instance."""
        return self.parent_retriever
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get enhanced processing statistics for monitoring."""
        spacy_stats = text_processor.get_processing_stats()
        
        return {
            'agent_name': 'Enhanced EvidenceSummarizerAgent',
            'retriever_type': 'ParentDocumentRetriever with GCS + spaCy',
            'document_store': 'GCS',
            'text_processor': spacy_stats,
            'parsing_strategies': ['trafilatura', 'beautifulsoup', 'confluence_specific'],
            'text_splitters': {
                'primary_chunk_size': config.max_chunk_size,
                'child_chunk_size': config.child_chunk_size,
                'chunk_overlap': config.chunk_overlap,
                'spacy_enhanced': True
            },
            'embedding_model': config.embedding_model_name,
            'enhancement_features': [
                'semantic_document_grouping',
                'entity_extraction',
                'compliance_keyword_identification',
                'intelligent_chunking',
                'similarity_clustering'
            ]
        }

"""
Enhanced SpannerVectorService with GCS document store and spaCy integration.

This service provides optimized vector storage for large documents using
GCS-based ParentDocumentRetriever and spaCy-enhanced text processing.
"""

import logging
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

import google.generativeai as genai
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from google.auth import default
from langchain_core.documents import Document
from langchain_google_spanner import SpannerVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain.retrievers import ParentDocumentRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter

from ..models.data_models import (
    ProcessedDocument, SimilarEvidenceResult, 
    ValidationStatus, ComplianceRequest
)
from ..services.gcs_docstore import GCSDocumentStore
from ..utils.spacy_processor import text_processor
from ..core.config import config

logger = logging.getLogger(__name__)


class EnhancedSpannerVectorService:
    """
    Enhanced service for GCP Spanner vector store with GCS and spaCy integration.
    
    Features:
    - GCS-based document store for production-ready persistence
    - spaCy-enhanced text processing and query building
    - Optimized ParentDocumentRetriever with intelligent chunking
    - Advanced similarity search with semantic understanding
    """
    
    def __init__(self):
        """Initialize enhanced Spanner vector service."""
        self.project_id = config.vertex_ai_project
        self.instance_id = config.spanner_instance_id
        self.database_id = config.spanner_database_id
        self.table_name = config.spanner_vector_table_name
        
        # Initialize embedding model
        self.embedding_model = VertexAIEmbeddings(
            model_name=config.embedding_model_name,
            project=self.project_id,
            location=config.vertex_ai_location
        )
        
        # Initialize enhanced vector store with metadata columns
        self.vector_store = SpannerVectorStore(
            instance_id=self.instance_id,
            database_id=self.database_id,
            table_name=self.table_name,
            embedding_service=self.embedding_model,
            metadata_columns=[
                'source_url', 'section_header', 'chunk_id', 'extraction_method',
                'content_type', 'validation_status', 'policy_name', 'timestamp',
                'rule_assessments', 'analysis_summary', 'confidence_score',
                'parent_id', 'document_count', 'content_group', 'total_length',
                'extraction_methods', 'content_types', 'is_parent_document',
                'spacy_entities', 'spacy_key_terms', 'compliance_keywords',
                'similarity_features', 'processed_at'
            ]
        )
        
        # Initialize GCS document store
        self.docstore = GCSDocumentStore(
            bucket_name=config.gcs_bucket_name,
            prefix=config.gcs_document_prefix
        )
        
        # Cache for ParentDocumentRetriever instances
        self._retriever_cache = {}
        
        logger.info(f"Initialized enhanced Spanner vector service with GCS and spaCy")
    
    def get_vector_store(self) -> SpannerVectorStore:
        """Get the underlying vector store instance."""
        return self.vector_store
    
    def get_parent_document_retriever(self, policy_name: str, use_spacy_chunking: bool = True) -> ParentDocumentRetriever:
        """
        Get or create a ParentDocumentRetriever with spaCy-enhanced chunking.
        
        Args:
            policy_name: Policy name for filtering and retrieval
            use_spacy_chunking: Whether to use spaCy-enhanced text splitting
            
        Returns:
            Configured ParentDocumentRetriever instance with GCS storage
        """
        try:
            # Check cache first
            cache_key = f"{policy_name}_{use_spacy_chunking}"
            if cache_key in self._retriever_cache:
                return self._retriever_cache[cache_key]
            
            # Create text splitters with spaCy enhancement
            if use_spacy_chunking:
                parent_splitter, child_splitter = self._create_spacy_enhanced_splitters()
            else:
                parent_splitter, child_splitter = self._create_standard_splitters()
            
            # Create ParentDocumentRetriever with GCS document store
            retriever = ParentDocumentRetriever(
                vectorstore=self.vector_store,
                docstore=self.docstore,
                child_splitter=child_splitter,
                parent_splitter=parent_splitter,
                search_type="similarity",
                search_kwargs={
                    "k": config.similarity_search_k,
                    "filter": {"policy_name": policy_name}
                }
            )
            
            # Cache for reuse
            self._retriever_cache[cache_key] = retriever
            
            logger.info(f"Created enhanced ParentDocumentRetriever for policy: {policy_name} "
                       f"(spaCy chunking: {use_spacy_chunking})")
            return retriever
            
        except Exception as e:
            logger.error(f"Failed to create ParentDocumentRetriever: {str(e)}")
            raise
    
    def _create_spacy_enhanced_splitters(self) -> Tuple[RecursiveCharacterTextSplitter, RecursiveCharacterTextSplitter]:
        """Create text splitters enhanced with spaCy sentence boundaries."""
        
        class SpacyEnhancedSplitter(RecursiveCharacterTextSplitter):
            """Text splitter that respects spaCy sentence boundaries."""
            
            def split_text(self, text: str) -> List[str]:
                # Process text with spaCy to get sentence boundaries
                try:
                    doc = text_processor.nlp(text[:config.spacy_max_length])
                    sentences = [sent.text.strip() for sent in doc.sents]
                    
                    # Group sentences into chunks of appropriate size
                    chunks = []
                    current_chunk = ""
                    
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) <= self._chunk_size:
                            current_chunk += sentence + " "
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence + " "
                    
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    return chunks
                    
                except Exception as e:
                    logger.warning(f"spaCy splitting failed, using standard splitter: {str(e)}")
                    return super().split_text(text)
        
        # Parent splitter for larger context documents
        parent_splitter = SpacyEnhancedSplitter(
            chunk_size=config.max_chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        # Child splitter for smaller, focused search chunks
        child_splitter = SpacyEnhancedSplitter(
            chunk_size=config.child_chunk_size,
            chunk_overlap=config.child_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        return parent_splitter, child_splitter
    
    def _create_standard_splitters(self) -> Tuple[RecursiveCharacterTextSplitter, RecursiveCharacterTextSplitter]:
        """Create standard text splitters without spaCy enhancement."""
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.max_chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.child_chunk_size,
            chunk_overlap=config.child_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        return parent_splitter, child_splitter
    
    def store_documents_with_retriever(self, documents: List[Document], policy_name: str) -> str:
        """
        Store documents using ParentDocumentRetriever with spaCy enhancement.
        
        Args:
            documents: List of parent documents to store
            policy_name: Policy name for evidence type classification
            
        Returns:
            Primary evidence ID for the stored documents
        """
        try:
            # Enhance documents with spaCy processing
            enhanced_documents = self._enhance_documents_with_spacy(documents, policy_name)
            
            # Get ParentDocumentRetriever for this policy
            retriever = self.get_parent_document_retriever(policy_name, use_spacy_chunking=True)
            
            # Generate document IDs
            doc_ids = [doc.metadata.get('parent_id', str(uuid.uuid4())) for doc in enhanced_documents]
            
            # Add documents to retriever (handles parent-child splitting and storage)
            retriever.add_documents(documents=enhanced_documents, ids=doc_ids)
            
            # Return first document ID as primary evidence ID
            evidence_id = doc_ids[0] if doc_ids else str(uuid.uuid4())
            
            # Log storage statistics
            total_chars = sum(len(doc.page_content) for doc in enhanced_documents)
            logger.info(f"Stored {len(enhanced_documents)} enhanced documents via ParentDocumentRetriever:")
            logger.info(f"  - Primary evidence ID: {evidence_id}")
            logger.info(f"  - Total content: {total_chars:,} characters")
            logger.info(f"  - Policy: {policy_name}")
            logger.info(f"  - spaCy enhancement: enabled")
            
            return evidence_id
            
        except Exception as e:
            logger.error(f"Failed to store documents with enhanced retriever: {str(e)}")
            raise
    
    def _enhance_documents_with_spacy(self, documents: List[Document], policy_name: str) -> List[Document]:
        """Enhance documents with spaCy-processed metadata."""
        enhanced_documents = []
        
        for doc in documents:
            try:
                # Process text with spaCy
                processed_text = text_processor.process_text(doc.page_content)
                
                # Extract compliance keywords
                compliance_keywords = text_processor.extract_compliance_keywords(doc.page_content)
                
                # Update metadata with spaCy features
                enhanced_metadata = doc.metadata.copy()
                enhanced_metadata.update({
                    'policy_name': policy_name,
                    'is_parent_document': True,
                    'stored_at': datetime.utcnow().isoformat(),
                    'processed_at': datetime.utcnow().isoformat(),
                    'spacy_entities': json.dumps([
                        {'text': e['text'], 'label': e['label']} 
                        for e in processed_text.entities[:10]  # Limit to top 10
                    ]),
                    'spacy_key_terms': json.dumps(processed_text.key_terms[:15]),
                    'compliance_keywords': json.dumps(compliance_keywords),
                    'similarity_features': json.dumps(processed_text.similarity_features[:20])
                })
                
                # Create enhanced document
                enhanced_doc = Document(
                    page_content=doc.page_content,
                    metadata=enhanced_metadata
                )
                enhanced_documents.append(enhanced_doc)
                
            except Exception as e:
                logger.warning(f"Failed to enhance document with spaCy: {str(e)}")
                # Add original document with basic metadata
                doc.metadata['policy_name'] = policy_name
                doc.metadata['is_parent_document'] = True
                doc.metadata['stored_at'] = datetime.utcnow().isoformat()
                enhanced_documents.append(doc)
        
        return enhanced_documents
    
    def similarity_search_with_retriever(self, query_text: str, policy_name: str, k: int = 5) -> List[SimilarEvidenceResult]:
        """
        Perform enhanced similarity search using spaCy-optimized queries.
        
        Args:
            query_text: Query text for similarity search
            policy_name: Policy name for filtering
            k: Number of similar documents to retrieve
            
        Returns:
            List of similar evidence results with enhanced context
        """
        try:
            # Enhance query using spaCy processing
            enhanced_query = self._enhance_query_with_spacy(query_text)
            
            # Get ParentDocumentRetriever for this policy
            retriever = self.get_parent_document_retriever(policy_name, use_spacy_chunking=True)
            
            # Update search parameters
            retriever.search_kwargs = {
                "k": k,
                "filter": {
                    "policy_name": policy_name,
                    "validation_status": [ValidationStatus.COMPLIANT.value, ValidationStatus.NON_COMPLIANT.value]
                }
            }
            
            # Perform retrieval (returns parent documents)
            similar_docs = retriever.get_relevant_documents(enhanced_query)
            
            # Convert to SimilarEvidenceResult objects with spaCy enhancement
            results = []
            for i, doc in enumerate(similar_docs):
                # Calculate similarity score using spaCy if available
                similarity_score = self._calculate_enhanced_similarity(query_text, doc.page_content, i)
                
                # Extract rule assessments from metadata
                rule_assessments = []
                if 'rule_assessments' in doc.metadata:
                    try:
                        rule_assessments = json.loads(doc.metadata['rule_assessments'])
                    except (json.JSONDecodeError, TypeError):
                        rule_assessments = []
                
                result = SimilarEvidenceResult(
                    content=doc.page_content,
                    metadata=doc.metadata,
                    similarity_score=similarity_score,
                    validation_status=ValidationStatus(doc.metadata.get('validation_status', 'pending')),
                    rule_assessments=rule_assessments
                )
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} similar documents with spaCy enhancement for policy: {policy_name}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform enhanced similarity search: {str(e)}")
            return []
    
    def _enhance_query_with_spacy(self, query_text: str) -> str:
        """Enhance query text using spaCy processing."""
        try:
            # Process query with spaCy
            processed_query = text_processor.process_text(query_text)
            
            # Build enhanced query using extracted features
            enhanced_query = text_processor.build_similarity_query([processed_query], max_query_length=800)
            
            logger.debug(f"Enhanced query: '{query_text[:100]}...' -> '{enhanced_query[:100]}...'")
            return enhanced_query
            
        except Exception as e:
            logger.warning(f"Failed to enhance query with spaCy: {str(e)}")
            return query_text
    
    def _calculate_enhanced_similarity(self, query_text: str, doc_content: str, rank: int) -> float:
        """Calculate enhanced similarity score using spaCy and ranking."""
        try:
            # Base similarity from spaCy
            spacy_similarity = text_processor.calculate_text_similarity(query_text, doc_content)
            
            # Ranking-based similarity (higher rank = lower similarity)
            rank_similarity = max(0.95 - (rank * 0.1), 0.1)
            
            # Combine similarities with weights
            combined_similarity = (spacy_similarity * 0.6) + (rank_similarity * 0.4)
            
            return min(combined_similarity, 1.0)
            
        except Exception as e:
            logger.warning(f"Failed to calculate enhanced similarity: {str(e)}")
            # Fallback to rank-based similarity
            return max(0.9 - (rank * 0.1), 0.1)
    
    def store_documents(self, documents: List[ProcessedDocument], policy_name: str) -> str:
        """
        Legacy method for backward compatibility.
        Converts ProcessedDocuments to Documents and uses enhanced storage.
        """
        try:
            # Convert ProcessedDocuments to Documents
            langchain_docs = []
            for doc in documents:
                doc.metadata.policy_name = policy_name
                langchain_doc = doc.to_langchain_document()
                langchain_docs.append(langchain_doc)
            
            # Use enhanced storage
            return self.store_documents_with_retriever(langchain_docs, policy_name)
            
        except Exception as e:
            logger.error(f"Failed to store ProcessedDocuments: {str(e)}")
            raise
    
    def similarity_search(self, query_documents: List[ProcessedDocument], k: int = 5) -> List[SimilarEvidenceResult]:
        """
        Legacy method for backward compatibility.
        Uses spaCy-enhanced query building and retrieval.
        """
        try:
            # Extract policy name from first document
            policy_name = "General"
            if query_documents and hasattr(query_documents[0].metadata, 'policy_name'):
                policy_name = query_documents[0].metadata.policy_name or "General"
            
            # Process documents with spaCy
            processed_texts = []
            for doc in query_documents[:3]:  # Limit to first 3 documents
                processed_text = text_processor.process_text(doc.content)
                processed_texts.append(processed_text)
            
            # Build enhanced query
            enhanced_query = text_processor.build_similarity_query(processed_texts)
            
            # Use enhanced search
            return self.similarity_search_with_retriever(enhanced_query, policy_name, k)
            
        except Exception as e:
            logger.error(f"Failed to perform legacy similarity search: {str(e)}")
            return []
    
    def update_document_status(self, evidence_id: str, evaluation_result: Dict[str, Any]) -> bool:
        """Update document validation status with enhanced metadata."""
        try:
            # Initialize Spanner client for direct updates
            client = spanner.Client(project=self.project_id)
            instance = client.instance(self.instance_id)
            database = instance.database(self.database_id)
            
            # Prepare update data
            validation_status = evaluation_result['decision']
            rule_assessments_json = json.dumps(evaluation_result['rule_assessments'])
            analysis_summary = evaluation_result['analysis_summary']
            confidence_score = evaluation_result['confidence_score']
            
            # Update document with enhanced metadata
            with database.batch() as batch:
                batch.update(
                    table=self.table_name,
                    columns=[
                        'langchain_id', 'validation_status', 'rule_assessments',
                        'analysis_summary', 'confidence_score', 'updated_at'
                    ],
                    values=[(
                        evidence_id, validation_status, rule_assessments_json,
                        analysis_summary, confidence_score, datetime.utcnow()
                    )]
                )
            
            logger.info(f"Successfully updated document {evidence_id} with enhanced status: {validation_status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")
            return False
    
    def get_document_statistics(self, policy_name: Optional[str] = None) -> Dict[str, Any]:
        """Get enhanced statistics about stored documents."""
        try:
            stats = {
                'vector_store_table': self.table_name,
                'embedding_model': config.embedding_model_name,
                'embedding_dimensions': config.embedding_dimensions,
                'retriever_type': 'ParentDocumentRetriever with GCS + spaCy',
                'document_store': 'GCS',
                'text_processor': 'spaCy',
                'parent_chunk_size': config.max_chunk_size,
                'child_chunk_size': config.child_chunk_size,
                'chunk_overlap': config.chunk_overlap,
                'spacy_features': {
                    'model_name': text_processor.nlp.meta.get('name', 'unknown'),
                    'ner_enabled': config.enable_spacy_ner,
                    'similarity_enabled': config.enable_spacy_similarity
                }
            }
            
            if policy_name:
                stats['policy_filter'] = policy_name
                stats['has_cached_retriever'] = f"{policy_name}_True" in self._retriever_cache
            
            # Add GCS storage stats
            gcs_stats = self.docstore.get_storage_stats()
            stats['gcs_storage'] = gcs_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get document statistics: {str(e)}")
            return {}
    
    def cleanup_cache(self):
        """Clean up cached retrievers and perform maintenance."""
        self._retriever_cache.clear()
        
        # Cleanup old GCS documents if configured
        try:
            max_age_days = int(os.getenv('GCS_CLEANUP_MAX_AGE_DAYS', '30'))
            deleted_count = self.docstore.cleanup_old_documents(max_age_days)
            logger.info(f"Cleaned up {deleted_count} old GCS documents")
        except Exception as e:
            logger.warning(f"Failed to cleanup GCS documents: {str(e)}")
        
        logger.info("Cleared ParentDocumentRetriever cache and performed maintenance")

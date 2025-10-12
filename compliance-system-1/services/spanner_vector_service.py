"""
Enhanced SpannerVectorService with ParentDocumentRetriever support.

This service now provides optimized vector storage for large documents using
parent-child document relationships for better semantic search.
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
from langchain.storage import InMemoryStore

from ..models.data_models import (
    ProcessedDocument, SimilarEvidenceResult, 
    ValidationStatus, ComplianceRequest
)
from ..core.config import config

logger = logging.getLogger(__name__)


class SpannerVectorService:
    """Enhanced service for interacting with GCP Spanner vector store with ParentDocumentRetriever support."""
    
    def __init__(self):
        """Initialize Spanner vector service with ParentDocumentRetriever capabilities."""
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
        
        # Initialize vector store with enhanced metadata columns for parent-child relationships
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
                'extraction_methods', 'content_types', 'is_parent_document'
            ]
        )
        
        # Initialize document store for parent documents
        self.docstore = InMemoryStore()
        
        # Cache for ParentDocumentRetriever instances
        self._retriever_cache = {}
        
        logger.info(f"Initialized enhanced Spanner vector service: {self.instance_id}/{self.database_id}")
    
    def get_vector_store(self) -> SpannerVectorStore:
        """Get the underlying vector store instance."""
        return self.vector_store
    
    def get_parent_document_retriever(self, policy_name: str) -> ParentDocumentRetriever:
        """
        Get or create a ParentDocumentRetriever for the specified policy.
        
        Args:
            policy_name: Policy name for filtering and retrieval
            
        Returns:
            Configured ParentDocumentRetriever instance
        """
        try:
            # Check cache first
            if policy_name in self._retriever_cache:
                return self._retriever_cache[policy_name]
            
            # Create text splitters
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            
            # Parent splitter for larger context documents
            parent_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.max_chunk_size,
                chunk_overlap=config.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
                keep_separator=True
            )
            
            # Child splitter for smaller, more focused search chunks
            child_splitter = RecursiveCharacterTextSplitter(
                chunk_size=400,  # Smaller for better semantic search
                chunk_overlap=50,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
                keep_separator=True
            )
            
            # Create ParentDocumentRetriever
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
            self._retriever_cache[policy_name] = retriever
            
            logger.info(f"Created ParentDocumentRetriever for policy: {policy_name}")
            return retriever
            
        except Exception as e:
            logger.error(f"Failed to create ParentDocumentRetriever: {str(e)}")
            raise
    
    def store_documents_with_retriever(self, documents: List[Document], policy_name: str) -> str:
        """
        Store documents using ParentDocumentRetriever for optimal parent-child relationships.
        
        Args:
            documents: List of parent documents to store
            policy_name: Policy name for evidence type classification
            
        Returns:
            Primary evidence ID for the stored documents
        """
        try:
            # Get ParentDocumentRetriever for this policy
            retriever = self.get_parent_document_retriever(policy_name)
            
            # Generate document IDs
            doc_ids = [doc.metadata.get('parent_id', str(uuid.uuid4())) for doc in documents]
            
            # Ensure policy_name in metadata
            for doc in documents:
                doc.metadata['policy_name'] = policy_name
                doc.metadata['is_parent_document'] = True
                doc.metadata['stored_at'] = datetime.utcnow().isoformat()
            
            # Add documents to retriever (handles parent-child splitting and storage)
            retriever.add_documents(documents=documents, ids=doc_ids)
            
            # Return first document ID as primary evidence ID
            evidence_id = doc_ids[0] if doc_ids else str(uuid.uuid4())
            
            # Log storage statistics
            total_chars = sum(len(doc.page_content) for doc in documents)
            logger.info(f"Stored {len(documents)} parent documents via ParentDocumentRetriever:")
            logger.info(f"  - Primary evidence ID: {evidence_id}")
            logger.info(f"  - Total content: {total_chars:,} characters")
            logger.info(f"  - Policy: {policy_name}")
            
            return evidence_id
            
        except Exception as e:
            logger.error(f"Failed to store documents with ParentDocumentRetriever: {str(e)}")
            raise
    
    def similarity_search_with_retriever(self, query_text: str, policy_name: str, k: int = 5) -> List[SimilarEvidenceResult]:
        """
        Perform similarity search using ParentDocumentRetriever.
        
        This provides better results by:
        1. Searching on smaller, focused child chunks
        2. Returning full parent documents for context
        3. Maintaining document relationships
        
        Args:
            query_text: Query text for similarity search
            policy_name: Policy name for filtering
            k: Number of similar documents to retrieve
            
        Returns:
            List of similar evidence results with full parent context
        """
        try:
            # Get ParentDocumentRetriever for this policy
            retriever = self.get_parent_document_retriever(policy_name)
            
            # Update search parameters
            retriever.search_kwargs = {
                "k": k,
                "filter": {
                    "policy_name": policy_name,
                    "validation_status": [ValidationStatus.COMPLIANT.value, ValidationStatus.NON_COMPLIANT.value]
                }
            }
            
            # Perform retrieval (returns parent documents)
            similar_docs = retriever.get_relevant_documents(query_text)
            
            # Convert to SimilarEvidenceResult objects
            results = []
            for i, doc in enumerate(similar_docs):
                # Extract rule assessments from metadata
                rule_assessments = []
                if 'rule_assessments' in doc.metadata:
                    try:
                        rule_assessments = json.loads(doc.metadata['rule_assessments'])
                    except (json.JSONDecodeError, TypeError):
                        rule_assessments = []
                
                # Calculate similarity score (approximate based on ranking)
                similarity_score = max(0.9 - (i * 0.1), 0.1)
                
                result = SimilarEvidenceResult(
                    content=doc.page_content,
                    metadata=doc.metadata,
                    similarity_score=similarity_score,
                    validation_status=ValidationStatus(doc.metadata.get('validation_status', 'pending')),
                    rule_assessments=rule_assessments
                )
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} similar parent documents for policy: {policy_name}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search with retriever: {str(e)}")
            return []
    
    def store_documents(self, documents: List[ProcessedDocument], policy_name: str) -> str:
        """
        Legacy method for backward compatibility.
        Converts ProcessedDocuments to Documents and uses retriever storage.
        
        Args:
            documents: List of processed documents to store
            policy_name: Policy name for evidence type classification
            
        Returns:
            Primary evidence ID for the stored documents
        """
        try:
            # Convert ProcessedDocuments to Documents
            langchain_docs = []
            for doc in documents:
                doc.metadata.policy_name = policy_name
                langchain_doc = doc.to_langchain_document()
                langchain_docs.append(langchain_doc)
            
            # Use retriever-based storage
            return self.store_documents_with_retriever(langchain_docs, policy_name)
            
        except Exception as e:
            logger.error(f"Failed to store ProcessedDocuments: {str(e)}")
            raise
    
    def similarity_search(self, query_documents: List[ProcessedDocument], k: int = 5) -> List[SimilarEvidenceResult]:
        """
        Legacy method for backward compatibility.
        Converts to query text and uses retriever-based search.
        
        Args:
            query_documents: Documents to search for similar content
            k: Number of similar documents to retrieve
            
        Returns:
            List of similar evidence results
        """
        try:
            # Extract policy name from first document
            policy_name = "General"
            if query_documents and hasattr(query_documents[0].metadata, 'policy_name'):
                policy_name = query_documents[0].metadata.policy_name or "General"
            
            # Combine content from query documents
            combined_content = ' '.join([doc.content[:500] for doc in query_documents[:3]])
            
            # Use retriever-based search
            return self.similarity_search_with_retriever(combined_content, policy_name, k)
            
        except Exception as e:
            logger.error(f"Failed to perform legacy similarity search: {str(e)}")
            return []
    
    def update_document_status(self, evidence_id: str, evaluation_result: Dict[str, Any]) -> bool:
        """
        Update document validation status and results for parent documents.
        
        Args:
            evidence_id: ID of the parent document to update
            evaluation_result: Evaluation results from LLM
            
        Returns:
            True if update successful, False otherwise
        """
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
            
            # Update both parent and child documents with the same parent_id
            with database.batch() as batch:
                # Update parent document
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
                
                # Also update any child documents with matching parent_id
                # Note: This would require a more complex query in practice
                # For now, we update the main document
            
            logger.info(f"Successfully updated document {evidence_id} with status: {validation_status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")
            return False
    
    def get_document_statistics(self, policy_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about stored documents."""
        try:
            # This would require querying the Spanner database for actual statistics
            # For now, return basic info
            stats = {
                'vector_store_table': self.table_name,
                'embedding_model': config.embedding_model_name,
                'embedding_dimensions': config.embedding_dimensions,
                'retriever_type': 'ParentDocumentRetriever',
                'parent_chunk_size': config.max_chunk_size,
                'child_chunk_size': 400,
                'chunk_overlap': config.chunk_overlap
            }
            
            if policy_name:
                stats['policy_filter'] = policy_name
                stats['has_cached_retriever'] = policy_name in self._retriever_cache
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get document statistics: {str(e)}")
            return {}
    
    def cleanup_cache(self):
        """Clean up cached retrievers."""
        self._retriever_cache.clear()
        logger.info("Cleared ParentDocumentRetriever cache")

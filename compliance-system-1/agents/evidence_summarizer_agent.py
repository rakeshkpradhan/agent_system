"""
Agent 1: Evidence Summarizer Agent (Data Ingestion Pipeline) - Updated with ParentDocumentRetriever

This agent is responsible for fetching, parsing, and storing evidence from Confluence pages.
Now uses LangChain ParentDocumentRetriever for optimal handling of large documents.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain_core.documents import Document

from ..models.data_models import WorkflowState, ProcessedDocument, ValidationStatus
from ..services.external_services import ConfluenceService
from ..services.spanner_vector_service import SpannerVectorService
from ..utils.content_parser import ContentParser, create_parsing_strategies
from ..core.config import config

logger = logging.getLogger(__name__)


class EvidenceSummarizerAgent:
    """
    Agent responsible for fetching, parsing, and storing evidence from Confluence.
    
    Uses ParentDocumentRetriever for optimal handling of large documents:
    - Stores small chunks for better semantic search
    - Maintains parent documents for full context
    - Supports multiple text splitting strategies
    """
    
    def __init__(self):
        """Initialize the Evidence Summarizer Agent with ParentDocumentRetriever."""
        self.confluence_service = ConfluenceService()
        self.vector_service = SpannerVectorService()
        
        # Initialize content parser with Confluence-optimized strategy
        strategies = create_parsing_strategies()
        self.content_parser = ContentParser(strategies['confluence_optimized'])
        
        # Initialize text splitters for different content types
        self._init_text_splitters()
        
        # ParentDocumentRetriever will be initialized per request
        self.parent_retriever = None
        
        logger.info("Initialized Evidence Summarizer Agent with ParentDocumentRetriever")
    
    def _init_text_splitters(self):
        """Initialize various text splitters for different content types."""
        
        # Primary recursive splitter for general content
        self.primary_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.max_chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        # Child splitter for smaller chunks used in retrieval
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,  # Smaller chunks for better semantic search
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        # Markdown header splitter for structured documents
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"), 
                ("###", "Header 3"),
                ("####", "Header 4"),
            ],
            strip_headers=False
        )
        
        # Table-specific splitter (custom implementation)
        self.table_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,  # Larger chunks for tables
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", " | ", " ", ""],
            keep_separator=True
        )
        
        logger.info("Initialized multiple text splitters for content processing")
    
    async def process(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main processing method for Evidence Summarizer Agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary with processing results and updated state
        """
        try:
            request = state.request
            logger.info(f"Processing evidence from URL: {request.evidence_url}")
            state.add_message(f"Starting evidence processing for {request.policy_name}")
            
            # Get ParentDocumentRetriever for this request
            self.parent_retriever = self.vector_service.get_parent_document_retriever(request.policy_name)
            
            # Task 1: Fetch Content
            html_content = self._fetch_content(request.evidence_url)
            state.add_message(f"Successfully fetched content ({len(html_content)} characters)")
            
            # Task 2: Parse and Structure Content  
            raw_documents = self._parse_and_structure_content(html_content, request.evidence_url)
            state.add_message(f"Parsed content into {len(raw_documents)} raw document segments")
            
            # Task 3: Create Parent Documents with Smart Splitting
            parent_documents = self._create_parent_documents(raw_documents, request.policy_name)
            state.add_message(f"Created {len(parent_documents)} parent documents")
            
            # Task 4: Embed and Store using ParentDocumentRetriever
            evidence_id = await self._embed_and_store_with_retriever(parent_documents, request.policy_name)
            state.add_message(f"Stored documents with evidence ID: {evidence_id}")
            
            return {
                'evidence_documents': parent_documents,
                'evidence_id': evidence_id,
                'parent_retriever': self.parent_retriever,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"EvidenceSummarizerAgent failed: {str(e)}"
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
            List of ProcessedDocument objects (raw, before splitting)
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
    
    def _create_parent_documents(self, raw_documents: List[ProcessedDocument], policy_name: str) -> List[Document]:
        """
        Task 3: Create Parent Documents with intelligent splitting strategies.
        
        Groups related content and applies appropriate splitting based on content type.
        
        Args:
            raw_documents: Raw parsed documents
            policy_name: Policy name for metadata
            
        Returns:
            List of parent Document objects ready for ParentDocumentRetriever
        """
        try:
            logger.info("Creating parent documents with intelligent splitting")
            
            # Group documents by content type and section
            grouped_docs = self._group_documents_by_context(raw_documents)
            
            parent_documents = []
            
            for group_key, doc_group in grouped_docs.items():
                # Combine related documents into larger parent documents
                combined_content = self._combine_document_group(doc_group)
                
                if len(combined_content.strip()) < 100:  # Skip very small groups
                    continue
                
                # Create parent document with comprehensive metadata
                parent_doc = Document(
                    page_content=combined_content,
                    metadata={
                        'source_url': doc_group[0].metadata.source_url,
                        'policy_name': policy_name,
                        'content_group': group_key,
                        'document_count': len(doc_group),
                        'extraction_methods': list(set(doc.metadata.extraction_method for doc in doc_group)),
                        'content_types': list(set(doc.metadata.content_type for doc in doc_group)),
                        'parent_id': str(uuid.uuid4()),
                        'timestamp': datetime.utcnow().isoformat(),
                        'validation_status': ValidationStatus.PENDING.value,
                        'total_length': len(combined_content),
                        'is_parent_document': True
                    }
                )
                
                parent_documents.append(parent_doc)
            
            logger.info(f"Created {len(parent_documents)} parent documents from {len(raw_documents)} raw documents")
            return parent_documents
            
        except Exception as e:
            logger.error(f"Failed to create parent documents: {str(e)}")
            raise
    
    def _group_documents_by_context(self, documents: List[ProcessedDocument]) -> Dict[str, List[ProcessedDocument]]:
        """Group documents by contextual similarity for better parent document creation."""
        groups = {}
        
        for doc in documents:
            # Create grouping key based on section header, content type, and extraction method
            section = doc.metadata.section_header or "general"
            content_type = doc.metadata.content_type or "text"
            
            # Clean and normalize section names
            section_key = section.replace(" ", "_").lower()[:50]
            group_key = f"{content_type}_{section_key}"
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(doc)
        
        # Merge very small groups with similar groups
        groups = self._merge_small_groups(groups)
        
        logger.info(f"Grouped {len(documents)} documents into {len(groups)} contextual groups")
        return groups
    
    def _merge_small_groups(self, groups: Dict[str, List[ProcessedDocument]]) -> Dict[str, List[ProcessedDocument]]:
        """Merge very small groups with similar groups to avoid fragmentation."""
        min_group_size = 2
        merged_groups = {}
        small_groups = {}
        
        # Separate large and small groups
        for key, docs in groups.items():
            if len(docs) >= min_group_size:
                merged_groups[key] = docs
            else:
                content_type = key.split('_')[0]
                if content_type not in small_groups:
                    small_groups[content_type] = []
                small_groups[content_type].extend(docs)
        
        # Add merged small groups back
        for content_type, docs in small_groups.items():
            if docs:
                merged_key = f"{content_type}_merged"
                merged_groups[merged_key] = docs
        
        return merged_groups
    
    def _combine_document_group(self, doc_group: List[ProcessedDocument]) -> str:
        """Combine a group of documents into a single coherent text."""
        sections = []
        
        # Sort by section header if available
        sorted_docs = sorted(doc_group, key=lambda d: d.metadata.section_header or "")
        
        current_section = None
        section_content = []
        
        for doc in sorted_docs:
            section_header = doc.metadata.section_header
            
            # Start new section if header changed
            if section_header != current_section and section_header:
                if section_content:
                    sections.append("\n".join(section_content))
                    section_content = []
                
                current_section = section_header
                section_content.append(f"## {section_header}")
            
            # Add document content
            section_content.append(doc.content)
        
        # Add final section
        if section_content:
            sections.append("\n".join(section_content))
        
        return "\n\n".join(sections)
    
    async def _embed_and_store_with_retriever(self, parent_documents: List[Document], policy_name: str) -> str:
        """
        Task 4: Generate embeddings and store using ParentDocumentRetriever.
        
        Uses the retriever to automatically handle parent-child relationships,
        embedding generation, and storage in Spanner vector store.
        
        Args:
            parent_documents: List of parent Document objects
            policy_name: Policy name for evidence type classification
            
        Returns:
            Primary evidence ID for the stored documents
        """
        try:
            logger.info(f"Storing {len(parent_documents)} parent documents using ParentDocumentRetriever")
            
            # Use the enhanced vector service to store documents
            evidence_id = self.vector_service.store_documents_with_retriever(parent_documents, policy_name)
            
            # Log storage statistics
            total_chars = sum(len(doc.page_content) for doc in parent_documents)
            avg_doc_size = total_chars / len(parent_documents) if parent_documents else 0
            
            logger.info(f"Successfully stored documents with ParentDocumentRetriever:")
            logger.info(f"  - Parent documents: {len(parent_documents)}")
            logger.info(f"  - Total characters: {total_chars:,}")
            logger.info(f"  - Average document size: {avg_doc_size:.0f} chars")
            logger.info(f"  - Primary evidence ID: {evidence_id}")
            
            return evidence_id
            
        except Exception as e:
            logger.error(f"Failed to store documents with ParentDocumentRetriever: {str(e)}")
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
        """Get the ParentDocumentRetriever instance for use by other agents."""
        return self.parent_retriever
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for monitoring."""
        return {
            'agent_name': 'EvidenceSummarizerAgent',
            'retriever_type': 'ParentDocumentRetriever',
            'parsing_strategies': ['trafilatura', 'beautifulsoup', 'confluence_specific'],
            'text_splitters': {
                'primary_chunk_size': config.max_chunk_size,
                'child_chunk_size': 400,
                'chunk_overlap': config.chunk_overlap
            },
            'embedding_model': config.embedding_model_name,
            'splitting_strategies': ['recursive', 'markdown_header', 'table_specific']
        }

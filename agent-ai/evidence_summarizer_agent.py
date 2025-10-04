"""
Agent 1: Evidence Summarizer Agent (Data Ingestion Pipeline)

This agent is responsible for fetching, parsing, and storing evidence from Confluence pages.
It implements a multi-strategy approach for content extraction and embedding generation.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..models.data_models import WorkflowState, ProcessedDocument, ValidationStatus
from ..services.external_services import ConfluenceService, SpannerVectorService
from ..utils.content_parser import ContentParser, create_parsing_strategies
from ..core.config import config

logger = logging.getLogger(__name__)


class EvidenceSummarizerAgent:
    """
    Agent responsible for fetching, parsing, and storing evidence from Confluence.

    This agent performs four main tasks:
    1. Fetch Content: Securely retrieve HTML content from Confluence
    2. Parse and Structure Content: Extract meaningful text using multiple strategies
    3. Create Documents: Convert chunks to Document objects with metadata
    4. Embed and Store: Generate embeddings and store in Spanner vector store
    """

    def __init__(self):
        """Initialize the Evidence Summarizer Agent."""
        self.confluence_service = ConfluenceService()
        self.vector_service = SpannerVectorService()

        # Initialize content parser with Confluence-optimized strategy
        strategies = create_parsing_strategies()
        self.content_parser = ContentParser(strategies['confluence_optimized'])

        logger.info("Initialized Evidence Summarizer Agent")

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

            # Task 1: Fetch Content
            html_content = self._fetch_content(request.evidence_url)
            state.add_message(f"Successfully fetched content ({len(html_content)} characters)")

            # Task 2: Parse and Structure Content
            documents = self._parse_and_structure_content(html_content, request.evidence_url)
            state.add_message(f"Parsed content into {len(documents)} document chunks")

            # Task 3: Create Documents (already done in parsing)
            processed_docs = self._validate_and_enrich_documents(documents, request.policy_name)
            state.add_message(f"Validated and enriched {len(processed_docs)} documents")

            # Task 4: Embed and Store
            evidence_id = self._embed_and_store(processed_docs, request.policy_name)
            state.add_message(f"Stored documents with evidence ID: {evidence_id}")

            return {
                'evidence_documents': processed_docs,
                'evidence_id': evidence_id,
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

        This method uses BeautifulSoup, Trafilatura, and custom Confluence parsing
        to extract meaningful text, tables, lists while filtering boilerplate.

        Args:
            html_content: Raw HTML content to parse
            source_url: Source URL for metadata

        Returns:
            List of ProcessedDocument objects
        """
        try:
            logger.info("Parsing and structuring HTML content")

            # Use content parser with multiple strategies
            documents = self.content_parser.parse_html_content(html_content, source_url)

            # Additional processing for Confluence-specific elements
            documents = self._post_process_confluence_content(documents)

            # Limit documents to prevent overwhelming downstream processing
            max_chunks = config.max_evidence_chunks
            if len(documents) > max_chunks:
                logger.warning(f"Limiting documents from {len(documents)} to {max_chunks}")
                documents = documents[:max_chunks]

            logger.info(f"Successfully parsed content into {len(documents)} document chunks")
            return documents

        except Exception as e:
            logger.error(f"Failed to parse HTML content: {str(e)}")
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

    def _validate_and_enrich_documents(self, documents: List[ProcessedDocument], policy_name: str) -> List[ProcessedDocument]:
        """
        Task 3: Validate and enrich documents with additional metadata.

        Args:
            documents: List of ProcessedDocument objects to validate
            policy_name: Policy name for metadata enrichment

        Returns:
            List of validated and enriched ProcessedDocument objects
        """
        try:
            validated_docs = []

            for i, doc in enumerate(documents):
                # Validate document content
                if not self._is_valid_document(doc):
                    logger.debug(f"Skipping invalid document chunk {i}")
                    continue

                # Enrich metadata
                doc.metadata.policy_name = policy_name
                doc.metadata.validation_status = ValidationStatus.PENDING
                doc.metadata.timestamp = datetime.utcnow().isoformat()

                # Add sequential chunk numbering if not present
                if not doc.metadata.chunk_id:
                    doc.metadata.chunk_id = f"chunk_{i}"

                validated_docs.append(doc)

            logger.info(f"Validated {len(validated_docs)} documents out of {len(documents)}")
            return validated_docs

        except Exception as e:
            logger.error(f"Failed to validate documents: {str(e)}")
            raise

    def _is_valid_document(self, doc: ProcessedDocument) -> bool:
        """Validate document meets quality criteria."""
        content = doc.content.strip()

        # Check minimum length
        if len(content) < 50:
            return False

        # Check for meaningful content (not just symbols/whitespace)
        if len(content.replace(' ', '').replace('\n', '')) < 20:
            return False

        # Check for excessive repetition
        words = content.split()
        if len(words) > 10:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # Less than 30% unique words
                return False

        return True

    def _embed_and_store(self, documents: List[ProcessedDocument], policy_name: str) -> str:
        """
        Task 4: Generate embeddings and store in Spanner vector store.

        Args:
            documents: List of ProcessedDocument objects to store
            policy_name: Policy name for evidence type classification

        Returns:
            Primary evidence ID for the stored documents
        """
        try:
            logger.info(f"Generating embeddings and storing {len(documents)} documents")

            # Store documents using vector service
            evidence_id = self.vector_service.store_documents(documents, policy_name)

            if not evidence_id:
                raise ValueError("Failed to get evidence ID from vector store")

            logger.info(f"Successfully stored documents with evidence ID: {evidence_id}")
            return evidence_id

        except Exception as e:
            logger.error(f"Failed to embed and store documents: {str(e)}")
            raise

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for monitoring."""
        return {
            'agent_name': 'EvidenceSummarizerAgent',
            'parsing_strategies': ['trafilatura', 'beautifulsoup', 'confluence_specific'],
            'max_chunks': config.max_evidence_chunks,
            'embedding_model': config.embedding_model_name
        }

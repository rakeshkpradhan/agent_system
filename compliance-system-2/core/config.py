"""
Enhanced Configuration management with GCS and spaCy support.

This module handles all configuration including environment variables,
GCP Secret Manager integration, GCS setup, and spaCy model configuration.
"""

import os
import logging
from typing import Optional, Dict, Any
from google.cloud import secretmanager
from google.auth.exceptions import DefaultCredentialsError

logger = logging.getLogger(__name__)


class ConfigManager:
    """Enhanced configuration management with GCS and spaCy integration."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.project_id = self._get_required_env('GCP_PROJECT_ID')
        self.location = os.getenv('GCP_LOCATION', 'us-central1')
        
        # Initialize secret manager client
        try:
            self.secret_client = secretmanager.SecretManagerServiceClient()
            self.project_path = f"projects/{self.project_id}"
            logger.info("Successfully initialized GCP Secret Manager client")
        except DefaultCredentialsError as e:
            logger.error(f"Failed to initialize GCP credentials: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Secret Manager client: {str(e)}")
            raise
    
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """Retrieve secret from GCP Secret Manager."""
        try:
            secret_path = f"{self.project_path}/secrets/{secret_name}/versions/{version}"
            response = self.secret_client.access_secret_version(request={"name": secret_path})
            secret_value = response.payload.data.decode('UTF-8')
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return secret_value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {str(e)}")
            raise
    
    def get_secret_safe(self, secret_name: str, version: str = "latest", default: Optional[str] = None) -> Optional[str]:
        """Safely retrieve secret, returning default if not found."""
        try:
            return self.get_secret(secret_name, version)
        except Exception as e:
            logger.warning(f"Could not retrieve secret {secret_name}: {str(e)}")
            return default
    
    # Confluence Configuration
    @property
    def confluence_api_token(self) -> str:
        """Get Confluence API token from Secret Manager."""
        return self.get_secret('confluence-api-token')
    
    @property
    def confluence_base_url(self) -> str:
        """Get Confluence base URL from environment or default."""
        return os.getenv('CONFLUENCE_BASE_URL', 'https://your-company.atlassian.net')
    
    @property
    def confluence_username(self) -> str:
        """Get Confluence username from Secret Manager."""
        return self.get_secret('confluence-username')
    
    # GCP Spanner Configuration
    @property
    def spanner_instance_id(self) -> str:
        """Get Spanner instance ID."""
        return os.getenv('SPANNER_INSTANCE_ID', 'compliance-instance')
    
    @property
    def spanner_database_id(self) -> str:
        """Get Spanner database ID."""
        return os.getenv('SPANNER_DATABASE_ID', 'compliance-db')
    
    @property
    def spanner_vector_table_name(self) -> str:
        """Get Spanner vector store table name."""
        return os.getenv('SPANNER_VECTOR_TABLE_NAME', 'evidence_embeddings')
    
    # GCP SpannerGraph Configuration
    @property
    def spanner_graph_name(self) -> str:
        """Get Spanner graph name for policy rules."""
        return os.getenv('SPANNER_GRAPH_NAME', 'PolicyGraph')
    
    # GCS Configuration
    @property
    def gcs_bucket_name(self) -> str:
        """Get GCS bucket name for document storage."""
        return os.getenv('GCS_BUCKET_NAME', f'{self.project_id}-compliance-docs')
    
    @property
    def gcs_location(self) -> str:
        """Get GCS bucket location."""
        return os.getenv('GCS_LOCATION', self.location)
    
    @property
    def gcs_document_prefix(self) -> str:
        """Get GCS document prefix."""
        return os.getenv('GCS_DOCUMENT_PREFIX', 'compliance_documents/')
    
    # Vertex AI Configuration
    @property
    def vertex_ai_project(self) -> str:
        """Get Vertex AI project ID."""
        return self.project_id
    
    @property
    def vertex_ai_location(self) -> str:
        """Get Vertex AI location."""
        return self.location
    
    @property
    def embedding_model_name(self) -> str:
        """Get embedding model name."""
        return os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-005')
    
    @property
    def llm_model_name(self) -> str:
        """Get LLM model name."""
        return os.getenv('LLM_MODEL_NAME', 'gemini-2.5-pro')
    
    # spaCy Configuration
    @property
    def spacy_model_name(self) -> str:
        """Get spaCy model name."""
        return os.getenv('SPACY_MODEL_NAME', 'en_core_web_sm')
    
    @property
    def spacy_model_large(self) -> str:
        """Get large spaCy model name for advanced processing."""
        return os.getenv('SPACY_MODEL_LARGE', 'en_core_web_lg')
    
    @property
    def use_spacy_large_model(self) -> bool:
        """Check if large spaCy model should be used."""
        return os.getenv('USE_SPACY_LARGE_MODEL', 'false').lower() == 'true'
    
    @property
    def spacy_max_length(self) -> int:
        """Get maximum text length for spaCy processing."""
        return int(os.getenv('SPACY_MAX_LENGTH', '1000000'))
    
    @property
    def enable_spacy_ner(self) -> bool:
        """Check if spaCy NER should be enabled."""
        return os.getenv('ENABLE_SPACY_NER', 'true').lower() == 'true'
    
    @property
    def enable_spacy_similarity(self) -> bool:
        """Check if spaCy similarity should be used."""
        return os.getenv('ENABLE_SPACY_SIMILARITY', 'true').lower() == 'true'
    
    # Application Configuration
    @property
    def max_evidence_chunks(self) -> int:
        """Get maximum number of evidence chunks to process."""
        return int(os.getenv('MAX_EVIDENCE_CHUNKS', '50'))
    
    @property
    def similarity_search_k(self) -> int:
        """Get number of similar documents to retrieve."""
        return int(os.getenv('SIMILARITY_SEARCH_K', '5'))
    
    @property
    def embedding_dimensions(self) -> int:
        """Get embedding dimensions."""
        return int(os.getenv('EMBEDDING_DIMENSIONS', '768'))
    
    @property
    def max_chunk_size(self) -> int:
        """Get maximum chunk size for document processing."""
        return int(os.getenv('MAX_CHUNK_SIZE', '2000'))
    
    @property
    def child_chunk_size(self) -> int:
        """Get child chunk size for ParentDocumentRetriever."""
        return int(os.getenv('CHILD_CHUNK_SIZE', '400'))
    
    @property
    def chunk_overlap(self) -> int:
        """Get chunk overlap for document processing."""
        return int(os.getenv('CHUNK_OVERLAP', '200'))
    
    @property
    def child_chunk_overlap(self) -> int:
        """Get child chunk overlap."""
        return int(os.getenv('CHILD_CHUNK_OVERLAP', '50'))
    
    # Query Enhancement Configuration
    @property
    def max_query_terms(self) -> int:
        """Get maximum number of query terms to extract."""
        return int(os.getenv('MAX_QUERY_TERMS', '15'))
    
    @property
    def min_term_length(self) -> int:
        """Get minimum term length for query extraction."""
        return int(os.getenv('MIN_TERM_LENGTH', '3'))
    
    @property
    def similarity_threshold(self) -> float:
        """Get similarity threshold for document retrieval."""
        return float(os.getenv('SIMILARITY_THRESHOLD', '0.7'))
    
    # Logging Configuration
    @property
    def log_level(self) -> str:
        """Get log level."""
        return os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def enable_debug_logging(self) -> bool:
        """Check if debug logging is enabled."""
        return os.getenv('ENABLE_DEBUG_LOGGING', 'false').lower() == 'true'
    
    # Flask Configuration
    @property
    def flask_host(self) -> str:
        """Get Flask host."""
        return os.getenv('FLASK_HOST', '0.0.0.0')
    
    @property
    def flask_port(self) -> int:
        """Get Flask port."""
        return int(os.getenv('FLASK_PORT', '5000'))
    
    @property
    def flask_debug(self) -> bool:
        """Check if Flask debug mode is enabled."""
        return os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary (excluding secrets)."""
        return {
            'project_id': self.project_id,
            'location': self.location,
            'confluence_base_url': self.confluence_base_url,
            'spanner_instance_id': self.spanner_instance_id,
            'spanner_database_id': self.spanner_database_id,
            'spanner_vector_table_name': self.spanner_vector_table_name,
            'spanner_graph_name': self.spanner_graph_name,
            'gcs_bucket_name': self.gcs_bucket_name,
            'gcs_location': self.gcs_location,
            'gcs_document_prefix': self.gcs_document_prefix,
            'embedding_model_name': self.embedding_model_name,
            'llm_model_name': self.llm_model_name,
            'spacy_model_name': self.spacy_model_name,
            'use_spacy_large_model': self.use_spacy_large_model,
            'enable_spacy_ner': self.enable_spacy_ner,
            'enable_spacy_similarity': self.enable_spacy_similarity,
            'max_evidence_chunks': self.max_evidence_chunks,
            'similarity_search_k': self.similarity_search_k,
            'embedding_dimensions': self.embedding_dimensions,
            'max_chunk_size': self.max_chunk_size,
            'child_chunk_size': self.child_chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'child_chunk_overlap': self.child_chunk_overlap,
            'max_query_terms': self.max_query_terms,
            'similarity_threshold': self.similarity_threshold,
            'log_level': self.log_level,
            'flask_host': self.flask_host,
            'flask_port': self.flask_port,
            'flask_debug': self.flask_debug
        }
    
    def validate_config(self) -> bool:
        """Validate that all required configuration is available."""
        try:
            # Test GCP access
            _ = self.project_id
            _ = self.spanner_instance_id
            _ = self.spanner_database_id
            _ = self.gcs_bucket_name
            
            # Test secret access (non-blocking)
            confluence_token = self.get_secret_safe('confluence-api-token')
            if not confluence_token:
                logger.warning("Confluence API token not available")
            
            confluence_username = self.get_secret_safe('confluence-username')
            if not confluence_username:
                logger.warning("Confluence username not available")
            
            logger.info("Configuration validation completed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False


# Global configuration instance
config = ConfigManager()

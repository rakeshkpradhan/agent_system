"""
GCS-based Document Store for ParentDocumentRetriever

This module provides a Cloud Storage-based document store that implements
LangChain's BaseStore interface for production-ready document persistence.
"""

import json
import logging
from typing import Iterator, List, Optional, Sequence, Tuple, Any, Dict
from datetime import datetime
import uuid

from google.cloud import storage
from google.cloud.exceptions import NotFound
from langchain.storage.base import BaseStore

from ..core.config import config

logger = logging.getLogger(__name__)


class GCSDocumentStore(BaseStore):
    """
    Google Cloud Storage-based document store for ParentDocumentRetriever.
    
    Provides persistent storage for parent documents with efficient retrieval
    and automatic backup capabilities.
    """
    
    def __init__(self, bucket_name: Optional[str] = None, prefix: str = "compliance_docs/"):
        """
        Initialize GCS document store.
        
        Args:
            bucket_name: GCS bucket name (defaults to config)
            prefix: Object prefix for document organization
        """
        self.bucket_name = bucket_name or config.gcs_bucket_name
        self.prefix = prefix.rstrip('/') + '/'
        
        # Initialize GCS client
        self.client = storage.Client(project=config.project_id)
        self.bucket = self.client.bucket(self.bucket_name)
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
        logger.info(f"Initialized GCS document store: {self.bucket_name}/{self.prefix}")
    
    def _ensure_bucket_exists(self):
        """Ensure the GCS bucket exists, create if necessary."""
        try:
            self.bucket.reload()
            logger.info(f"Using existing GCS bucket: {self.bucket_name}")
        except NotFound:
            try:
                self.bucket = self.client.create_bucket(
                    self.bucket_name,
                    location=config.gcs_location or config.vertex_ai_location
                )
                logger.info(f"Created GCS bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to create GCS bucket: {str(e)}")
                raise
    
    def _get_object_name(self, key: str) -> str:
        """Get full object name with prefix."""
        return f"{self.prefix}{key}.json"
    
    def mget(self, keys: Sequence[str]) -> List[Optional[Any]]:
        """
        Get multiple values by keys.
        
        Args:
            keys: List of keys to retrieve
            
        Returns:
            List of values (None for missing keys)
        """
        results = []
        
        for key in keys:
            try:
                object_name = self._get_object_name(key)
                blob = self.bucket.blob(object_name)
                
                if blob.exists():
                    content = blob.download_as_text()
                    doc_data = json.loads(content)
                    results.append(doc_data['content'])
                else:
                    results.append(None)
                    
            except Exception as e:
                logger.warning(f"Failed to retrieve document {key}: {str(e)}")
                results.append(None)
        
        return results
    
    def mset(self, key_value_pairs: Sequence[Tuple[str, Any]]) -> None:
        """
        Set multiple key-value pairs.
        
        Args:
            key_value_pairs: List of (key, value) tuples
        """
        for key, value in key_value_pairs:
            try:
                object_name = self._get_object_name(key)
                blob = self.bucket.blob(object_name)
                
                # Prepare document data with metadata
                doc_data = {
                    'key': key,
                    'content': value,
                    'stored_at': datetime.utcnow().isoformat(),
                    'content_type': type(value).__name__,
                    'content_length': len(str(value)) if value else 0
                }
                
                # Store as JSON
                blob.upload_from_string(
                    json.dumps(doc_data, ensure_ascii=False),
                    content_type='application/json'
                )
                
                # Set metadata
                blob.metadata = {
                    'key': key,
                    'stored_at': doc_data['stored_at'],
                    'content_type': doc_data['content_type']
                }
                blob.patch()
                
            except Exception as e:
                logger.error(f"Failed to store document {key}: {str(e)}")
                raise
    
    def mdelete(self, keys: Sequence[str]) -> None:
        """
        Delete multiple keys.
        
        Args:
            keys: List of keys to delete
        """
        for key in keys:
            try:
                object_name = self._get_object_name(key)
                blob = self.bucket.blob(object_name)
                
                if blob.exists():
                    blob.delete()
                    logger.debug(f"Deleted document: {key}")
                    
            except Exception as e:
                logger.warning(f"Failed to delete document {key}: {str(e)}")
    
    def yield_keys(self, prefix: Optional[str] = None) -> Iterator[str]:
        """
        Yield all keys with optional prefix filter.
        
        Args:
            prefix: Optional key prefix filter
            
        Yields:
            Document keys
        """
        try:
            # List all objects with the document prefix
            blob_prefix = self.prefix
            if prefix:
                blob_prefix += prefix
            
            blobs = self.bucket.list_blobs(prefix=blob_prefix)
            
            for blob in blobs:
                # Extract key from object name
                if blob.name.startswith(self.prefix) and blob.name.endswith('.json'):
                    key = blob.name[len(self.prefix):-5]  # Remove prefix and .json
                    yield key
                    
        except Exception as e:
            logger.error(f"Failed to list document keys: {str(e)}")
    
    def get_document_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific document.
        
        Args:
            key: Document key
            
        Returns:
            Document metadata or None if not found
        """
        try:
            object_name = self._get_object_name(key)
            blob = self.bucket.blob(object_name)
            
            if blob.exists():
                blob.reload()
                return {
                    'key': key,
                    'size': blob.size,
                    'created': blob.time_created.isoformat() if blob.time_created else None,
                    'updated': blob.updated.isoformat() if blob.updated else None,
                    'metadata': blob.metadata or {},
                    'content_type': blob.content_type
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {key}: {str(e)}")
            return None
    
    def cleanup_old_documents(self, max_age_days: int = 30) -> int:
        """
        Clean up old documents based on age.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of documents deleted
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
            deleted_count = 0
            
            blobs = self.bucket.list_blobs(prefix=self.prefix)
            
            for blob in blobs:
                if blob.time_created and blob.time_created.replace(tzinfo=None) < cutoff_time:
                    blob.delete()
                    deleted_count += 1
                    logger.debug(f"Deleted old document: {blob.name}")
            
            logger.info(f"Cleaned up {deleted_count} old documents")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old documents: {str(e)}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            total_objects = 0
            total_size = 0
            
            blobs = self.bucket.list_blobs(prefix=self.prefix)
            
            for blob in blobs:
                total_objects += 1
                total_size += blob.size or 0
            
            return {
                'bucket_name': self.bucket_name,
                'prefix': self.prefix,
                'total_objects': total_objects,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {str(e)}")
            return {}

# Create service classes for external integrations
services_code = '''"""
Service classes for external integrations including Confluence, GCP Spanner, and Vertex AI.

This module provides abstracted service interfaces for all external dependencies
used by the compliance verification system.
"""

import logging
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import requests
import google.generativeai as genai
from google.cloud import spanner
from google.cloud.spanner_v1.database import Database
from google.auth import default
from langchain_core.documents import Document
from langchain_google_spanner import SpannerVectorStore
from langchain_google_vertexai import VertexAIEmbeddings

from ..models.data_models import (
    ProcessedDocument, PolicyRule, SimilarEvidenceResult, 
    ValidationStatus, ComplianceRequest
)
from ..core.config import config

logger = logging.getLogger(__name__)


class ConfluenceService:
    """Service for interacting with Confluence API."""
    
    def __init__(self):
        """Initialize Confluence service."""
        self.base_url = config.confluence_base_url
        self.username = config.confluence_username
        self.api_token = config.confluence_api_token
        
        # Setup authentication
        self.auth = (self.username, self.api_token)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"Initialized Confluence service for: {self.base_url}")
    
    def fetch_page_content(self, evidence_url: str) -> str:
        """
        Fetch content from Confluence page with proper authentication.
        
        Args:
            evidence_url: URL of the Confluence page
            
        Returns:
            Raw HTML content of the page
            
        Raises:
            requests.RequestException: If API request fails
            ValueError: If no content found
        """
        try:
            # Parse URL to extract page ID
            page_id = self._extract_page_id(evidence_url)
            
            # Construct API URL
            api_url = f"{self.base_url}/wiki/rest/api/content/{page_id}"
            params = {
                'expand': 'body.storage,metadata.properties,version,ancestors'
            }
            
            logger.info(f"Fetching Confluence page: {page_id}")
            
            response = requests.get(
                api_url, 
                auth=self.auth, 
                headers=self.headers, 
                params=params, 
                timeout=30
            )
            response.raise_for_status()
            
            content_data = response.json()
            html_content = content_data.get('body', {}).get('storage', {}).get('value', '')
            
            if not html_content:
                raise ValueError(f"No content found in Confluence page {page_id}")
            
            # Log metadata for debugging
            title = content_data.get('title', 'Unknown')
            version = content_data.get('version', {}).get('number', 'Unknown')
            logger.info(f"Retrieved page '{title}' (version {version}), content length: {len(html_content)}")
            
            return html_content
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Confluence content from {evidence_url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Confluence content: {str(e)}")
            raise
    
    def _extract_page_id(self, url: str) -> str:
        """Extract page ID from Confluence URL."""
        try:
            # Handle different URL formats
            if '/pages/' in url:
                # Format: .../pages/{pageId}/...
                page_id = url.split('/pages/')[1].split('/')[0]
            elif '/display/' in url:
                # Format: .../display/{spaceKey}/{pageTitle}
                # Need to convert to page ID via API
                parts = url.split('/display/')[1].split('/')
                if len(parts) >= 2:
                    space_key = parts[0]
                    page_title = parts[1].replace('+', ' ')
                    page_id = self._get_page_id_by_title(space_key, page_title)
                else:
                    raise ValueError("Invalid display URL format")
            elif url.isdigit():
                # Direct page ID
                page_id = url
            else:
                raise ValueError(f"Unable to extract page ID from URL: {url}")
            
            return page_id
            
        except Exception as e:
            logger.error(f"Failed to extract page ID from URL {url}: {str(e)}")
            raise
    
    def _get_page_id_by_title(self, space_key: str, title: str) -> str:
        """Get page ID by space key and title."""
        try:
            api_url = f"{self.base_url}/wiki/rest/api/content"
            params = {
                'type': 'page',
                'spaceKey': space_key,
                'title': title,
                'limit': 1
            }
            
            response = requests.get(
                api_url,
                auth=self.auth,
                headers=self.headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                raise ValueError(f"Page not found: {space_key}/{title}")
            
            return results[0]['id']
            
        except Exception as e:
            logger.error(f"Failed to get page ID for {space_key}/{title}: {str(e)}")
            raise


class SpannerVectorService:
    """Service for interacting with GCP Spanner vector store."""
    
    def __init__(self):
        """Initialize Spanner vector service."""
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
        
        # Initialize vector store
        self.vector_store = SpannerVectorStore(
            instance_id=self.instance_id,
            database_id=self.database_id,
            table_name=self.table_name,
            embedding_service=self.embedding_model,
            metadata_columns=[
                'source_url', 'section_header', 'chunk_id', 'extraction_method',
                'content_type', 'validation_status', 'policy_name', 'timestamp',
                'rule_assessments', 'analysis_summary', 'confidence_score'
            ]
        )
        
        logger.info(f"Initialized Spanner vector service: {self.instance_id}/{self.database_id}")
    
    def store_documents(self, documents: List[ProcessedDocument], policy_name: str) -> str:
        """
        Store processed documents in vector store.
        
        Args:
            documents: List of processed documents to store
            policy_name: Policy name for evidence type classification
            
        Returns:
            Primary evidence ID for the stored documents
        """
        try:
            # Convert to LangChain documents and add policy metadata
            langchain_docs = []
            for doc in documents:
                doc.metadata.policy_name = policy_name
                langchain_doc = doc.to_langchain_document()
                langchain_docs.append(langchain_doc)
            
            # Store documents
            doc_ids = self.vector_store.add_documents(langchain_docs)
            
            # Return first ID as primary evidence ID
            evidence_id = doc_ids[0] if doc_ids else None
            
            logger.info(f"Stored {len(documents)} documents in vector store, primary ID: {evidence_id}")
            return evidence_id
            
        except Exception as e:
            logger.error(f"Failed to store documents in vector store: {str(e)}")
            raise
    
    def similarity_search(self, query_documents: List[ProcessedDocument], k: int = 5) -> List[SimilarEvidenceResult]:
        """
        Perform similarity search for historical evidence.
        
        Args:
            query_documents: Documents to search for similar content
            k: Number of similar documents to retrieve
            
        Returns:
            List of similar evidence results
        """
        try:
            # Combine content from query documents
            combined_content = ' '.join([doc.content[:500] for doc in query_documents[:3]])
            
            # Perform similarity search with metadata filtering
            filter_dict = {
                'validation_status': [ValidationStatus.COMPLIANT.value, ValidationStatus.NON_COMPLIANT.value]
            }
            
            similar_docs = self.vector_store.similarity_search_with_score(
                combined_content,
                k=k,
                filter=filter_dict
            )
            
            # Convert to SimilarEvidenceResult objects
            results = []
            for doc, score in similar_docs:
                # Parse rule assessments from metadata
                rule_assessments = []
                if 'rule_assessments' in doc.metadata:
                    try:
                        rule_assessments = json.loads(doc.metadata['rule_assessments'])
                    except (json.JSONDecodeError, TypeError):
                        rule_assessments = []
                
                result = SimilarEvidenceResult(
                    content=doc.page_content,
                    metadata=doc.metadata,
                    similarity_score=float(1 - score),  # Convert distance to similarity
                    validation_status=ValidationStatus(doc.metadata.get('validation_status', 'pending')),
                    rule_assessments=rule_assessments
                )
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} similar evidence documents")
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {str(e)}")
            return []
    
    def update_document_status(self, evidence_id: str, evaluation_result: Dict[str, Any]) -> bool:
        """
        Update document validation status and results.
        
        Args:
            evidence_id: ID of the document to update
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
            
            # Update the document record
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
            
            logger.info(f"Successfully updated document {evidence_id} with status: {validation_status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")
            return False


class SpannerGraphService:
    """Service for interacting with GCP SpannerGraph for policy rules."""
    
    def __init__(self):
        """Initialize SpannerGraph service."""
        self.project_id = config.vertex_ai_project
        self.instance_id = config.spanner_instance_id
        self.database_id = config.spanner_database_id
        self.graph_name = config.spanner_graph_name
        
        # Initialize Spanner client
        self.client = spanner.Client(project=self.project_id)
        self.instance = self.client.instance(self.instance_id)
        self.database = self.instance.database(self.database_id)
        
        logger.info(f"Initialized SpannerGraph service: {self.graph_name}")
    
    def get_policy_rules(self, policy_name: str) -> List[PolicyRule]:
        """
        Retrieve policy validation rules from SpannerGraph.
        
        Args:
            policy_name: Name of the policy to retrieve rules for
            
        Returns:
            List of PolicyRule objects
        """
        try:
            # Construct GQL query for SpannerGraph
            query = f"""
            GRAPH {self.graph_name}
            MATCH (p:Policy {{name: @policy_name}})-[:HAS_RULE]->(r:Rule)
            OPTIONAL MATCH (p)-[:REFERENCES]->(ref_policy:Policy)-[:HAS_RULE]->(ref_rule:Rule)
            RETURN {{
                rule_id: r.rule_id,
                rule_description: r.description,
                rule_type: r.type,
                severity: r.severity,
                validation_criteria: r.validation_criteria,
                policy_name: p.name
            }} as rule
            UNION ALL
            RETURN {{
                rule_id: ref_rule.rule_id,
                rule_description: ref_rule.description,
                rule_type: ref_rule.type,
                severity: ref_rule.severity,
                validation_criteria: ref_rule.validation_criteria,
                policy_name: ref_policy.name
            }} as rule
            """
            
            # Execute query
            with self.database.snapshot() as snapshot:
                results = snapshot.execute_sql(
                    query,
                    params={'policy_name': policy_name},
                    param_types={'policy_name': spanner.param_types.STRING}
                )
                
                rules = []
                for row in results:
                    rule_data = row[0]  # The 'rule' column
                    
                    rule = PolicyRule(
                        rule_id=rule_data.get('rule_id', ''),
                        rule_description=rule_data.get('rule_description', ''),
                        rule_type=rule_data.get('rule_type', 'general'),
                        severity=rule_data.get('severity', 'medium'),
                        validation_criteria=rule_data.get('validation_criteria', ''),
                        policy_name=rule_data.get('policy_name', policy_name)
                    )
                    rules.append(rule)
                
                logger.info(f"Retrieved {len(rules)} rules for policy: {policy_name}")
                return rules
                
        except Exception as e:
            logger.error(f"Failed to retrieve policy rules for {policy_name}: {str(e)}")
            # Return empty list to allow graceful degradation
            return []


class VertexAIService:
    """Service for interacting with Vertex AI for embeddings and LLM inference."""
    
    def __init__(self):
        """Initialize Vertex AI service."""
        self.project_id = config.vertex_ai_project
        self.location = config.vertex_ai_location
        self.embedding_model_name = config.embedding_model_name
        self.llm_model_name = config.llm_model_name
        
        # Configure Vertex AI
        credentials, project = default()
        genai.configure(
            api_key=None,
            transport='vertexai',
            project=project,
            location=self.location
        )
        
        logger.info(f"Initialized Vertex AI service for project: {self.project_id}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text content.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = []
            
            # Process texts individually for text-embedding-005
            for text in texts:
                try:
                    # Use the genai client for embeddings
                    client = genai.Client()
                    result = client.models.embed_content(
                        model=self.embedding_model_name,
                        contents=text[:8000]  # Truncate if too long
                    )
                    
                    if result.embeddings:
                        embeddings.append(result.embeddings[0].values)
                    else:
                        logger.warning(f"No embedding returned for text: {text[:100]}...")
                        embeddings.append([0.0] * config.embedding_dimensions)
                        
                except Exception as e:
                    logger.error(f"Failed to generate embedding for text: {str(e)}")
                    embeddings.append([0.0] * config.embedding_dimensions)
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise
    
    def evaluate_compliance(self, prompt: str) -> Dict[str, Any]:
        """
        Use Gemini 2.5 Pro to evaluate compliance.
        
        Args:
            prompt: Structured prompt for compliance evaluation
            
        Returns:
            Parsed JSON response from LLM
        """
        try:
            # Configure the model with JSON mode
            model = genai.GenerativeModel(
                self.llm_model_name,
                generation_config={
                    'temperature': 0.1,
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 8192,
                    'response_mime_type': 'application/json'
                }
            )
            
            logger.info("Sending compliance evaluation request to Gemini 2.5 Pro")
            
            # Generate response
            response = model.generate_content(prompt)
            
            if not response.text:
                raise ValueError("Empty response from LLM")
            
            # Parse JSON response
            try:
                result = json.loads(response.text)
                logger.info(f"LLM evaluation completed: {result.get('decision', 'unknown')}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response: {response.text}")
                raise ValueError("Invalid JSON response from LLM")
                
        except Exception as e:
            logger.error(f"LLM evaluation failed: {str(e)}")
            raise
'''

with open("agentic_compliance_system/services/__init__.py", "w") as f:
    f.write("# Services module for external integrations")

with open("agentic_compliance_system/services/external_services.py", "w") as f:
    f.write(services_code)

print("✅ Created comprehensive service layer for external integrations")
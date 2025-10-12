"""
spaCy-enhanced text processing utilities for compliance verification.

This module provides advanced text processing capabilities using spaCy for:
- Intelligent tokenization and sentence segmentation
- Named Entity Recognition (NER) for compliance entities
- Advanced query building for similarity search
- Text similarity and semantic analysis
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import re

import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from spacy.tokens import Doc, Token, Span

from ..core.config import config

logger = logging.getLogger(__name__)


@dataclass
class ProcessedText:
    """Container for spaCy-processed text with extracted features."""
    original_text: str
    cleaned_text: str
    tokens: List[str]
    entities: List[Dict[str, Any]]
    key_terms: List[str]
    sentences: List[str]
    compliance_entities: List[Dict[str, Any]]
    similarity_features: List[str]


@dataclass
class ComplianceEntity:
    """Compliance-specific named entity."""
    text: str
    label: str
    start: int
    end: int
    confidence: float
    entity_type: str  # test, policy, requirement, etc.


class SpacyTextProcessor:
    """
    Advanced text processor using spaCy for compliance verification.
    
    Provides intelligent tokenization, NER, and query building capabilities
    optimized for compliance document processing.
    """
    
    def __init__(self):
        """Initialize spaCy text processor with compliance-specific enhancements."""
        try:
            # Load spaCy model
            model_name = config.spacy_model_large if config.use_spacy_large_model else config.spacy_model_name
            self.nlp = spacy.load(model_name)
            
            # Configure processing pipeline
            self._configure_nlp_pipeline()
            
            # Initialize compliance patterns
            self._init_compliance_patterns()
            
            logger.info(f"Initialized spaCy text processor with model: {model_name}")
            
        except IOError as e:
            logger.error(f"Failed to load spaCy model: {str(e)}")
            logger.info("Installing required spaCy model...")
            self._install_spacy_model()
            self.nlp = spacy.load(config.spacy_model_name)
            self._configure_nlp_pipeline()
            self._init_compliance_patterns()
    
    def _install_spacy_model(self):
        """Install required spaCy model if not available."""
        import subprocess
        import sys
        
        try:
            model_name = config.spacy_model_name
            subprocess.check_call([
                sys.executable, "-m", "spacy", "download", model_name
            ])
            logger.info(f"Successfully installed spaCy model: {model_name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install spaCy model: {str(e)}")
            raise
    
    def _configure_nlp_pipeline(self):
        """Configure spaCy processing pipeline for compliance documents."""
        # Set maximum text length
        self.nlp.max_length = config.spacy_max_length
        
        # Add custom compliance component if needed
        if "compliance_ner" not in self.nlp.pipe_names:
            self.nlp.add_pipe("compliance_ner", last=True)
        
        # Configure pipeline components
        if self.nlp.has_pipe("ner") and config.enable_spacy_ner:
            # Keep NER component
            pass
        elif not config.enable_spacy_ner and self.nlp.has_pipe("ner"):
            # Disable NER if not needed
            self.nlp.disable_pipe("ner")
    
    def _init_compliance_patterns(self):
        """Initialize compliance-specific patterns and matchers."""
        from spacy.matcher import Matcher
        
        self.matcher = Matcher(self.nlp.vocab)
        
        # Define compliance-specific patterns
        compliance_patterns = {
            "TEST_EXECUTION": [
                [{"LOWER": "test"}, {"LOWER": {"IN": ["executed", "run", "performed"]}},
                 {"IS_ALPHA": True, "OP": "*"}],
                [{"LOWER": {"IN": ["regression", "performance", "integration"}}], 
                 {"LOWER": "test"}, {"IS_ALPHA": True, "OP": "*"}],
            ],
            "POLICY_COMPLIANCE": [
                [{"LOWER": "policy"}, {"LOWER": {"IN": ["compliant", "compliance", "adherence"]}},
                 {"IS_ALPHA": True, "OP": "*"}],
                [{"LOWER": {"IN": ["meets", "satisfies", "fulfills"}}}, 
                 {"LOWER": {"IN": ["requirement", "criteria", "standard"]}},
                 {"IS_ALPHA": True, "OP": "*"}],
            ],
            "QUALITY_METRICS": [
                [{"LOWER": {"IN": ["pass", "fail"}}}, {"LOWER": "rate"},
                 {"IS_ALPHA": True, "OP": "*"}],
                [{"LIKE_NUM": True}, {"LOWER": {"IN": ["percent", "%", "coverage"]}},
                 {"IS_ALPHA": True, "OP": "*"}],
            ],
            "APPROVAL_SIGNOFF": [
                [{"LOWER": {"IN": ["approved", "signed", "reviewed"}}}, {"LOWER": "by"},
                 {"IS_ALPHA": True, "OP": "+"}],
                [{"LOWER": {"IN": ["qa", "lead", "manager"]}}, {"LOWER": "approval"},
                 {"IS_ALPHA": True, "OP": "*"}],
            ]
        }
        
        # Add patterns to matcher
        for pattern_name, patterns in compliance_patterns.items():
            self.matcher.add(pattern_name, patterns)
        
        logger.info(f"Initialized {len(compliance_patterns)} compliance patterns")
    
    @spacy.Language.component("compliance_ner")
    def compliance_ner_component(self, doc: Doc) -> Doc:
        """Custom spaCy component for compliance-specific NER."""
        # Find compliance patterns
        matches = self.matcher(doc)
        
        # Create compliance entities
        compliance_ents = []
        for match_id, start, end in matches:
            span = doc[start:end]
            label = self.nlp.vocab.strings[match_id]
            
            # Create new entity
            compliance_ents.append(Span(doc, start, end, label=label))
        
        # Add to existing entities
        doc.ents = list(doc.ents) + compliance_ents
        return doc
    
    def process_text(self, text: str) -> ProcessedText:
        """
        Process text using spaCy with compliance-specific enhancements.
        
        Args:
            text: Raw text to process
            
        Returns:
            ProcessedText object with extracted features
        """
        try:
            # Clean text
            cleaned_text = self._clean_text(text)
            
            # Process with spaCy
            doc = self.nlp(cleaned_text)
            
            # Extract features
            tokens = self._extract_tokens(doc)
            entities = self._extract_entities(doc)
            key_terms = self._extract_key_terms(doc)
            sentences = self._extract_sentences(doc)
            compliance_entities = self._extract_compliance_entities(doc)
            similarity_features = self._extract_similarity_features(doc)
            
            return ProcessedText(
                original_text=text,
                cleaned_text=cleaned_text,
                tokens=tokens,
                entities=entities,
                key_terms=key_terms,
                sentences=sentences,
                compliance_entities=compliance_entities,
                similarity_features=similarity_features
            )
            
        except Exception as e:
            logger.error(f"Failed to process text with spaCy: {str(e)}")
            # Return basic processed text
            return ProcessedText(
                original_text=text,
                cleaned_text=text,
                tokens=text.split(),
                entities=[],
                key_terms=[],
                sentences=[text],
                compliance_entities=[],
                similarity_features=[]
            )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for processing."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s\.,!?;:()-]', ' ', text)
        
        # Normalize case for better processing
        # Keep original case but clean structure
        text = text.strip()
        
        return text
    
    def _extract_tokens(self, doc: Doc) -> List[str]:
        """Extract meaningful tokens from spaCy doc."""
        tokens = []
        
        for token in doc:
            # Skip stop words, punctuation, and whitespace
            if (not token.is_stop and 
                not token.is_punct and 
                not token.is_space and
                len(token.text) > config.min_term_length):
                
                # Use lemmatized form for better matching
                tokens.append(token.lemma_.lower())
        
        return tokens
    
    def _extract_entities(self, doc: Doc) -> List[Dict[str, Any]]:
        """Extract named entities with confidence scores."""
        entities = []
        
        for ent in doc.ents:
            entity_info = {
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'description': spacy.explain(ent.label_) or ent.label_
            }
            entities.append(entity_info)
        
        return entities
    
    def _extract_key_terms(self, doc: Doc) -> List[str]:
        """Extract key terms using advanced spaCy features."""
        # Collect candidate terms
        candidates = {}
        
        # Process tokens with POS and dependency information
        for token in doc:
            if self._is_key_term_candidate(token):
                lemma = token.lemma_.lower()
                
                # Calculate term importance score
                score = self._calculate_term_importance(token)
                
                if lemma in candidates:
                    candidates[lemma] = max(candidates[lemma], score)
                else:
                    candidates[lemma] = score
        
        # Process noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Max 3-word phrases
                phrase = ' '.join([t.lemma_.lower() for t in chunk if not t.is_stop])
                if phrase and len(phrase) > 3:
                    candidates[phrase] = candidates.get(phrase, 0) + 1.5
        
        # Sort by importance and return top terms
        sorted_terms = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        return [term for term, score in sorted_terms[:config.max_query_terms]]
    
    def _is_key_term_candidate(self, token: Token) -> bool:
        """Check if token is a good candidate for key term extraction."""
        return (
            not token.is_stop and
            not token.is_punct and
            not token.is_space and
            not token.like_url and
            not token.like_email and
            len(token.text) >= config.min_term_length and
            token.pos_ in ['NOUN', 'PROPN', 'ADJ', 'VERB'] and
            token.is_alpha
        )
    
    def _calculate_term_importance(self, token: Token) -> float:
        """Calculate importance score for a term."""
        score = 1.0
        
        # POS-based scoring
        if token.pos_ == 'NOUN':
            score += 1.0
        elif token.pos_ == 'PROPN':
            score += 1.5
        elif token.pos_ == 'ADJ':
            score += 0.5
        elif token.pos_ == 'VERB':
            score += 0.8
        
        # Dependency-based scoring
        if token.dep_ in ['ROOT', 'nsubj', 'dobj']:
            score += 1.0
        elif token.dep_ in ['compound', 'amod']:
            score += 0.5
        
        # Length-based scoring
        if len(token.text) > 6:
            score += 0.3
        
        # Frequency-based scoring (inverse frequency within doc)
        doc_freq = len([t for t in token.doc if t.lemma_ == token.lemma_])
        if doc_freq == 1:
            score += 0.5  # Unique terms are more important
        elif doc_freq > 5:
            score -= 0.3  # Very frequent terms are less important
        
        return score
    
    def _extract_sentences(self, doc: Doc) -> List[str]:
        """Extract sentences with compliance relevance scoring."""
        sentences = []
        
        for sent in doc.sents:
            sentence_text = sent.text.strip()
            if len(sentence_text) > 20:  # Skip very short sentences
                sentences.append(sentence_text)
        
        return sentences
    
    def _extract_compliance_entities(self, doc: Doc) -> List[Dict[str, Any]]:
        """Extract compliance-specific entities."""
        compliance_entities = []
        
        # Process compliance patterns found by matcher
        matches = self.matcher(doc)
        
        for match_id, start, end in matches:
            span = doc[start:end]
            pattern_name = self.nlp.vocab.strings[match_id]
            
            entity = {
                'text': span.text,
                'label': pattern_name,
                'start': span.start_char,
                'end': span.end_char,
                'entity_type': self._get_entity_type(pattern_name),
                'confidence': 0.8  # Pattern-based entities have high confidence
            }
            compliance_entities.append(entity)
        
        return compliance_entities
    
    def _get_entity_type(self, pattern_name: str) -> str:
        """Map pattern name to entity type."""
        entity_type_map = {
            'TEST_EXECUTION': 'test_activity',
            'POLICY_COMPLIANCE': 'compliance_statement',
            'QUALITY_METRICS': 'quality_measure',
            'APPROVAL_SIGNOFF': 'approval_process'
        }
        return entity_type_map.get(pattern_name, 'general')
    
    def _extract_similarity_features(self, doc: Doc) -> List[str]:
        """Extract features optimized for similarity search."""
        features = []
        
        # Add important entities
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'EVENT', 'DATE']:
                features.append(ent.text.lower())
        
        # Add compliance entities
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            features.append(span.text.lower())
        
        # Add key noun phrases
        for chunk in doc.noun_chunks:
            if 2 <= len(chunk.text.split()) <= 3:
                features.append(chunk.text.lower())
        
        return list(set(features))  # Remove duplicates
    
    def build_similarity_query(self, processed_texts: List[ProcessedText], max_query_length: int = 800) -> str:
        """
        Build optimized similarity search query from processed texts.
        
        Args:
            processed_texts: List of ProcessedText objects
            max_query_length: Maximum query length
            
        Returns:
            Optimized query string for similarity search
        """
        try:
            # Collect all key terms and features
            all_key_terms = []
            all_entities = []
            all_compliance_entities = []
            
            for pt in processed_texts:
                all_key_terms.extend(pt.key_terms)
                all_entities.extend([e['text'].lower() for e in pt.entities])
                all_compliance_entities.extend([e['text'].lower() for e in pt.compliance_entities])
            
            # Calculate term frequencies and importance
            term_freq = {}
            for term in all_key_terms:
                term_freq[term] = term_freq.get(term, 0) + 1
            
            # Weight terms by type and frequency
            weighted_terms = []
            
            # Compliance entities get highest weight
            for term in set(all_compliance_entities):
                weighted_terms.append((term, 3.0))
            
            # Named entities get medium weight
            for term in set(all_entities):
                if term not in all_compliance_entities:
                    weighted_terms.append((term, 2.0))
            
            # Key terms get base weight with frequency adjustment
            for term, freq in term_freq.items():
                if term not in all_entities and term not in all_compliance_entities:
                    weight = 1.0 + min(freq * 0.1, 0.5)  # Slight boost for frequent terms
                    weighted_terms.append((term, weight))
            
            # Sort by weight and build query
            weighted_terms.sort(key=lambda x: x[1], reverse=True)
            
            query_parts = []
            current_length = 0
            
            for term, weight in weighted_terms:
                if current_length + len(term) + 1 <= max_query_length:
                    query_parts.append(term)
                    current_length += len(term) + 1
                else:
                    break
            
            # Build final query with structure
            query = ' '.join(query_parts[:20])  # Limit to top 20 terms
            
            logger.info(f"Built similarity query with {len(query_parts)} terms, {len(query)} characters")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build similarity query: {str(e)}")
            # Fallback to simple concatenation
            simple_query = ' '.join([pt.cleaned_text[:200] for pt in processed_texts[:3]])
            return simple_query[:max_query_length]
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts using spaCy.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            if not config.enable_spacy_similarity:
                return 0.0
            
            # Process both texts
            doc1 = self.nlp(text1[:1000])  # Limit length for performance
            doc2 = self.nlp(text2[:1000])
            
            # Calculate similarity using spaCy's built-in similarity
            similarity = doc1.similarity(doc2)
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"Failed to calculate text similarity: {str(e)}")
            return 0.0
    
    def extract_compliance_keywords(self, text: str) -> Dict[str, List[str]]:
        """
        Extract compliance-specific keywords organized by category.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of keyword categories and their terms
        """
        try:
            processed = self.process_text(text)
            
            keywords = {
                'test_activities': [],
                'quality_metrics': [],
                'compliance_statements': [],
                'approval_processes': [],
                'entities': [],
                'key_terms': processed.key_terms[:10]  # Top 10 key terms
            }
            
            # Categorize compliance entities
            for entity in processed.compliance_entities:
                entity_type = entity.get('entity_type', 'general')
                if entity_type == 'test_activity':
                    keywords['test_activities'].append(entity['text'])
                elif entity_type == 'quality_measure':
                    keywords['quality_metrics'].append(entity['text'])
                elif entity_type == 'compliance_statement':
                    keywords['compliance_statements'].append(entity['text'])
                elif entity_type == 'approval_process':
                    keywords['approval_processes'].append(entity['text'])
            
            # Add important named entities
            for entity in processed.entities:
                if entity['label'] in ['ORG', 'PERSON', 'PRODUCT', 'EVENT']:
                    keywords['entities'].append(entity['text'])
            
            return keywords
            
        except Exception as e:
            logger.error(f"Failed to extract compliance keywords: {str(e)}")
            return {'key_terms': [], 'entities': [], 'test_activities': [], 
                   'quality_metrics': [], 'compliance_statements': [], 'approval_processes': []}
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and configuration."""
        return {
            'processor_name': 'SpacyTextProcessor',
            'model_name': self.nlp.meta.get('name', 'unknown'),
            'model_version': self.nlp.meta.get('version', 'unknown'),
            'pipeline_components': list(self.nlp.pipe_names),
            'max_length': self.nlp.max_length,
            'patterns_count': len(self.matcher),
            'config': {
                'enable_ner': config.enable_spacy_ner,
                'enable_similarity': config.enable_spacy_similarity,
                'max_query_terms': config.max_query_terms,
                'min_term_length': config.min_term_length
            }
        }


# Global text processor instance
text_processor = SpacyTextProcessor()

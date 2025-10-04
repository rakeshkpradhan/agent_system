# Create content parsing utilities with multiple strategies
content_parser_code = '''"""
Content parsing utilities for extracting and structuring text from HTML documents.

This module provides multiple parsing strategies to handle various types of content
including BeautifulSoup, Trafilatura, and custom parsing for Confluence-specific content.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag
import trafilatura
from urllib.parse import urlparse, urljoin

from ..models.data_models import ProcessedDocument, EvidenceMetadata

logger = logging.getLogger(__name__)


@dataclass
class ParsingStrategy:
    """Configuration for content parsing strategy."""
    name: str
    use_trafilatura: bool = True
    use_beautifulsoup: bool = True
    extract_tables: bool = True
    extract_lists: bool = True
    extract_images: bool = False
    min_chunk_size: int = 50
    max_chunk_size: int = 2000
    chunk_overlap: int = 200


class ContentParser:
    """Multi-strategy content parser for HTML documents."""
    
    def __init__(self, strategy: Optional[ParsingStrategy] = None):
        """Initialize content parser with strategy."""
        self.strategy = strategy or ParsingStrategy(name="default")
        logger.info(f"Initialized ContentParser with strategy: {self.strategy.name}")
    
    def parse_html_content(self, html_content: str, source_url: str) -> List[ProcessedDocument]:
        """
        Parse HTML content using multiple strategies and return processed documents.
        
        Args:
            html_content: Raw HTML content to parse
            source_url: Source URL of the content
            
        Returns:
            List of ProcessedDocument objects
        """
        try:
            documents = []
            
            # Strategy 1: Trafilatura for clean text extraction
            if self.strategy.use_trafilatura:
                trafilatura_docs = self._parse_with_trafilatura(html_content, source_url)
                documents.extend(trafilatura_docs)
                logger.info(f"Trafilatura extracted {len(trafilatura_docs)} documents")
            
            # Strategy 2: BeautifulSoup for structured content
            if self.strategy.use_beautifulsoup:
                bs_docs = self._parse_with_beautifulsoup(html_content, source_url)
                documents.extend(bs_docs)
                logger.info(f"BeautifulSoup extracted {len(bs_docs)} documents")
            
            # Strategy 3: Confluence-specific parsing
            confluence_docs = self._parse_confluence_specific(html_content, source_url)
            documents.extend(confluence_docs)
            logger.info(f"Confluence-specific parsing extracted {len(confluence_docs)} documents")
            
            # Remove duplicates and filter by size
            documents = self._deduplicate_and_filter(documents)
            
            logger.info(f"Total documents after processing: {len(documents)}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to parse HTML content: {str(e)}")
            raise
    
    def _parse_with_trafilatura(self, html_content: str, source_url: str) -> List[ProcessedDocument]:
        """Parse content using Trafilatura library."""
        documents = []
        
        try:
            # Extract clean text
            clean_text = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=self.strategy.extract_tables,
                include_links=True,
                output_format='txt'
            )
            
            if clean_text:
                # Split into chunks by paragraphs and sections
                chunks = self._split_text_into_chunks(clean_text)
                
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) >= self.strategy.min_chunk_size:
                        metadata = EvidenceMetadata(
                            source_url=source_url,
                            chunk_id=f"trafilatura_chunk_{i}",
                            extraction_method="trafilatura",
                            content_type="text"
                        )
                        
                        document = ProcessedDocument(
                            content=chunk.strip(),
                            metadata=metadata
                        )
                        documents.append(document)
            
        except Exception as e:
            logger.warning(f"Trafilatura parsing failed: {str(e)}")
        
        return documents
    
    def _parse_with_beautifulsoup(self, html_content: str, source_url: str) -> List[ProcessedDocument]:
        """Parse content using BeautifulSoup for structured extraction."""
        documents = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            self._clean_soup(soup)
            
            # Extract section-based content
            documents.extend(self._extract_sections(soup, source_url))
            
            # Extract tables if enabled
            if self.strategy.extract_tables:
                documents.extend(self._extract_tables(soup, source_url))
            
            # Extract lists if enabled  
            if self.strategy.extract_lists:
                documents.extend(self._extract_lists(soup, source_url))
            
        except Exception as e:
            logger.warning(f"BeautifulSoup parsing failed: {str(e)}")
        
        return documents
    
    def _parse_confluence_specific(self, html_content: str, source_url: str) -> List[ProcessedDocument]:
        """Parse Confluence-specific content structures."""
        documents = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract Confluence macros
            documents.extend(self._extract_confluence_macros(soup, source_url))
            
            # Extract Confluence page properties
            documents.extend(self._extract_confluence_properties(soup, source_url))
            
            # Extract Confluence panels and callouts
            documents.extend(self._extract_confluence_panels(soup, source_url))
            
        except Exception as e:
            logger.warning(f"Confluence-specific parsing failed: {str(e)}")
        
        return documents
    
    def _clean_soup(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from BeautifulSoup object."""
        # Remove navigation, sidebars, and boilerplate
        unwanted_selectors = [
            'nav', 'aside', 'footer', 'header',
            '.nav', '.sidebar', '.footer', '.header',
            '.navigation', '.breadcrumb', '.pagination',
            'script', 'style', 'meta', 'link'
        ]
        
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()
    
    def _extract_sections(self, soup: BeautifulSoup, source_url: str) -> List[ProcessedDocument]:
        """Extract content organized by sections (headers)."""
        documents = []
        
        # Find all headers
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for i, header in enumerate(headers):
            section_content = []
            section_content.append(header.get_text().strip())
            
            # Get content until next header or end
            current_element = header.find_next_sibling()
            
            while current_element:
                if current_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    break
                
                if current_element.get_text().strip():
                    section_content.append(current_element.get_text().strip())
                
                current_element = current_element.find_next_sibling()
            
            if len(section_content) > 1:
                content = '\\n'.join(section_content)
                
                if len(content) >= self.strategy.min_chunk_size:
                    metadata = EvidenceMetadata(
                        source_url=source_url,
                        section_header=header.get_text().strip(),
                        chunk_id=f"section_{i}",
                        extraction_method="beautifulsoup_sections",
                        content_type="section"
                    )
                    
                    document = ProcessedDocument(
                        content=content,
                        metadata=metadata
                    )
                    documents.append(document)
        
        return documents
    
    def _extract_tables(self, soup: BeautifulSoup, source_url: str) -> List[ProcessedDocument]:
        """Extract and structure table content."""
        documents = []
        
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            table_text = self._table_to_text(table)
            
            if table_text and len(table_text) >= self.strategy.min_chunk_size:
                metadata = EvidenceMetadata(
                    source_url=source_url,
                    chunk_id=f"table_{i}",
                    extraction_method="beautifulsoup_table",
                    content_type="table"
                )
                
                document = ProcessedDocument(
                    content=table_text,
                    metadata=metadata
                )
                documents.append(document)
        
        return documents
    
    def _extract_lists(self, soup: BeautifulSoup, source_url: str) -> List[ProcessedDocument]:
        """Extract structured list content."""
        documents = []
        
        lists = soup.find_all(['ul', 'ol'])
        for i, list_element in enumerate(lists):
            list_text = self._list_to_text(list_element)
            
            if list_text and len(list_text) >= self.strategy.min_chunk_size:
                metadata = EvidenceMetadata(
                    source_url=source_url,
                    chunk_id=f"list_{i}",
                    extraction_method="beautifulsoup_list",
                    content_type="list"
                )
                
                document = ProcessedDocument(
                    content=list_text,
                    metadata=metadata
                )
                documents.append(document)
        
        return documents
    
    def _extract_confluence_macros(self, soup: BeautifulSoup, source_url: str) -> List[ProcessedDocument]:
        """Extract content from Confluence macros."""
        documents = []
        
        # Find Confluence structured macros
        macros = soup.find_all('ac:structured-macro')
        
        for i, macro in enumerate(macros):
            macro_name = macro.get('ac:name', 'unknown')
            
            # Extract macro content
            content_parts = []
            
            # Get macro body
            body = macro.find('ac:rich-text-body') or macro.find('ac:plain-text-body')
            if body:
                content_parts.append(f"Macro: {macro_name}")
                content_parts.append(body.get_text().strip())
            
            # Get macro parameters
            params = macro.find_all('ac:parameter')
            for param in params:
                param_name = param.get('ac:name', 'param')
                param_value = param.get_text().strip()
                if param_value:
                    content_parts.append(f"{param_name}: {param_value}")
            
            if content_parts:
                content = '\\n'.join(content_parts)
                
                if len(content) >= self.strategy.min_chunk_size:
                    metadata = EvidenceMetadata(
                        source_url=source_url,
                        chunk_id=f"macro_{i}_{macro_name}",
                        extraction_method="confluence_macro",
                        content_type="macro"
                    )
                    
                    document = ProcessedDocument(
                        content=content,
                        metadata=metadata
                    )
                    documents.append(document)
        
        return documents
    
    def _extract_confluence_properties(self, soup: BeautifulSoup, source_url: str) -> List[ProcessedDocument]:
        """Extract Confluence page properties."""
        documents = []
        
        # Find property tables or panels
        property_elements = soup.find_all(['table', 'div'], 
                                        class_=lambda x: x and 'property' in x.lower())
        
        for i, element in enumerate(property_elements):
            content = element.get_text().strip()
            
            if content and len(content) >= self.strategy.min_chunk_size:
                metadata = EvidenceMetadata(
                    source_url=source_url,
                    chunk_id=f"properties_{i}",
                    extraction_method="confluence_properties",
                    content_type="properties"
                )
                
                document = ProcessedDocument(
                    content=content,
                    metadata=metadata
                )
                documents.append(document)
        
        return documents
    
    def _extract_confluence_panels(self, soup: BeautifulSoup, source_url: str) -> List[ProcessedDocument]:
        """Extract content from Confluence panels and callouts."""
        documents = []
        
        # Find panels (info, warning, note, etc.)
        panel_selectors = [
            '.aui-message', '.confluence-information-macro',
            '.panel', '.panelContent', '.info-macro', '.warning-macro'
        ]
        
        for selector in panel_selectors:
            panels = soup.select(selector)
            
            for i, panel in enumerate(panels):
                content = panel.get_text().strip()
                
                if content and len(content) >= self.strategy.min_chunk_size:
                    metadata = EvidenceMetadata(
                        source_url=source_url,
                        chunk_id=f"panel_{selector.replace('.', '')}_{i}",
                        extraction_method="confluence_panel",
                        content_type="panel"
                    )
                    
                    document = ProcessedDocument(
                        content=content,
                        metadata=metadata
                    )
                    documents.append(document)
        
        return documents
    
    def _table_to_text(self, table: Tag) -> str:
        """Convert HTML table to structured text."""
        rows = []
        
        for row in table.find_all('tr'):
            cells = []
            for cell in row.find_all(['td', 'th']):
                cell_text = cell.get_text().strip()
                cells.append(cell_text)
            
            if cells:
                rows.append(' | '.join(cells))
        
        return '\\n'.join(rows)
    
    def _list_to_text(self, list_element: Tag) -> str:
        """Convert HTML list to structured text."""
        items = []
        
        for item in list_element.find_all('li'):
            item_text = item.get_text().strip()
            if item_text:
                items.append(f"• {item_text}")
        
        return '\\n'.join(items)
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split('\\n\\n') if p.strip()]
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max size, save current chunk
            if len(current_chunk) + len(paragraph) > self.strategy.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    
                    # Start new chunk with overlap
                    words = current_chunk.split()
                    if len(words) > 20:
                        overlap_words = words[-20:]  # Last 20 words for overlap
                        current_chunk = ' '.join(overlap_words) + '\\n\\n' + paragraph
                    else:
                        current_chunk = paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += '\\n\\n' + paragraph
                else:
                    current_chunk = paragraph
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _deduplicate_and_filter(self, documents: List[ProcessedDocument]) -> List[ProcessedDocument]:
        """Remove duplicate documents and filter by quality."""
        seen_content = set()
        filtered_docs = []
        
        for doc in documents:
            # Create a normalized version for deduplication
            normalized_content = ' '.join(doc.content.split()).lower()
            
            # Skip if too short or duplicate
            if (len(doc.content) < self.strategy.min_chunk_size or 
                normalized_content in seen_content):
                continue
            
            seen_content.add(normalized_content)
            filtered_docs.append(doc)
        
        return filtered_docs


def create_parsing_strategies() -> Dict[str, ParsingStrategy]:
    """Create predefined parsing strategies for different content types."""
    return {
        'comprehensive': ParsingStrategy(
            name="comprehensive",
            use_trafilatura=True,
            use_beautifulsoup=True,
            extract_tables=True,
            extract_lists=True,
            extract_images=False,
            min_chunk_size=100,
            max_chunk_size=2000,
            chunk_overlap=200
        ),
        'text_focused': ParsingStrategy(
            name="text_focused",
            use_trafilatura=True,
            use_beautifulsoup=False,
            extract_tables=False,
            extract_lists=False,
            extract_images=False,
            min_chunk_size=200,
            max_chunk_size=1500,
            chunk_overlap=150
        ),
        'structured_focused': ParsingStrategy(
            name="structured_focused",
            use_trafilatura=False,
            use_beautifulsoup=True,
            extract_tables=True,
            extract_lists=True,
            extract_images=False,
            min_chunk_size=50,
            max_chunk_size=2500,
            chunk_overlap=250
        ),
        'confluence_optimized': ParsingStrategy(
            name="confluence_optimized",
            use_trafilatura=True,
            use_beautifulsoup=True,
            extract_tables=True,
            extract_lists=True,
            extract_images=False,
            min_chunk_size=75,
            max_chunk_size=1800,
            chunk_overlap=180
        )
    }
'''

with open("agentic_compliance_system/utils/content_parser.py", "w") as f:
    f.write(content_parser_code)

print("✅ Created comprehensive content parsing utilities")
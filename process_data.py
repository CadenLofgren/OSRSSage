"""
Data Processing Pipeline
Processes scraped wiki data and creates intelligent chunks for vector storage.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import yaml
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes and chunks wiki data intelligently."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize processor with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.chunk_size = self.config['processing']['chunk_size']
        self.chunk_overlap = self.config['processing']['chunk_overlap']
        self.min_chunk_size = self.config['processing']['min_chunk_size']
        self.preserve_tables = self.config['processing']['preserve_tables']
        self.preserve_lists = self.config['processing']['preserve_lists']
        
        self.raw_data_dir = Path(self.config['wiki']['output_dir'])
        self.processed_data_dir = Path("data/processed")
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_scraped_data(self) -> List[Dict]:
        """Load all scraped wiki data."""
        pages_data = []
        
        # Try to load consolidated file first
        all_pages_file = self.raw_data_dir / "all_pages.json"
        if all_pages_file.exists():
            logger.info(f"Loading consolidated data from {all_pages_file}")
            with open(all_pages_file, 'r', encoding='utf-8') as f:
                pages_data = json.load(f)
        else:
            # Load individual JSON files
            logger.info(f"Loading individual page files from {self.raw_data_dir}")
            json_files = list(self.raw_data_dir.glob("*.json"))
            
            for json_file in tqdm(json_files, desc="Loading pages"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        page_data = json.load(f)
                        if isinstance(page_data, dict) and 'title' in page_data:
                            pages_data.append(page_data)
                except Exception as e:
                    logger.warning(f"Error loading {json_file}: {e}")
        
        logger.info(f"Loaded {len(pages_data)} pages")
        return pages_data
    
    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        """Chunk text intelligently, preserving context."""
        chunks = []
        
        if not text or len(text.strip()) < self.min_chunk_size:
            return chunks
        
        # Split by paragraphs first to maintain coherence
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # If paragraph itself is too large, split it
            if para_length > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append({
                            'text': chunk_text,
                            'metadata': metadata.copy()
                        })
                    current_chunk = []
                    current_length = 0
                
                # Split large paragraph by sentences
                sentences = para.split('. ')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    if current_length + len(sentence) > self.chunk_size:
                        if current_chunk:
                            chunk_text = '\n\n'.join(current_chunk)
                            if len(chunk_text) >= self.min_chunk_size:
                                chunks.append({
                                    'text': chunk_text,
                                    'metadata': metadata.copy()
                                })
                        current_chunk = [sentence]
                        current_length = len(sentence)
                    else:
                        current_chunk.append(sentence)
                        current_length += len(sentence) + 2  # +2 for '\n\n'
            else:
                # Check if adding this paragraph would exceed chunk size
                if current_length + para_length > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append({
                            'text': chunk_text,
                            'metadata': metadata.copy()
                        })
                    
                    # Start new chunk with overlap
                    if self.chunk_overlap > 0 and current_chunk:
                        # Take last few sentences for overlap
                        overlap_text = '\n\n'.join(current_chunk[-2:]) if len(current_chunk) >= 2 else current_chunk[-1]
                        overlap_text = overlap_text[-self.chunk_overlap:]
                        current_chunk = [overlap_text, para] if overlap_text else [para]
                        current_length = len(overlap_text) + para_length + 2
                    else:
                        current_chunk = [para]
                        current_length = para_length
                else:
                    current_chunk.append(para)
                    current_length += para_length + 2
        
        # Save last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    'text': chunk_text,
                    'metadata': metadata.copy()
                })
        
        return chunks
    
    def process_page(self, page_data: Dict) -> List[Dict]:
        """Process a single page into chunks."""
        chunks = []
        title = page_data.get('title', 'Unknown')
        url = page_data.get('url', '')
        
        # Create base metadata
        base_metadata = {
            'page_title': title,
            'url': url,
            'page_id': page_data.get('page_id', '')
        }
        
        # Process infobox separately (keep as single chunk)
        if page_data.get('infobox'):
            infobox_text = f"Stats/Info for {title}:\n{json.dumps(page_data['infobox'], indent=2)}"
            chunks.append({
                'text': infobox_text,
                'metadata': {
                    **base_metadata,
                    'section': 'Infobox',
                    'type': 'structured_data'
                }
            })
        
        # Process sections intelligently
        sections = page_data.get('sections', {})
        for section_name, section_text in sections.items():
            section_metadata = {
                **base_metadata,
                'section': section_name,
                'type': 'section'
            }
            
            section_chunks = self.chunk_text(section_text, section_metadata)
            chunks.extend(section_chunks)
        
        # Process tables if preserve_tables is True
        if self.preserve_tables and page_data.get('tables'):
            for table in page_data['tables']:
                table_text = f"Table: {table['section']}\n{json.dumps(table['data'], indent=2)}"
                chunks.append({
                    'text': table_text,
                    'metadata': {
                        **base_metadata,
                        'section': table['section'],
                        'type': 'table'
                    }
                })
        
        # Process lists if preserve_lists is True
        if self.preserve_lists and page_data.get('lists'):
            for lst in page_data['lists']:
                list_text = f"List: {lst['section']}\n" + '\n'.join([f"- {item}" for item in lst['items']])
                chunks.append({
                    'text': list_text,
                    'metadata': {
                        **base_metadata,
                        'section': lst['section'],
                        'type': 'list'
                    }
                })
        
        # If no structured data, process main text
        if not chunks and page_data.get('text'):
            main_chunks = self.chunk_text(page_data['text'], {
                **base_metadata,
                'section': 'Main',
                'type': 'text'
            })
            chunks.extend(main_chunks)
        
        # Add chunk index to metadata
        for i, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = i
            chunk['metadata']['total_chunks'] = len(chunks)
        
        return chunks
    
    def process_all(self) -> List[Dict]:
        """Process all scraped pages."""
        logger.info("Starting data processing...")
        
        pages_data = self.load_scraped_data()
        all_chunks = []
        
        for page_data in tqdm(pages_data, desc="Processing pages"):
            try:
                chunks = self.process_page(page_data)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Error processing page {page_data.get('title', 'Unknown')}: {e}")
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(pages_data)} pages")
        
        # Save processed chunks
        output_file = self.processed_data_dir / "processed_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved processed chunks to {output_file}")
        
        return all_chunks


if __name__ == "__main__":
    processor = DataProcessor()
    processor.process_all()

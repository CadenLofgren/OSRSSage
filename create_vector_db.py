"""
Vector Database Creation
Creates embeddings and stores them in Chroma vector database.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
import yaml

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorDBBuilder:
    """Builds vector database from processed chunks."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize vector DB builder with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.embedding_model_name = self.config['vector_db']['embedding_model']
        self.persist_directory = self.config['vector_db']['persist_directory']
        self.collection_name = self.config['vector_db']['collection_name']
        self.batch_size = self.config['vector_db']['batch_size']
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        logger.info("Embedding model loaded successfully")
        
        # Initialize Chroma client
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
    
    def load_processed_chunks(self) -> List[Dict]:
        """Load processed chunks from JSON file."""
        processed_data_dir = Path("data/processed")
        chunks_file = processed_data_dir / "processed_chunks.json"
        
        if not chunks_file.exists():
            raise FileNotFoundError(
                f"Processed chunks file not found: {chunks_file}\n"
                "Please run process_data.py first."
            )
        
        logger.info(f"Loading processed chunks from {chunks_file}")
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        logger.info(f"Loaded {len(chunks)} chunks")
        return chunks
    
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts."""
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        return embeddings.tolist()
    
    def build_vector_db(self, clear_existing: bool = False):
        """Build vector database from processed chunks."""
        if clear_existing:
            try:
                self.client.delete_collection(name=self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("Cleared existing collection")
            except:
                pass
        
        # Load chunks
        chunks = self.load_processed_chunks()
        
        # Check if collection already has data
        existing_count = self.collection.count()
        if existing_count > 0 and not clear_existing:
            logger.info(f"Collection already has {existing_count} documents. Skipping.")
            response = input("Clear existing data and rebuild? (y/n): ")
            if response.lower() == 'y':
                self.build_vector_db(clear_existing=True)
                return
            else:
                logger.info("Keeping existing data. Add new chunks if needed.")
                return
        
        # Process in batches
        logger.info("Creating embeddings and storing in vector database...")
        
        texts = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(tqdm(chunks, desc="Processing chunks")):
            texts.append(chunk['text'])
            metadatas.append(chunk['metadata'])
            ids.append(f"chunk_{i}")
            
            # Process batch when full
            if len(texts) >= self.batch_size:
                embeddings = self.create_embeddings_batch(texts)
                
                self.collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
                
                texts = []
                metadatas = []
                ids = []
        
        # Process remaining chunks
        if texts:
            embeddings = self.create_embeddings_batch(texts)
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        
        logger.info(f"Vector database built successfully! Total documents: {self.collection.count()}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build vector database from processed chunks")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before building"
    )
    
    args = parser.parse_args()
    
    builder = VectorDBBuilder()
    builder.build_vector_db(clear_existing=args.clear)

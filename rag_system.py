"""
RAG System Core
Retrieval-Augmented Generation system for OSRS wiki queries.
"""

import logging
from typing import List, Dict, Optional
import yaml

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import ollama

from security import SecurityManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGSystem:
    """RAG system for querying OSRS wiki."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize RAG system with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load embedding model
        self.embedding_model_name = self.config['vector_db']['embedding_model']
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        # Initialize Chroma client
        persist_directory = self.config['vector_db']['persist_directory']
        collection_name = self.config['vector_db']['collection_name']
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_collection(name=collection_name)
        logger.info(f"Loaded collection with {self.collection.count()} documents")
        
        # RAG settings
        self.top_k = self.config['rag']['top_k']
        self.similarity_threshold = self.config['rag']['similarity_threshold']
        self.max_context_length = self.config['rag']['max_context_length']
        
        # LLM settings
        self.llm_model = self.config['llm']['model']
        self.llm_base_url = self.config['llm']['base_url']
        self.temperature = self.config['llm']['temperature']
        self.max_tokens = self.config['llm']['max_tokens']
        self.max_response_tokens = self.config['llm'].get('max_response_tokens', 1000)
        self.system_prompt = self.config['llm']['system_prompt']
        
        # Initialize Ollama client
        self.ollama_client = ollama.Client(host=self.llm_base_url)
        
        # Initialize security manager
        security_config = self.config.get('security', {})
        rate_limit = security_config.get('rate_limit_interval', 2.0)
        log_file = security_config.get('query_log_file', 'logs/query_log.jsonl')
        self.security_manager = SecurityManager(
            rate_limit_interval=rate_limit,
            log_file=log_file
        )
        self.enable_security = security_config.get('enable_input_validation', True)
        self.enable_rate_limiting = security_config.get('enable_rate_limiting', True)
        self.enable_logging = security_config.get('enable_query_logging', True)
        
        logger.info("RAG system initialized successfully")
    
    def retrieve(self, query: str) -> List[Dict]:
        """Retrieve relevant chunks for a query."""
        # Create query embedding
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()
        
        # Search in vector database
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        retrieved_chunks = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i]
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= self.similarity_threshold:
                    retrieved_chunks.append({
                        'text': doc,
                        'metadata': results['metadatas'][0][i],
                        'similarity': similarity
                    })
        
        return retrieved_chunks
    
    def format_context(self, chunks: List[Dict]) -> str:
        """Format retrieved chunks into context string."""
        context_parts = []
        current_length = 0
        
        for chunk in chunks:
            chunk_text = f"[Source: {chunk['metadata'].get('page_title', 'Unknown')}"
            if chunk['metadata'].get('section'):
                chunk_text += f" - {chunk['metadata']['section']}"
            chunk_text += f"]\n{chunk['text']}\n\n"
            
            chunk_length = len(chunk_text)
            if current_length + chunk_length > self.max_context_length:
                break
            
            context_parts.append(chunk_text)
            current_length += chunk_length
        
        return '\n'.join(context_parts)
    
    def get_referenced_pages(self, chunks: List[Dict]) -> List[str]:
        """Extract unique page titles from retrieved chunks."""
        pages = set()
        for chunk in chunks:
            page_title = chunk['metadata'].get('page_title')
            if page_title:
                pages.add(page_title)
        return sorted(list(pages))
    
    def generate(self, query: str, context: str) -> str:
        """Generate response using Ollama."""
        # Sanitize the query in the prompt to prevent injection
        safe_query = query.replace('\n', ' ').replace('\r', '')
        
        user_prompt = f"""Context from OSRS Wiki:
{context}

Question: {safe_query}

Answer based on the provided context:"""
        
        # Use the smaller of max_tokens and max_response_tokens for safety
        token_limit = min(self.max_tokens, self.max_response_tokens)
        
        try:
            # Use chat method for better compatibility
            messages = [
                {'role': 'system', 'content': self.system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
            
            response = self.ollama_client.chat(
                model=self.llm_model,
                messages=messages,
                options={
                    'temperature': self.temperature,
                    'num_predict': token_limit
                }
            )
            
            answer = response['message']['content']
            
            # Additional safety: truncate if somehow too long
            # Rough estimate: 1 token ≈ 4 characters
            max_chars = token_limit * 4
            if len(answer) > max_chars:
                answer = answer[:max_chars] + "... [Response truncated]"
                logger.warning(f"Response truncated to {max_chars} characters")
            
            return answer
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Fallback to generate method if chat doesn't work
            try:
                response = self.ollama_client.generate(
                    model=self.llm_model,
                    prompt=f"{self.system_prompt}\n\n{user_prompt}",
                    options={
                        'temperature': self.temperature,
                        'num_predict': token_limit
                    }
                )
                answer = response.get('response', str(response))
                
                # Truncate if needed
                max_chars = token_limit * 4
                if len(answer) > max_chars:
                    answer = answer[:max_chars] + "... [Response truncated]"
                
                return answer
            except Exception as e2:
                logger.error(f"Fallback generate also failed: {e2}")
                return f"Error generating response: {str(e)}"
    
    def query(self, user_query: str, user_id: str = "default", 
              skip_security: bool = False) -> Dict:
        """
        Complete RAG query pipeline with security checks.
        
        Args:
            user_query: The user's query
            user_id: Identifier for rate limiting and logging
            skip_security: Skip security checks (for internal use only)
        
        Returns:
            Dict with answer, sources, chunks, and any security errors
        """
        original_query = user_query
        sanitized = False
        
        # Input validation
        if self.enable_security and not skip_security:
            is_valid, sanitized_query, error_msg = self.security_manager.validate_query(user_query)
            if not is_valid:
                logger.warning(f"Invalid query rejected: {error_msg}")
                return {
                    'answer': f"Query rejected: {error_msg}",
                    'sources': [],
                    'chunks': [],
                    'error': error_msg,
                    'rejected': True
                }
            
            if sanitized_query != user_query:
                sanitized = True
                user_query = sanitized_query
                logger.info("Query was sanitized")
            
            # Rate limiting
            if self.enable_rate_limiting:
                allowed, wait_time = self.security_manager.check_rate_limit(user_id)
                if not allowed:
                    logger.warning(f"Rate limit exceeded for user {user_id}, wait {wait_time:.1f}s")
                    return {
                        'answer': f"Rate limit exceeded. Please wait {wait_time:.1f} seconds before your next query.",
                        'sources': [],
                        'chunks': [],
                        'error': 'rate_limit',
                        'wait_time': wait_time
                    }
        
        # Retrieve relevant chunks
        chunks = self.retrieve(user_query)
        
        if not chunks:
            result = {
                'answer': "I couldn't find relevant information in the OSRS wiki for your query.",
                'sources': [],
                'chunks': []
            }
            # Log even failed queries
            if self.enable_logging and not skip_security:
                self.security_manager.log_query(original_query, result, user_id, sanitized)
            return result
        
        # Format context
        context = self.format_context(chunks)
        
        # Generate response
        answer = self.generate(user_query, context)
        
        # Get referenced pages
        sources = self.get_referenced_pages(chunks)
        
        result = {
            'answer': answer,
            'sources': sources,
            'chunks': chunks
        }
        
        # Log query and response
        if self.enable_logging and not skip_security:
            self.security_manager.log_query(original_query, result, user_id, sanitized)
        
        return result


if __name__ == "__main__":
    # Test the RAG system
    rag = RAGSystem()
    
    test_query = "What are the requirements for the Dragon Slayer quest?"
    result = rag.query(test_query)
    
    print(f"\nQuery: {test_query}")
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nSources: {', '.join(result['sources'])}")

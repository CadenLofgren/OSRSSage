"""
Security Module
Handles input validation, sanitization, rate limiting, and logging.
"""

import re
import time
import logging
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


class InputValidator:
    """Validates and sanitizes user input."""
    
    # Dangerous patterns that could be used for prompt injection
    DANGEROUS_PATTERNS = [
        r'ignore\s+(previous|above|all)\s+(instructions?|prompts?|commands?)',
        r'forget\s+(previous|above|all)',
        r'you\s+are\s+now',
        r'act\s+as\s+if',
        r'pretend\s+to\s+be',
        r'system\s*:',
        r'<\|.*?\|>',  # Special tokens
        r'\[INST\]',  # Instruction tags
        r'\[/INST\]',
    ]
    
    # Maximum query length
    MAX_QUERY_LENGTH = 2000
    
    # Allowed characters (basic alphanumeric, punctuation, spaces)
    ALLOWED_CHARS_PATTERN = re.compile(r'^[a-zA-Z0-9\s\.,!?;:\-\'\"\(\)\[\]\/]+$')
    
    @classmethod
    def validate_and_sanitize(cls, query: str):
        """
        Validate and sanitize user query.
        Returns: (is_valid, sanitized_query, error_message)
        """
        if not query or not isinstance(query, str):
            return False, "", "Query must be a non-empty string"
        
        # Check length
        if len(query) > cls.MAX_QUERY_LENGTH:
            return False, query[:cls.MAX_QUERY_LENGTH], f"Query too long (max {cls.MAX_QUERY_LENGTH} chars)"
        
        # Remove leading/trailing whitespace
        sanitized = query.strip()
        
        if not sanitized:
            return False, "", "Query cannot be empty"
        
        # Check for dangerous patterns (prompt injection attempts)
        sanitized_lower = sanitized.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, sanitized_lower, re.IGNORECASE):
                logger.warning(f"Potential prompt injection detected: {pattern}")
                return False, sanitized, "Query contains potentially unsafe content"
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Remove control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\t')
        
        # Basic character validation (allow most unicode, but log suspicious patterns)
        suspicious_chars = re.findall(r'[^\w\s\.,!?;:\-\'\"\(\)\[\]\/]', sanitized)
        if suspicious_chars:
            unique_suspicious = set(suspicious_chars)
            logger.info(f"Query contains non-standard characters: {unique_suspicious}")
            # Still allow it, but log for review
        
        return True, sanitized, None


class RateLimiter:
    """Rate limiter for queries."""
    
    def __init__(self, min_interval: float = 2.0):
        """
        Initialize rate limiter.
        Args:
            min_interval: Minimum seconds between requests (default: 2.0)
        """
        self.min_interval = min_interval
        self.last_request_time: Dict[str, float] = defaultdict(float)
    
    def check_rate_limit(self, user_id: str = "default"):
        """
        Check if request should be rate limited.
        Returns: (is_allowed, wait_time)
        """
        current_time = time.time()
        last_time = self.last_request_time[user_id]
        
        time_since_last = current_time - last_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            return False, wait_time
        
        # Update last request time
        self.last_request_time[user_id] = current_time
        return True, 0.0
    
    def reset(self, user_id: str = "default"):
        """Reset rate limit for a user."""
        self.last_request_time[user_id] = 0.0


class QueryLogger:
    """Logs queries and responses for debugging."""
    
    def __init__(self, log_file: str = "logs/query_log.jsonl"):
        """Initialize query logger."""
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_query(self, query: str, response: Dict, user_id: str = "default", 
                  sanitized: bool = False) -> None:
        """Log a query and its response."""
        try:
            # Create a hash of the query for privacy (optional)
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
            
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'query_hash': query_hash,
                'query_length': len(query),
                'query_preview': query[:100] + "..." if len(query) > 100 else query,
                'sanitized': sanitized,
                'response_length': len(response.get('answer', '')),
                'sources_count': len(response.get('sources', [])),
                'sources': response.get('sources', []),
                'chunks_retrieved': len(response.get('chunks', []))
            }
            
            # Append to JSONL file
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            logger.debug(f"Logged query: {query_hash}")
            
        except Exception as e:
            logger.error(f"Error logging query: {e}")
    
    def clear_logs(self) -> bool:
        """Clear all query logs."""
        try:
            if self.log_file.exists():
                self.log_file.unlink()
                logger.info("Query logs cleared")
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return False
    
    def get_log_count(self) -> int:
        """Get number of log entries."""
        try:
            if not self.log_file.exists():
                return 0
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error counting logs: {e}")
            return 0


class SecurityManager:
    """Main security manager combining all security features."""
    
    def __init__(self, rate_limit_interval: float = 2.0, log_file: str = "logs/query_log.jsonl"):
        """Initialize security manager."""
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(min_interval=rate_limit_interval)
        self.logger = QueryLogger(log_file=log_file)
    
    def validate_query(self, query: str):
        """Validate and sanitize a query."""
        return self.validator.validate_and_sanitize(query)
    
    def check_rate_limit(self, user_id: str = "default"):
        """Check rate limit for a user."""
        return self.rate_limiter.check_rate_limit(user_id)
    
    def log_query(self, query: str, response: Dict, user_id: str = "default", 
                  sanitized: bool = False) -> None:
        """Log a query and response."""
        self.logger.log_query(query, response, user_id, sanitized)
    
    def clear_logs(self) -> bool:
        """Clear all logs."""
        return self.logger.clear_logs()
    
    def get_log_count(self) -> int:
        """Get number of logged queries."""
        return self.logger.get_log_count()

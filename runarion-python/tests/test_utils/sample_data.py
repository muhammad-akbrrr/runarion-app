"""
Test data generators for creating realistic test scenarios.
Provides utilities for generating test requests, responses, and database records.
"""

import uuid
import json
import random
import time
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

def generate_ulid():
    """
    Generate a ULID (Universally Unique Lexicographically Sortable Identifier).
    Compatible with Laravel's ULID format (26 characters).
    Enhanced for test environments with microsecond precision and additional entropy.
    """
    import time
    import random
    import threading
    import os
    
    # ULID timestamp with microsecond precision for test uniqueness
    timestamp = int(time.time() * 1000000)  # Microsecond precision
    
    # Add additional entropy sources for test environment
    thread_id = threading.get_ident() % 1000  # Thread ID component
    process_id = os.getpid() % 1000  # Process ID component
    random_component = random.randint(0, 999)  # Additional randomness
    
    # Combine entropy sources
    enhanced_timestamp = timestamp + (thread_id << 10) + (process_id << 5) + random_component
    
    # Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    
    # Generate timestamp part (10 characters) from enhanced timestamp
    timestamp_part = ""
    temp_timestamp = enhanced_timestamp
    for _ in range(10):
        timestamp_part = alphabet[temp_timestamp % 32] + timestamp_part
        temp_timestamp //= 32
    
    # Generate random part (16 characters) with cryptographic randomness
    random_part = ""
    for _ in range(16):
        random_part += alphabet[random.randint(0, 31)]
    
    # Add a small delay to ensure uniqueness in rapid succession (test environment only)
    time.sleep(0.001)  # 1ms delay
    
    return timestamp_part + random_part


class SampleDataGenerator:
    """
    Generates realistic test data for various testing scenarios.
    
    Note: This is not a pytest test class, it's a utility class.
    """
    
    def __init__(self, connection_pool=None):
        # Use built-in random data instead of faker
        self.connection_pool = connection_pool
        self.sample_names = [
            "Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince",
            "Edward Norton", "Fiona Apple", "George Lucas", "Hannah Montana"
        ]
        self.sample_words = [
            "adventure", "mystery", "romance", "thriller", "fantasy", "drama",
            "comedy", "action", "horror", "science", "fiction", "biography"
        ]
        self.sample_companies = [
            "TechCorp", "DataSystems", "CloudWorks", "DevStudio", "CodeLabs"
        ]
    
    def get_existing_user_id(self) -> int:
        """
        Get a random existing user ID from the seeded database.
        
        Returns:
            A valid user ID from the users table, or a random number if no DB connection
        """
        if self.connection_pool:
            try:
                conn = self.connection_pool.getconn()
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id FROM users 
                        ORDER BY RANDOM() 
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                finally:
                    self.connection_pool.putconn(conn)
            except Exception:
                # Fall back to random if database query fails
                pass
        
        # Fallback to random number for backward compatibility
        return random.randint(1, 1000)
    
    def generate_draft_request(self, 
                             draft_id: str = None,
                             user_id: int = None,
                             workspace_id: str = None,
                             provider: str = 'openai',
                             **kwargs) -> Dict[str, Any]:
        """
        Generate a realistic draft processing request.
        
        Args:
            draft_id: Optional draft ID
            user_id: Optional user ID
            workspace_id: Optional workspace ID
            provider: AI provider name
            **kwargs: Additional request parameters
            
        Returns:
            Draft request data
        """
        request_data = {
            'draft_id': draft_id or generate_ulid(),
            'file_name': kwargs.get('file_name', 'test_manuscript.txt'),
            'provider': provider,
            'model': kwargs.get('model', self._get_default_model(provider)),
            'user_id': user_id or self.get_existing_user_id(),
            'workspace_id': workspace_id or generate_ulid(),
            'project_id': kwargs.get('project_id', generate_ulid()),
            'chaptering_mode': kwargs.get('chaptering_mode', random.choice(['flexible', 'constrained'])),
            'target_chapter_length': kwargs.get('target_chapter_length', random.choice([1000, 2500, 5000]))
        }
        
        return request_data
    
    def generate_user_data(self, user_id: int = None) -> Dict[str, Any]:
        """
        Generate realistic user data.
        
        Args:
            user_id: Optional user ID
            
        Returns:
            User data
        """
        return {
            'user_id': user_id or random.randint(1, 10000),
            'username': f"user_{random.randint(1000, 9999)}",
            'email': f"user{random.randint(1, 1000)}@example.com",
            'name': random.choice(self.sample_names),
            'created_at': datetime.now() - timedelta(days=random.randint(1, 365)),
            'subscription_tier': random.choice(['free', 'premium', 'enterprise'])
        }
    
    def generate_workspace_data(self, workspace_id: str = None, owner_id: int = None) -> Dict[str, Any]:
        """
        Generate realistic workspace data.
        
        Args:
            workspace_id: Optional workspace ID
            owner_id: Optional owner user ID
            
        Returns:
            Workspace data
        """
        return {
            'workspace_id': workspace_id or generate_ulid(),
            'name': random.choice(self.sample_companies) + ' Workspace',
            'description': f"Test workspace for {random.choice(self.sample_words)} project development",
            'owner_id': owner_id or random.randint(1, 1000),
            'created_at': datetime.now() - timedelta(days=random.randint(1, 180)),
            'member_count': random.randint(1, 50),
            'plan': random.choice(['free', 'professional', 'enterprise'])
        }
    
    def generate_manuscript_content(self, 
                                  chapter_count: int = 3,
                                  words_per_chapter: int = 5000,
                                  genre: str = 'fiction') -> str:
        """
        Generate realistic manuscript content.
        
        Args:
            chapter_count: Number of chapters
            words_per_chapter: Approximate words per chapter
            genre: Genre of the manuscript
            
        Returns:
            Generated manuscript content
        """
        chapters = []
        
        for i in range(chapter_count):
            chapter_title = f"Chapter {i+1}: {random.choice(self.sample_words).title()} {random.choice(self.sample_words).title()}"
            
            # Generate chapter content
            paragraphs = []
            words_written = 0
            
            while words_written < words_per_chapter:
                # Generate paragraph with random sentences
                sentences = []
                for _ in range(random.randint(3, 8)):
                    sentence_words = random.choices(self.sample_words, k=random.randint(8, 15))
                    sentence = " ".join(sentence_words) + "."
                    sentences.append(sentence.capitalize())
                
                paragraph = " ".join(sentences)
                paragraphs.append(paragraph)
                words_written += len(paragraph.split())
            
            chapter_content = f"{chapter_title}\n\n" + "\n\n".join(paragraphs)
            chapters.append(chapter_content)
        
        return "\n\n" + "="*50 + "\n\n".join(chapters)
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for a provider."""
        model_mapping = {
            'openai': 'gpt-4o-mini',
            'gemini': 'gemini-2.0-flash',
            'deepseek': 'deepseek-chat'
        }
        return model_mapping.get(provider, 'gpt-4o-mini')
    
    def generate_batch_requests(self, 
                              count: int = 10,
                              user_id: int = None,
                              workspace_id: str = None) -> List[Dict[str, Any]]:
        """
        Generate a batch of draft requests for load testing.
        
        Args:
            count: Number of requests to generate
            user_id: Optional fixed user ID
            workspace_id: Optional fixed workspace ID
            
        Returns:
            List of draft requests
        """
        requests = []
        
        for i in range(count):
            request = self.generate_draft_request(
                user_id=user_id,
                workspace_id=workspace_id,
                file_name=f'test_manuscript_{i+1}.txt',
                provider=random.choice(['openai', 'gemini', 'deepseek'])
            )
            requests.append(request)
        
        return requests
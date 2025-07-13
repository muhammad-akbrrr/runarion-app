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
    """
    # ULID timestamp (48 bits) + randomness (80 bits)
    timestamp = int(time.time() * 1000)  # Current time in milliseconds
    
    # Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    
    # Generate timestamp part (10 characters)
    timestamp_part = ""
    temp_timestamp = timestamp
    for _ in range(10):
        timestamp_part = alphabet[temp_timestamp % 32] + timestamp_part
        temp_timestamp //= 32
    
    # Generate random part (16 characters)
    random_part = ""
    for _ in range(16):
        random_part += alphabet[random.randint(0, 31)]
    
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
                                  words_per_chapter: int = 2000,
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
    
    def generate_scene_data(self, 
                          scene_number: int = 1,
                          draft_id: str = None) -> Dict[str, Any]:
        """
        Generate realistic scene data.
        
        Args:
            scene_number: Scene number
            draft_id: Associated draft ID
            
        Returns:
            Scene data
        """
        characters = [random.choice(self.sample_names) for _ in range(random.randint(1, 4))]
        
        return {
            'draft_id': draft_id or generate_ulid(),
            'scene_number': scene_number,
            'title': f"Scene {scene_number}: {random.choice(self.sample_words).title()}",
            'summary': f"A {random.choice(self.sample_words)} scene involving {', '.join(characters[:2])}",
            'setting': f"A {random.choice(['dark', 'bright', 'mysterious', 'peaceful'])} {random.choice(['forest', 'room', 'street', 'building'])}",
            'characters': characters,
            'original_content': f"Scene {scene_number} content with {random.choice(self.sample_words)} and {random.choice(self.sample_words)} elements. " * 20,
            'analysis_json': {
                'emotional_tone': random.choice(['tense', 'peaceful', 'exciting', 'melancholic']),
                'pacing': random.choice(['slow', 'moderate', 'fast']),
                'conflict_level': random.choice(['low', 'medium', 'high'])
            }
        }
    
    def generate_chunk_data(self, 
                          chunk_number: int = 1,
                          draft_id: str = None,
                          chunk_size: int = 1000) -> Dict[str, Any]:
        """
        Generate realistic chunk data.
        
        Args:
            chunk_number: Chunk number
            draft_id: Associated draft ID
            chunk_size: Approximate size in characters
            
        Returns:
            Chunk data
        """
        # Generate text that approximates the chunk size
        words_needed = chunk_size // 6  # Rough estimate
        raw_text = " ".join(random.choices(self.sample_words, k=words_needed))
        
        return {
            'draft_id': draft_id or generate_ulid(),
            'chunk_number': chunk_number,
            'raw_text': raw_text,
            'cleaned_text': raw_text,  # Initially same as raw
            'token_count': len(raw_text.split()),
            'character_count': len(raw_text)
        }
    
    def generate_analysis_report(self, 
                               draft_id: str = None,
                               report_type: str = 'character_analysis') -> Dict[str, Any]:
        """
        Generate realistic analysis report data.
        
        Args:
            draft_id: Associated draft ID
            report_type: Type of analysis report
            
        Returns:
            Analysis report data
        """
        report_content = {
            'character_analysis': {
                'main_characters': [
                    {
                        'name': random.choice(self.sample_names),
                        'role': random.choice(['protagonist', 'antagonist', 'supporting']),
                        'traits': [random.choice(self.sample_words) for _ in range(3)],
                        'development_arc': f"Character shows {random.choice(self.sample_words)} throughout the story"
                    }
                    for _ in range(random.randint(2, 5))
                ],
                'character_relationships': [
                    {
                        'character_1': random.choice(self.sample_names),
                        'character_2': random.choice(self.sample_names),
                        'relationship_type': random.choice(['friendship', 'rivalry', 'romance', 'family']),
                        'strength': random.uniform(0.1, 1.0)
                    }
                    for _ in range(random.randint(1, 3))
                ]
            },
            'plot_analysis': {
                'plot_structure': random.choice(['three_act', 'five_act', 'episodic']),
                'themes': [random.choice(self.sample_words) for _ in range(random.randint(2, 4))],
                'conflicts': [
                    {
                        'type': random.choice(['internal', 'external', 'interpersonal']),
                        'description': f"Conflict involving {random.choice(self.sample_words)}"
                    }
                    for _ in range(random.randint(1, 3))
                ]
            },
            'style_analysis': {
                'writing_style': random.choice(['descriptive', 'dialogue-heavy', 'action-oriented']),
                'tone': random.choice(['formal', 'casual', 'poetic']),
                'vocabulary_complexity': random.choice(['simple', 'moderate', 'complex']),
                'sentence_structure': random.choice(['simple', 'compound', 'complex'])
            }
        }
        
        return {
            'draft_id': draft_id or generate_ulid(),
            'report_type': report_type,
            'report_subject': 'manuscript_analysis',
            'content_json': report_content.get(report_type, report_content['character_analysis']),
            'created_at': datetime.now(),
            'analysis_confidence': random.uniform(0.6, 0.95)
        }
    
    def generate_plot_issue(self, 
                          draft_id: str = None,
                          issue_type: str = '01') -> Dict[str, Any]:
        """
        Generate realistic plot issue data.
        
        Args:
            draft_id: Associated draft ID
            issue_type: Type of plot issue ('01' = plot_hole, '02' = inconsistency)
            
        Returns:
            Plot issue data
        """
        issue_descriptions = {
            '01': [  # Plot holes
                'Character motivation unclear',
                'Missing setup for plot point',
                'Unexplained character knowledge',
                'Timeline inconsistency'
            ],
            '02': [  # Inconsistencies
                'Character trait contradiction',
                'Setting description mismatch',
                'Dialog style inconsistency',
                'World-building contradiction'
            ]
        }
        
        return {
            'draft_id': draft_id or generate_ulid(),
            'issue_type': issue_type,
            'description': random.choice(issue_descriptions.get(issue_type, issue_descriptions['01'])),
            'severity': random.choice(['low', 'medium', 'high']),
            'location': f"scene_{random.randint(1, 10)}",
            'suggested_fix': f"Fix by addressing {random.choice(self.sample_words)} issues",
            'created_at': datetime.now()
        }
    
    def generate_chapter_data(self, 
                            chapter_number: int = 1,
                            draft_id: str = None) -> Dict[str, Any]:
        """
        Generate realistic chapter data.
        
        Args:
            chapter_number: Chapter number
            draft_id: Associated draft ID
            
        Returns:
            Chapter data
        """
        word_count = random.randint(1500, 3500)
        content = " ".join(random.choices(self.sample_words, k=word_count))
        
        return {
            'draft_id': draft_id or generate_ulid(),
            'chapter_number': chapter_number,
            'title': f"Chapter {chapter_number}: {random.choice(self.sample_words).title()} {random.choice(self.sample_words).title()}",
            'content': content,
            'word_count': word_count,
            'scene_count': random.randint(1, 4),
            'created_at': datetime.now()
        }
    
    def generate_api_response(self, 
                            success: bool = True,
                            data: Dict[str, Any] = None,
                            error_message: str = None) -> Dict[str, Any]:
        """
        Generate realistic API response.
        
        Args:
            success: Whether the response indicates success
            data: Response data payload
            error_message: Error message if not successful
            
        Returns:
            API response data
        """
        if success:
            return {
                'success': True,
                'data': data or {},
                'message': 'Request processed successfully',
                'timestamp': datetime.now().isoformat(),
                'request_id': generate_ulid()
            }
        else:
            return {
                'success': False,
                'error': {
                    'message': error_message or 'An error occurred',
                    'code': random.choice(['VALIDATION_ERROR', 'PROCESSING_ERROR', 'SYSTEM_ERROR']),
                    'details': {}
                },
                'timestamp': datetime.now().isoformat(),
                'request_id': generate_ulid()
            }
    
    def generate_processing_timeline(self, 
                                   draft_id: str = None,
                                   total_duration_minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Generate realistic processing timeline events.
        
        Args:
            draft_id: Associated draft ID
            total_duration_minutes: Total processing duration in minutes
            
        Returns:
            List of timeline events
        """
        stages = [
            ('processing', 'Processing started'),
            ('stage_1_complete', 'Document ingestion completed'),
            ('stage_2_complete', 'Text cleaning completed'),
            ('stage_3_complete', 'Scene extraction completed'),
            ('stage_4_complete', 'Analysis completed'),
            ('stage_5_complete', 'Coherence check completed'),
            ('stage_6_complete', 'Enhancement completed'),
            ('completed', 'Processing completed')
        ]
        
        timeline = []
        current_time = datetime.now() - timedelta(minutes=total_duration_minutes)
        
        for i, (status, description) in enumerate(stages):
            # Add some randomness to timing
            stage_duration = random.uniform(2, 8)  # 2-8 minutes per stage
            current_time += timedelta(minutes=stage_duration)
            
            timeline.append({
                'draft_id': draft_id or generate_ulid(),
                'status': status,
                'description': description,
                'timestamp': current_time.isoformat(),
                'stage_number': i + 1,
                'duration_minutes': stage_duration
            })
        
        return timeline
    
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
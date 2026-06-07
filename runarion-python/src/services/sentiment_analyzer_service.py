"""
SentimentAnalyzerService - Service for analyzing character relationships and sentiment.

This service handles:
- Extracting relationships from manuscript content
- Auto-calculating sentiment scores with reasons
- Gathering text evidence for relationship assessments
- Storing relationships in Apache AGE graph database
- Tracking relationship changes over time
"""

import logging
import json
import uuid
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from src.services.records_manager import RecordsManager
from src.services.generation_engine import GenerationEngine
from src.models.request import BaseGenerationRequest, GenerationConfig
from src.models.quota import QuotaCaller
from src.utils.json_response_parser import JSONResponseParser

logger = logging.getLogger(__name__)


class SentimentAnalyzerService:
    """
    Service for character relationship and sentiment analysis.
    Works with manuscripts being actively written (proactive writing flow).
    """
    
    def __init__(self, db_pool):
        """
        Initialize the Sentiment Analyzer Service.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self.records_manager = RecordsManager(db_pool)
        
        logger.info("SentimentAnalyzerService initialized")
    
    def _create_caller(self, project_id: str, workspace_id: str = None) -> QuotaCaller:
        """
        Create a QuotaCaller for generation requests.
        """
        user_id = 1  # Default fallback
        api_keys = {}
        
        if workspace_id:
            try:
                conn = self.db_pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT wm.user_id 
                            FROM workspace_members wm
                            WHERE wm.workspace_id = %s
                            ORDER BY wm.role = 'owner' DESC, wm.created_at ASC
                            LIMIT 1
                        """, (workspace_id,))
                        result = cursor.fetchone()
                        if result:
                            user_id = result[0]
                finally:
                    self.db_pool.putconn(conn)
            except Exception as e:
                logger.debug(f"Could not get user_id from workspace: {e}, using default")
        
        return QuotaCaller.from_request_data(
            user_id=user_id,
            workspace_id=workspace_id or project_id,
            project_id=project_id,
            session_id=str(uuid.uuid4()),
            api_keys=api_keys
        )
    
    def _get_generation_engine(self, model: str, provider: str, caller: QuotaCaller) -> GenerationEngine:
        """Create a GenerationEngine instance for AI calls."""
        generation_config = GenerationConfig(
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_output_tokens=8192  # Increased to handle chapters with many interactions
        )
        
        base_request = BaseGenerationRequest(
            prompt="",
            instruction="",
            model=model,
            provider=provider,
            generation_config=generation_config,
            caller=caller  # caller must be in the request, not separate
        )
        
        return GenerationEngine(base_request)
    
    # =========================================================================
    # SENTIMENT CALCULATION
    # =========================================================================
    
    def calculate_sentiment_score(
        self, 
        emotional_tone: str, 
        context: str,
        relationship_type: str = ""
    ) -> Tuple[int, List[str]]:
        """
        Calculate sentiment score with detailed reasons (CK3-style breakdown).
        
        Args:
            emotional_tone: The emotional tone (hostile/neutral/friendly/etc.)
            context: The context text describing the relationship
            relationship_type: The type of relationship (LOVES, HATES, etc.)
            
        Returns:
            Tuple of (score: int, reasons: List[str])
        """
        reasons = []
        
        # Base scores from emotional_tone
        tone_scores = {
            'hostile': -70,
            'antagonistic': -60,
            'distrustful': -40,
            'cold': -30,
            'neutral': 0,
            'professional': 10,
            'cordial': 20,
            'friendly': 45,
            'warm': 55,
            'affectionate': 65,
            'romantic': 80,
            'familial': 60,
            'devoted': 85
        }
        
        tone_lower = emotional_tone.lower().strip()
        base_score = tone_scores.get(tone_lower, 0)
        reasons.append(f"Base tone: {emotional_tone} ({base_score:+d})")
        
        # Relationship type modifiers
        rel_type_modifiers = {
            'LOVES': 30, 'ADORES': 35, 'MARRIED_TO': 25, 'ENGAGED_TO': 20,
            'TRUSTS': 20, 'PROTECTS': 15, 'MENTORS': 15, 'MENTOR_TO': 15,
            'ALLIED_WITH': 10, 'FRIENDS_WITH': 15, 'SUPPORTS': 10,
            'RESPECTS': 10, 'ADMIRES': 15,
            'KNOWS': 0, 'INTERACTS_WITH': 0, 'RELATED_TO': 0,
            'RIVALS': -15, 'RIVAL_OF': -15, 'COMPETES_WITH': -10,
            'DISTRUSTS': -20, 'FEARS': -25,
            'DISLIKES': -30, 'RESENTS': -35,
            'HATES': -40, 'DESPISES': -50,
            'BETRAYED': -60, 'BETRAYS': -55, 'ENEMY_OF': -50
        }
        
        rel_upper = relationship_type.upper().replace(' ', '_')
        if rel_upper in rel_type_modifiers:
            mod = rel_type_modifiers[rel_upper]
            if mod != 0:
                reasons.append(f"Relationship type: {relationship_type} ({mod:+d})")
                base_score += mod
        
        # Context keyword analysis
        context_lower = context.lower() if context else ""
        
        negative_keywords = {
            'betray': -30, 'betrayed': -30, 'betrayal': -30,
            'hate': -25, 'hates': -25, 'hatred': -25,
            'despise': -25, 'despises': -25,
            'enemy': -20, 'enemies': -20,
            'kill': -20, 'killed': -20, 'murder': -25,
            'threaten': -15, 'threatens': -15, 'threatened': -15,
            'attack': -15, 'attacks': -15, 'attacked': -15,
            'fear': -15, 'fears': -15, 'afraid': -15,
            'distrust': -15, 'distrusts': -15,
            'resent': -15, 'resents': -15, 'resentment': -15,
            'anger': -10, 'angry': -10,
            'rivalry': -10, 'rival': -10,
            'conflict': -10, 'conflicts': -10,
            'tension': -8, 'tense': -8,
            'suspicious': -8, 'suspicion': -8,
            'cold': -5, 'distant': -5
        }
        
        positive_keywords = {
            'love': 25, 'loves': 25, 'beloved': 25,
            'adore': 25, 'adores': 25,
            'trust': 20, 'trusts': 20,
            'protect': 20, 'protects': 20, 'protecting': 20,
            'devotion': 20, 'devoted': 20,
            'loyal': 18, 'loyalty': 18,
            'friend': 15, 'friends': 15, 'friendship': 15,
            'support': 15, 'supports': 15, 'supporting': 15,
            'care': 15, 'cares': 15, 'caring': 15,
            'respect': 12, 'respects': 12,
            'admire': 12, 'admires': 12, 'admiration': 12,
            'ally': 10, 'allies': 10, 'alliance': 10,
            'mentor': 10, 'mentors': 10, 'guidance': 10,
            'help': 8, 'helps': 8, 'helping': 8,
            'bond': 8, 'bonded': 8,
            'comfort': 8, 'comforts': 8,
            'warm': 5, 'warmth': 5,
            'kind': 5, 'kindness': 5
        }
        
        # Track which modifiers we've already applied to avoid double-counting
        applied_modifiers = set()
        
        for keyword, mod in negative_keywords.items():
            if keyword in context_lower and keyword not in applied_modifiers:
                # Check for negation (e.g., "doesn't hate")
                negation_pattern = rf"(doesn\'t|don\'t|not|never|no longer)\s+\w*\s*{keyword}"
                if not re.search(negation_pattern, context_lower):
                    base_score += mod
                    reasons.append(f"Context: \"{keyword}\" ({mod:+d})")
                    applied_modifiers.add(keyword)
                    # Also add related words to avoid double-counting
                    if keyword.endswith('s'):
                        applied_modifiers.add(keyword[:-1])
                    else:
                        applied_modifiers.add(keyword + 's')
        
        for keyword, mod in positive_keywords.items():
            if keyword in context_lower and keyword not in applied_modifiers:
                # Check for negation
                negation_pattern = rf"(doesn\'t|don\'t|not|never|no longer)\s+\w*\s*{keyword}"
                if not re.search(negation_pattern, context_lower):
                    base_score += mod
                    reasons.append(f"Context: \"{keyword}\" ({mod:+d})")
                    applied_modifiers.add(keyword)
                    if keyword.endswith('s'):
                        applied_modifiers.add(keyword[:-1])
                    else:
                        applied_modifiers.add(keyword + 's')
        
        # Clamp to -100 to +100
        final_score = max(-100, min(100, base_score))
        
        return final_score, reasons
    
    def _sentiment_to_tone(self, sentiment_score: int) -> str:
        """
        Derive emotional tone from sentiment score.
        Used when AI provides score but not explicit tone.
        """
        if sentiment_score <= -70:
            return 'hostile'
        elif sentiment_score <= -50:
            return 'antagonistic'
        elif sentiment_score <= -30:
            return 'cold'
        elif sentiment_score <= -10:
            return 'distrustful'
        elif sentiment_score <= 10:
            return 'neutral'
        elif sentiment_score <= 30:
            return 'cordial'
        elif sentiment_score <= 50:
            return 'friendly'
        elif sentiment_score <= 70:
            return 'warm'
        else:
            return 'affectionate'
    
    # =========================================================================
    # CHAPTER-BASED RELATIONSHIP ANALYSIS (NEW APPROACH)
    # =========================================================================
    
    def _get_chapter_analysis_prompt(self) -> str:
        """
        Prompt for analyzing how one character engages with another in a single chapter.
        This is the core of the new simpler approach.
        """
        return """Analyze how {source_character} engages with {target_character} in this chapter.

CHAPTER: {chapter_name}
CONTENT:
{chapter_content}

ANALYSIS REQUIRED:

1. SENTIMENT SCORE (-100 to +100): How positive/negative is {source_character}'s attitude toward {target_character}?
   - Very negative (hostile, hateful): -80 to -100
   - Negative (cold, distrustful): -40 to -79
   - Slightly negative (tense, wary): -10 to -39
   - Neutral: -9 to +9
   - Slightly positive (cordial, respectful): +10 to +39
   - Positive (friendly, supportive): +40 to +79
   - Very positive (devoted, loving): +80 to +100

2. RELATIONSHIP TYPE: Choose ONE:
   FRIEND, ALLY, MENTOR, PROTECTOR, RIVAL, ENEMY, LOVER, FAMILY, SUBORDINATE, LEADER, ACQUAINTANCE, STRANGER

3. EMOTIONAL TONE: The dominant emotional quality (be specific and creative):
   Examples: warm, cold, tense, playful, hostile, protective, suspicious, affectionate, brotherly, wary-but-trusting

4. DETAILED SUMMARY: 4-6 sentences describing:
   - How {source_character} treats {target_character} in this chapter
   - What actions/words demonstrate their feelings
   - Any significant moments or shifts in their dynamic

5. KEY EVIDENCE: Provide 3-5 direct quotes from the chapter that show their relationship.
   Each quote should be 20-80 characters and demonstrate a specific aspect of their dynamic.

Return JSON only:
{{
  "sentiment_score": <number -100 to +100>,
  "relationship_type": "TYPE",
  "emotional_tone": "tone",
  "summary": "Detailed 4-6 sentence analysis",
  "key_evidence": [
    {{"quote": "Direct quote from text", "context": "What this shows about their relationship"}},
    {{"quote": "Another quote", "context": "What this demonstrates"}},
    {{"quote": "Third quote", "context": "Significance"}}
  ]
}}"""

    def _get_overall_relationship_prompt(self) -> str:
        """Prompt for synthesizing overall relationship from chapter analyses."""
        return """Based on these chapter-by-chapter analyses, synthesize the OVERALL relationship.

CHARACTER PAIR: {source_character} → {target_character}

CHAPTER ANALYSES:
{chapter_analyses}

Synthesize an overall assessment:
1. OVERALL SENTIMENT (-100 to +100): Considering all chapters, what's the overall sentiment?
2. RELATIONSHIP TYPE: The dominant type across chapters
3. EMOTIONAL TONE: The prevailing emotional quality
4. RELATIONSHIP SUMMARY: 2-3 sentences capturing the essence of how {source_character} views {target_character}
5. PROGRESSION: Brief note on how the relationship evolved (if at all)

Return JSON only:
{{
  "overall_sentiment": <number>,
  "relationship_type": "TYPE",
  "emotional_tone": "tone",
  "summary": "Overall relationship description",
  "progression": "How the relationship evolved across chapters"
}}"""

    def analyze_relationship_by_chapters(
        self,
        project_id: str,
        workspace_id: str,
        source_character: str,
        target_character: str,
        chapters: List[Dict[str, Any]],
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Analyze how source_character engages with target_character across chapters.
        
        This is the NEW simpler approach - one analysis per chapter, not micro-interactions.
        
        Returns:
            {
                'source': str,
                'target': str,
                'chapter_analyses': [...],
                'overall': {...},
                'success': bool
            }
        """
        logger.info(f"analyze_relationship_by_chapters called: {source_character} → {target_character}, chapters_count={len(chapters) if chapters else 0}")
        
        chapter_analyses = []
        
        if not chapters:
            logger.warning(f"No chapters provided for {source_character} → {target_character}")
            return {
                'source': source_character,
                'target': target_character,
                'chapter_analyses': [],
                'overall': None,
                'success': False,
                'error': 'No chapters provided for analysis'
            }
        
        logger.info(f"Starting chapter loop with {len(chapters)} chapters")
        
        for idx, chapter in enumerate(chapters):
            try:
                logger.info(f"Processing chapter {idx + 1}/{len(chapters)}")
                
                # Ensure chapter numbers are 1-based (some systems use 0-based indexing)
                raw_order = chapter.get('order', 0)
                # Fix: Convert string order to int if needed
                if isinstance(raw_order, str):
                    try:
                        raw_order = int(raw_order)
                    except ValueError:
                        raw_order = 0
                        
                # Always convert 0-indexed order to 1-indexed chapter number
                chapter_number = raw_order + 1
                chapter_name = chapter.get('chapter_name', f"Chapter {chapter_number}")
                chapter_content = chapter.get('content', '')
                
                logger.info(f"Processing {chapter_name} (order={raw_order}, num={chapter_number}), content length: {len(chapter_content) if chapter_content else 0}")
            
                if not chapter_content or not chapter_content.strip():
                    logger.warning(f"Skipping {chapter_name} - no content")
                    continue
                
                # Analyze this chapter
                analysis = self._analyze_single_chapter(
                    project_id=project_id,
                    workspace_id=workspace_id,
                    source_character=source_character,
                    target_character=target_character,
                    chapter_name=chapter_name,
                    chapter_number=chapter_number,
                    chapter_content=chapter_content,
                    model=model,
                    provider=provider
                )
                
                if analysis:
                    chapter_analyses.append(analysis)
                    logger.info(f"  ✓ {chapter_name} analysis successful: score={analysis.get('sentiment_score', '?')}")
                else:
                    logger.warning(f"  ✗ {chapter_name} analysis returned None/empty")
                
                # Rate limiting delay between chapter analyses to avoid 429 errors
                # Even paid tier has per-minute request limits
                time.sleep(1.5)  # 1.5 second delay between each chapter analysis
                
            except Exception as chapter_error:
                logger.error(f"Error processing chapter {idx}: {chapter_error}", exc_info=True)
        
        if not chapter_analyses:
            return {
                'source': source_character,
                'target': target_character,
                'chapter_analyses': [],
                'overall': None,
                'success': False,
                'error': 'No chapter analyses could be generated'
            }
        
        # Synthesize overall relationship
        overall = self._synthesize_overall_relationship(
            project_id=project_id,
            workspace_id=workspace_id,
            source_character=source_character,
            target_character=target_character,
            chapter_analyses=chapter_analyses,
            model=model,
            provider=provider
        )
        
        return {
            'source': source_character,
            'target': target_character,
            'chapter_analyses': chapter_analyses,
            'overall': overall,
            'success': True
        }
    
    def _analyze_single_chapter(
        self,
        project_id: str,
        workspace_id: str,
        source_character: str,
        target_character: str,
        chapter_name: str,
        chapter_number: int,
        chapter_content: str,
        model: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze how source engages with target in a single chapter."""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                caller = self._create_caller(project_id, workspace_id)
                engine = self._get_generation_engine(model, provider, caller)
                
                prompt = self._get_chapter_analysis_prompt().format(
                    source_character=source_character,
                    target_character=target_character,
                    chapter_name=chapter_name,
                    chapter_content=chapter_content[:12000]  # Limit content
                )
                
                engine.request.prompt = prompt
                engine.request.instruction = f"Analyze {source_character}'s engagement with {target_character}. Return JSON only."
                
                response = engine.generate(skip_quota=True)
                
                if not response.success:
                    error_msg = response.error_message or ''
                    # Check for rate limit error
                    if '429' in str(error_msg) or 'RESOURCE_EXHAUSTED' in str(error_msg):
                        if attempt < max_retries - 1:
                            logger.warning(f"Rate limited for {chapter_name}, waiting {retry_delay}s before retry {attempt + 2}/{max_retries}")
                            time.sleep(retry_delay)
                            retry_delay *= 1.5  # Increase delay for next retry
                            continue
                    logger.warning(f"AI failed for {source_character} → {target_character} in {chapter_name}: {error_msg}")
                    return None
                
                # Success - break out of retry loop
                break
                
            except Exception as e:
                if attempt < max_retries - 1 and ('429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e)):
                    logger.warning(f"Rate limit exception for {chapter_name}, waiting {retry_delay}s before retry")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                logger.error(f"Error analyzing chapter {chapter_name}: {e}")
                return None
        
        # Parse response (after successful generation)
        try:
            response_text = response.text.strip()
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                logger.warning(f"No JSON found in response for {chapter_name}")
                return None
            
            analysis = json.loads(json_match.group())
            
            # Validate and clamp score
            score = analysis.get('sentiment_score', 0)
            try:
                score = int(score)
                score = max(-100, min(100, score))
            except:
                score = 0
            
            # Handle both old format (key_moment) and new format (key_evidence)
            key_evidence = analysis.get('key_evidence', [])
            if not key_evidence and analysis.get('key_moment'):
                # Backward compatibility: convert key_moment to key_evidence format
                key_evidence = [{'quote': analysis.get('key_moment', ''), 'context': ''}]
            
            return {
                'chapter_number': chapter_number,
                'chapter_name': chapter_name,
                'sentiment_score': score,
                'relationship_type': analysis.get('relationship_type', 'ACQUAINTANCE'),
                'emotional_tone': analysis.get('emotional_tone', 'neutral'),
                'summary': analysis.get('summary', ''),
                'key_evidence': key_evidence  # Array of {quote, context}
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed for {chapter_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing chapter analysis for {chapter_name}: {e}")
            return None
    
    def _synthesize_overall_relationship(
        self,
        project_id: str,
        workspace_id: str,
        source_character: str,
        target_character: str,
        chapter_analyses: List[Dict[str, Any]],
        model: str,
        provider: str
    ) -> Dict[str, Any]:
        """Synthesize overall relationship from chapter analyses."""
        import time
        
        max_retries = 3
        retry_delay = 5
        
        # Build chapter analyses summary for prompt
        analyses_text = ""
        for ca in chapter_analyses:
            analyses_text += f"\n{ca['chapter_name']} (score: {ca['sentiment_score']:+d}):\n"
            analyses_text += f"  Type: {ca['relationship_type']}, Tone: {ca['emotional_tone']}\n"
            analyses_text += f"  Summary: {ca['summary']}\n"
        
        for attempt in range(max_retries):
            try:
                caller = self._create_caller(project_id, workspace_id)
                engine = self._get_generation_engine(model, provider, caller)
                
                prompt = self._get_overall_relationship_prompt().format(
                    source_character=source_character,
                    target_character=target_character,
                    chapter_analyses=analyses_text
                )
                
                engine.request.prompt = prompt
                engine.request.instruction = "Synthesize overall relationship. Return JSON only."
                
                response = engine.generate(skip_quota=True)
                
                if not response.success:
                    error_msg = response.error_message or ''
                    # Check for rate limit error
                    if '429' in str(error_msg) or 'RESOURCE_EXHAUSTED' in str(error_msg):
                        if attempt < max_retries - 1:
                            logger.warning(f"Rate limited for synthesis, waiting {retry_delay}s before retry {attempt + 2}/{max_retries}")
                            time.sleep(retry_delay)
                            retry_delay *= 1.5
                            continue
                    # If we get here, give up and fall back
                    avg_score = sum(ca['sentiment_score'] for ca in chapter_analyses) // len(chapter_analyses)
                    return {
                        'overall_sentiment': avg_score,
                        'relationship_type': chapter_analyses[-1].get('relationship_type', 'ACQUAINTANCE'),
                        'emotional_tone': chapter_analyses[-1].get('emotional_tone', 'neutral'),
                        'summary': 'Unable to synthesize - showing latest chapter analysis.',
                        'progression': ''
                    }
                
                # Parse response
                response_text = response.text.strip()
                response_text = re.sub(r'```json\s*', '', response_text)
                response_text = re.sub(r'```\s*', '', response_text)
                
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    try:
                        overall = json.loads(json_match.group())
                        # Clamp score
                        score = overall.get('overall_sentiment', 0)
                        try:
                            score = int(score)
                            score = max(-100, min(100, score))
                        except:
                            score = 0
                        overall['overall_sentiment'] = score
                        return overall
                    except:
                        pass
                
                # Fallback
                avg_score = sum(ca['sentiment_score'] for ca in chapter_analyses) // len(chapter_analyses)
                return {
                    'overall_sentiment': avg_score,
                    'relationship_type': chapter_analyses[-1].get('relationship_type', 'ACQUAINTANCE'),
                    'emotional_tone': chapter_analyses[-1].get('emotional_tone', 'neutral'),
                    'summary': 'Relationship synthesized from chapter analyses.',
                    'progression': ''
                }
                
            except Exception as e:
                if attempt < max_retries - 1 and ('429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e)):
                    logger.warning(f"Rate limit exception for synthesis, waiting {retry_delay}s before retry")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                logger.error(f"Error synthesizing relationship: {e}")
                avg_score = sum(ca['sentiment_score'] for ca in chapter_analyses) // len(chapter_analyses) if chapter_analyses else 0
                return {
                    'overall_sentiment': avg_score,
                    'relationship_type': 'ACQUAINTANCE',
                    'emotional_tone': 'neutral',
                    'summary': f'Error during synthesis: {e}',
                    'progression': ''
                }
        
        # Shouldn't reach here, but fallback just in case
        avg_score = sum(ca['sentiment_score'] for ca in chapter_analyses) // len(chapter_analyses) if chapter_analyses else 0
        return {
            'overall_sentiment': avg_score,
            'relationship_type': 'ACQUAINTANCE',
            'emotional_tone': 'neutral',
            'summary': 'Synthesis completed with fallback.',
            'progression': ''
        }

    def extract_relationships_v2(
        self,
        project_id: str,
        workspace_id: str,
        character_ids: Optional[List[str]] = None,
        chapter_orders: Optional[List[int]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini",
        focus_mode: str = "all"  # 'all', 'selected', or '1-to-1'
    ) -> Dict[str, Any]:
        """
        NEW V2: Extract relationships using chapter-based analysis.
        
        Modes:
        - 'all': Analyze all character pairs
        - 'selected': Analyze selected characters with all others
        - '1-to-1': Analyze exactly 2 characters (both directions)
        
        Returns chapter-by-chapter analysis for each relationship.
        """
        try:
            # Get chapters
            all_chapters = self.get_chapters(project_id, workspace_id)
            if not all_chapters:
                return {'error': 'No chapters found', 'success': False}
            
            # Filter chapters if specified
            chapters_to_process = all_chapters
            if chapter_orders is not None:
                # Debug: Log what we're filtering
                all_orders = [ch.get('order') for ch in all_chapters]
                logger.info(f"Filtering chapters: requested orders={chapter_orders} (types={[type(o).__name__ for o in chapter_orders]}), available orders={all_orders} (types={[type(o).__name__ for o in all_orders]})")
                
                # Handle potential type mismatches (int vs str)
                chapter_orders_set = set(chapter_orders)
                chapter_orders_str = {str(o) for o in chapter_orders}
                
                chapters_to_process = [
                    ch for ch in all_chapters 
                    if ch.get('order') in chapter_orders_set or str(ch.get('order')) in chapter_orders_str
                ]
                logger.info(f"After filtering: {len(chapters_to_process)} chapters")
            
            if not chapters_to_process:
                return {'error': 'No chapters match specified orders', 'success': False}
            
            # Get characters
            existing_characters = self.get_existing_characters(project_id)
            if not existing_characters:
                return {'error': 'No characters found. Extract entities first.', 'success': False}
            
            # Determine which characters to process
            all_char_names = [c.get('name') for c in existing_characters if c.get('name')]
            
            if character_ids:
                selected_chars = [
                    c.get('name') for c in existing_characters
                    if str(c.get('vertex_id')) in [str(id) for id in character_ids] and c.get('name')
                ]
            else:
                selected_chars = all_char_names
            
            if not selected_chars:
                return {'error': 'No valid characters to analyze', 'success': False}
            
            # Validate 1-to-1 mode
            if focus_mode == '1-to-1' and len(selected_chars) != 2:
                return {'error': f'1-to-1 mode requires exactly 2 characters. Found: {len(selected_chars)}', 'success': False}
            
            logger.info("=== V2 EXTRACTION START ===")
            logger.info(f"Mode: {focus_mode}, Characters: {len(selected_chars)}, Chapters: {len(chapters_to_process)}")
            
            # Debug: Log chapter details
            for i, ch in enumerate(chapters_to_process):
                ch_order = ch.get('order')
                ch_name = ch.get('chapter_name', 'Unknown')
                ch_content = ch.get('content', '')
                content_len = len(ch_content) if ch_content else 0
                logger.info(f"  Chapter {i}: order={ch_order} (type={type(ch_order).__name__}), name={ch_name}, content_length={content_len}")
            
            # Determine character pairs to analyze
            pairs_to_analyze = []
            
            if focus_mode == '1-to-1':
                # Both directions between the 2 selected characters
                char1, char2 = selected_chars[0], selected_chars[1]
                pairs_to_analyze = [(char1, char2), (char2, char1)]
                
            elif focus_mode == 'selected':
                # Selected characters with all others
                for selected in selected_chars:
                    for other in all_char_names:
                        if selected != other:
                            pairs_to_analyze.append((selected, other))
                            
            else:  # 'all' mode
                # All pairs (both directions)
                for i, char1 in enumerate(all_char_names):
                    for char2 in all_char_names:
                        if char1 != char2:
                            pairs_to_analyze.append((char1, char2))
            
            logger.info(f"Analyzing {len(pairs_to_analyze)} character pairs")
            
            # Analyze each pair
            relationships = []
            for source, target in pairs_to_analyze:
                logger.info(f"Analyzing: {source} → {target}")
                
                result = self.analyze_relationship_by_chapters(
                    project_id=project_id,
                    workspace_id=workspace_id,
                    source_character=source,
                    target_character=target,
                    chapters=chapters_to_process,
                    model=model,
                    provider=provider
                )
                
                if result.get('success'):
                    relationships.append(result)
                    
                    # Store relationship in database
                    self._store_relationship_v2(project_id, workspace_id, result, model, provider)
                
                # Rate limiting delay between character pairs to avoid 429 errors
                # This is on top of the per-chapter delays
                time.sleep(2)  # 2 second delay between each character pair analysis
            
            logger.info("=== V2 EXTRACTION COMPLETE ===")
            logger.info(f"Relationships analyzed: {len(relationships)}")
            
            return {
                'success': True,
                'relationships': relationships,
                'total_pairs': len(pairs_to_analyze),
                'successful_pairs': len(relationships),
                'chapters_analyzed': len(chapters_to_process),
                'mode': focus_mode
            }
            
        except Exception as e:
            logger.error(f"Error in extract_relationships_v2: {e}", exc_info=True)
            return {'error': str(e), 'success': False}
    
    def _store_relationship_v2(self, project_id: str, workspace_id: str, relationship_data: Dict[str, Any], model: str = "gemini-2.5-flash", provider: str = "gemini") -> None:
        """
        Store the V2 relationship data in the database.
        
        SMART MERGE: If relationship exists with previous chapter analyses,
        merge new analyses with existing ones and re-synthesize overall score.
        """
        try:
            source = relationship_data['source']
            target = relationship_data['target']
            new_chapter_analyses = relationship_data.get('chapter_analyses', [])
            
            logger.info(f"=== STORING V2: {source} → {target}, new chapters: {len(new_chapter_analyses)} ===")
            
            # =====================================================
            # STEP 1: DIRECTLY query existing chapter_analyses from DB
            # =====================================================
            existing_chapters = []
            
            # Get vertex IDs
            source_vertex_id = self.records_manager._get_vertex_id_by_name(project_id, source)
            target_vertex_id = self.records_manager._get_vertex_id_by_name(project_id, target)
            
            if source_vertex_id and target_vertex_id:
                conn = None
                try:
                    conn = self.records_manager.db_pool.getconn()
                    with conn.cursor() as cursor:
                        # Direct query for chapter_analyses using PostgreSQL JSON operator
                        cursor.execute("""
                            SELECT properties->>'chapter_analyses' 
                            FROM novel_graph_edges 
                            WHERE project_id = %s 
                            AND source_vertex_id = %s 
                            AND target_vertex_id = %s
                            ORDER BY updated_at DESC
                            LIMIT 1
                        """, (project_id, source_vertex_id, target_vertex_id))
                        
                        result = cursor.fetchone()
                        if result and result[0]:
                            try:
                                existing_chapters = json.loads(result[0])
                                existing_ch_nums = [ch.get('chapter_number', '?') for ch in existing_chapters]
                                logger.info(f"Found {len(existing_chapters)} existing chapters: {existing_ch_nums}")
                            except (json.JSONDecodeError, TypeError) as e:
                                logger.warning(f"Could not parse existing chapter_analyses: {e}")
                                existing_chapters = []
                        else:
                            logger.info(f"No existing chapters found for {source} → {target}")
                except Exception as e:
                    logger.warning(f"Error fetching existing chapters: {e}")
                finally:
                    if conn:
                        self.records_manager.db_pool.putconn(conn)
            
            # =====================================================
            # STEP 2: Merge chapter analyses (update by chapter number, add new)
            # =====================================================
            merged_chapters = self._merge_chapter_analyses(existing_chapters, new_chapter_analyses)
            logger.info(f"Merged chapters: {len(existing_chapters)} existing + {len(new_chapter_analyses)} new = {len(merged_chapters)} total")
            
            # =====================================================
            # STEP 3: Re-synthesize overall if we have merged data
            # =====================================================
            if len(merged_chapters) > len(new_chapter_analyses):
                # We merged with existing data, need to re-synthesize
                logger.info(f"Re-synthesizing overall score from {len(merged_chapters)} merged chapters")
                overall = self._synthesize_overall_from_chapters(
                    project_id=project_id,
                    workspace_id=workspace_id,
                    source_character=source,
                    target_character=target,
                    chapter_analyses=merged_chapters,
                    model=model,
                    provider=provider
                )
            else:
                # No existing data to merge, use the provided overall
                overall = relationship_data.get('overall', {})
            
            # =====================================================
            # STEP 4: Build properties and save
            # =====================================================
            sentiment_score = overall.get('overall_sentiment', 0)
            emotional_tone = overall.get('emotional_tone', 'neutral')
            context = overall.get('summary', '')
            progression = overall.get('progression', '')
            
            properties = {
                'sentiment_score': sentiment_score,
                'emotional_tone': emotional_tone,
                'context': context,
                'relationship_progression': progression,
                'chapter_analyses': json.dumps(merged_chapters),  # Store merged chapters
                'analysis_version': 'v2',
                'directional': True,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            relationship_type = overall.get('relationship_type', 'ACQUAINTANCE')
            
            logger.info(f"V2 Storing: {source} → {target}")
            logger.info(f"  Type: {relationship_type}, Score: {sentiment_score}, Tone: {emotional_tone}")
            logger.info(f"  Context: {context[:100]}..." if len(context) > 100 else f"  Context: {context}")
            logger.info(f"  Chapters: {len(merged_chapters)} analyses (merged)")
            
            # Upsert relationship
            edge_id = self.records_manager.upsert_relationship(
                project_id=project_id,
                source_name=source,
                target_name=target,
                relationship_type=relationship_type,
                properties=properties
            )
            
            logger.info(f"Stored V2 relationship: {source} → {target} (edge_id: {edge_id}, score: {sentiment_score}, type: {relationship_type})")
            
        except Exception as e:
            logger.error(f"Failed to store V2 relationship {relationship_data.get('source', '?')} → {relationship_data.get('target', '?')}: {e}", exc_info=True)
    
    def _get_existing_relationship(self, project_id: str, source: str, target: str) -> Optional[Dict[str, Any]]:
        """
        Get existing relationship between source and target if it exists.
        
        Uses PostgreSQL metadata table for reliable retrieval of large JSON properties
        like chapter_analyses (AGE has issues with large escaped JSON).
        
        Returns:
            Relationship dict with properties including chapter_analyses, or None if not found
        """
        try:
            logger.info(f"Looking up existing relationship: {source} → {target} in project {project_id}")
            
            # Use metadata table for reliable chapter_analyses retrieval
            rel = self.records_manager.get_relationship_metadata_by_names(project_id, source, target)
            
            if rel:
                logger.info(f"Found existing relationship: {source} → {target}")
                props = rel.get('properties', {})
                
                if not props:
                    logger.warning("Relationship found but properties is empty/None")
                    return rel
                
                logger.debug(f"Properties keys: {list(props.keys())}")
                
                # Get chapter_analyses - could be string (JSON) or already parsed list
                chapter_analyses_raw = props.get('chapter_analyses')
                
                if chapter_analyses_raw is None:
                    logger.warning("chapter_analyses key not found in properties")
                    logger.info("Found existing relationship with 0 chapter analyses")
                    return rel
                
                # Parse chapter_analyses
                try:
                    if isinstance(chapter_analyses_raw, str):
                        if chapter_analyses_raw.strip() == '' or chapter_analyses_raw.strip() == '[]':
                            chapters = []
                        else:
                            chapters = json.loads(chapter_analyses_raw)
                    elif isinstance(chapter_analyses_raw, list):
                        chapters = chapter_analyses_raw
                    else:
                        logger.warning(f"Unexpected chapter_analyses type: {type(chapter_analyses_raw)}")
                        chapters = []
                    
                    logger.info(f"Found existing relationship with {len(chapters)} chapter analyses")
                    
                    # Log chapter numbers for debugging
                    if chapters:
                        chapter_nums = [ch.get('chapter_number', ch.get('chapter_order', '?')) for ch in chapters]
                        logger.debug(f"Existing chapter numbers: {chapter_nums}")
                        
                except json.JSONDecodeError as parse_err:
                    logger.error(f"JSON decode error for chapter_analyses: {parse_err}")
                    logger.debug(f"Raw chapter_analyses value: {str(chapter_analyses_raw)[:200]}...")
                    logger.info("Found existing relationship with 0 chapter analyses (parse error)")
                except Exception as parse_err:
                    logger.error(f"Unexpected error parsing chapter_analyses: {parse_err}", exc_info=True)
                    logger.info("Found existing relationship with 0 chapter analyses (error)")
                    
                return rel
            else:
                logger.info(f"No existing relationship found for {source} → {target}")
            
            return None
        except Exception as e:
            logger.error(f"Error getting existing relationship: {e}", exc_info=True)
            return None
    
    def _merge_chapter_analyses(
        self, 
        existing_chapters: List[Dict[str, Any]], 
        new_chapters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge new chapter analyses with existing ones.
        
        Rules:
        - If same chapter_number exists, REPLACE with new analysis
        - If new chapter_number, ADD to the list
        - Sort by chapter_number
        
        Returns:
            Merged list of chapter analyses
        """
        # Build lookup by chapter number
        merged = {}
        
        # Add existing chapters
        for ch in existing_chapters:
            chapter_num = ch.get('chapter_number', ch.get('chapter_order', 0))
            merged[chapter_num] = ch
        
        # Add/replace with new chapters
        for ch in new_chapters:
            chapter_num = ch.get('chapter_number', ch.get('chapter_order', 0))
            merged[chapter_num] = ch
            logger.debug(f"{'Replaced' if chapter_num in merged else 'Added'} chapter {chapter_num}")
        
        # Sort by chapter number and return as list
        sorted_chapters = sorted(merged.values(), key=lambda x: x.get('chapter_number', x.get('chapter_order', 0)))
        return sorted_chapters
    
    def _synthesize_overall_from_chapters(
        self,
        project_id: str,
        workspace_id: str,
        source_character: str,
        target_character: str,
        chapter_analyses: List[Dict[str, Any]],
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Re-synthesize overall relationship assessment from ALL chapter analyses.
        
        This is called when merging new chapter data with existing to ensure
        the overall score/tone/type reflects ALL chapters, not just the new ones.
        
        Returns:
            Overall assessment dict with overall_sentiment, relationship_type, emotional_tone, summary, progression
        """
        if not chapter_analyses:
            return {
                'overall_sentiment': 0,
                'relationship_type': 'ACQUAINTANCE',
                'emotional_tone': 'neutral',
                'summary': 'No chapter analyses available',
                'progression': ''
            }
        
        # Try AI synthesis first
        try:
            # Use the existing synthesis method
            overall = self._synthesize_overall_relationship(
                project_id=project_id,
                workspace_id=workspace_id,
                source_character=source_character,
                target_character=target_character,
                chapter_analyses=chapter_analyses,
                model=model,
                provider=provider
            )
            if overall:
                return overall
        except Exception as e:
            logger.warning(f"AI synthesis failed during merge, using fallback: {e}")
        
        # Fallback: Calculate from chapter data
        scores = [ch.get('sentiment_score', 0) for ch in chapter_analyses]
        avg_score = sum(scores) // len(scores) if scores else 0
        
        # Get most recent chapter's type/tone as fallback
        latest_chapter = max(chapter_analyses, key=lambda x: x.get('chapter_number', 0))
        
        return {
            'overall_sentiment': avg_score,
            'relationship_type': latest_chapter.get('relationship_type', 'ACQUAINTANCE'),
            'emotional_tone': latest_chapter.get('emotional_tone', 'neutral'),
            'summary': f"Relationship based on {len(chapter_analyses)} chapter analyses (average score: {avg_score})",
            'progression': f"From Chapter 1 to Chapter {latest_chapter.get('chapter_number', len(chapter_analyses))}"
        }

    # =========================================================================
    # LEGACY RELATIONSHIP EXTRACTION (kept for backward compatibility)
    # =========================================================================
    
    def _get_relationship_extraction_prompt(self) -> str:
        """Get the AI prompt for extracting relationships from manuscript (legacy - combined chapters)."""
        return """You are a literary relationship analyst. Extract ALL character relationships from the provided manuscript content.

For each relationship, identify:
1. The two characters involved (source and target)
2. The type of relationship (use standardized types like LOVES, HATES, TRUSTS, FEARS, PROTECTS, MENTORS, RIVALS, ALLIED_WITH, etc.)
3. The emotional tone of the relationship
4. A detailed context explaining the relationship
5. Direct text evidence (actual quotes from the manuscript that demonstrate this relationship)

MANUSCRIPT CONTENT:
{manuscript_content}

{character_context}

IMPORTANT GUIDELINES:
- Only extract relationships between NAMED characters
- Include BOTH directions if the relationship is mutual or different in each direction (e.g., A loves B, B respects A)
- Be specific about relationship types - use nuanced types like MENTORS, PROTECTS, BETRAYS rather than generic INTERACTS_WITH
- Provide actual TEXT EVIDENCE - short quotes from the manuscript that demonstrate the relationship
- The emotional_tone should be one of: hostile, antagonistic, cold, neutral, professional, cordial, friendly, warm, affectionate, romantic, familial, devoted

OUTPUT FORMAT (JSON):
{{
  "relationships": [
    {{
      "source": "Character A Name",
      "target": "Character B Name",
      "relationship_type": "RELATIONSHIP_TYPE",
      "emotional_tone": "emotional_tone_value",
      "context": "Detailed description of how these characters relate to each other, their history, and current dynamic",
      "text_evidence": [
        {{"quote": "Actual quote from manuscript...", "location": "Chapter X"}},
        {{"quote": "Another supporting quote...", "location": "Chapter Y"}}
      ]
    }}
  ]
}}

Extract all significant relationships:"""

    def _get_single_character_prompt(self) -> str:
        """Get focused prompt for extracting interactions for ONE specific character."""
        return """Extract up to 10 interactions involving {character_name} in this chapter.

CHAPTER: {chapter_name}
CONTENT:
{chapter_content}

KNOWN CHARACTERS (use EXACT names):
{known_characters}

INTERACTION TYPE - USE ONLY ONE OF THESE EXACT WORDS:
WARNS, THANKS, MOCKS, PROTECTS, COMFORTS, ARGUES, SUPPORTS, QUESTIONS, REASSURES, TEASES, IGNORES, THREATENS, HELPS, CRITICIZES, AGREES, DISAGREES, TRUSTS, DOUBTS

SENTIMENT SCORE (-100 to +100):
- Friendly/supportive: +20 to +60
- Hostile/negative: -20 to -60  
- Neutral: -10 to +10
- Avoid +100 or -100 unless truly extreme

RULES:
- Both characters MUST be from the KNOWN CHARACTERS list
- Quote actual text for evidence (30+ chars)
- Only meaningful interactions, skip trivial ones

Return JSON only:
{{"interactions": [{{
  "source_character": "exact name from list",
  "target_character": "exact name from list",
  "interaction_type": "ONE WORD from list above",
  "sentiment_score": <number>,
  "sentiment_reasoning": "brief explanation",
  "context": "what happens",
  "text_evidence": "quote from text"
}}]}}"""
    
    def _get_1to1_prompt(self) -> str:
        """Get focused prompt for extracting interactions ONLY between two specific characters."""
        return """Extract interactions between "{character_1}" and "{character_2}" in this chapter.

RULES:
- ONLY these two characters - ignore everyone else
- source_character and target_character MUST be exactly "{character_1}" or "{character_2}"

CHAPTER: {chapter_name}
CONTENT:
{chapter_content}

INTERACTION TYPE - USE ONLY ONE OF THESE EXACT WORDS:
WARNS, THANKS, MOCKS, PROTECTS, COMFORTS, ARGUES, SUPPORTS, QUESTIONS, REASSURES, TEASES, IGNORES, THREATENS, HELPS, CRITICIZES, AGREES, DISAGREES, TRUSTS, DOUBTS

SENTIMENT SCORE (-100 to +100):
- Friendly/supportive action: +20 to +60
- Hostile/negative action: -20 to -60
- Neutral exchange: -10 to +10
- Avoid extremes like +100 or -100 unless truly extreme (betrayal, saving life)

Return JSON only:
{{"interactions": [{{
  "source_character": "exact name",
  "target_character": "exact name",
  "interaction_type": "ONE WORD from list above",
  "sentiment_score": <number>,
  "sentiment_reasoning": "brief explanation",
  "context": "what happens",
  "text_evidence": "quote from text"
}}]}}"""
    
    def get_chapters(self, project_id: str, workspace_id: str = None) -> List[Dict[str, Any]]:
        """
        Get chapters for a project using direct database access.

        Args:
            project_id: Project UUID
            workspace_id: Optional workspace ID (kept for API compatibility, not used)

        Returns:
            List of chapter dictionaries with order, chapter_name, content
        """
        # Direct database query - fetches chapters from project_content table
        conn = None
        try:
            conn = self.db_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT content FROM project_content 
                    WHERE project_id = %s
                """, (project_id,))
                
                result = cursor.fetchone()
                if not result or not result[0]:
                    logger.warning(f"No project_content found for project {project_id}")
                    return []
                
                chapters = result[0]
                if isinstance(chapters, str):
                    chapters = json.loads(chapters)
                
                if not isinstance(chapters, list):
                    logger.warning(f"Invalid chapters format for project {project_id}")
                    return []
                
                # Enrich chapters with order and content
                enriched_chapters = []
                for chapter in chapters:
                    chapter_order = chapter.get('order')
                    chapter_name = chapter.get('chapter_name', f"Chapter {chapter_order}")
                    chapter_content = chapter.get('content', '')
                    
                    enriched_chapters.append({
                        'order': chapter_order,
                        'chapter_name': chapter_name,
                        'content': chapter_content
                    })
                
                logger.info(f"Retrieved {len(enriched_chapters)} chapters from project_content")
                return enriched_chapters
                
        except Exception as e:
            logger.error(f"Failed to get chapters: {e}")
            return []
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_existing_characters(self, project_id: str) -> List[Dict[str, Any]]:
        """Get existing character entities for context."""
        try:
            # Use lowercase 'character' - this is how entity types are stored in metadata
            entities = self.records_manager.get_project_entities(
                project_id=project_id,
                entity_type="character"
            )
            return entities
        except Exception as e:
            logger.warning(f"Could not get existing characters: {e}")
            return []
    
    def extract_relationships(
        self,
        project_id: str,
        workspace_id: str,
        character_ids: Optional[List[str]] = None,  # None = all characters
        chapter_orders: Optional[List[int]] = None,  # None = all chapters
        model: str = "gemini-2.5-flash",
        provider: str = "gemini",
        focus_mode: str = "all"  # 'all', 'selected', or '1-to-1'
    ) -> Dict[str, Any]:
        """
        Extract relationships using ONE CHARACTER AT A TIME approach.
        
        DECONSTRUCTOR PATTERN: Process each character individually to keep
        AI responses small and parseable. This prevents token limit issues.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID
            character_ids: Optional list of character vertex IDs to focus on (None = all)
            chapter_orders: Optional list of chapter orders to analyze (None = all)
            model: AI model to use
            provider: AI provider
            focus_mode: 'all' (all characters), 'selected' (specific set), or '1-to-1' (exactly 2 characters, only their mutual interactions)
            
        Returns:
            Dictionary with extracted interactions, aggregated relationships, and processing info
        """
        try:
            # Get chapters
            all_chapters = self.get_chapters(project_id, workspace_id)
            
            if not all_chapters:
                return {'error': 'No chapters found for this project'}
            
            # Filter chapters if specific ones requested
            chapters_to_process = all_chapters
            if chapter_orders is not None:
                chapters_to_process = [
                    ch for ch in all_chapters 
                    if ch.get('order') in chapter_orders
                ]
            
            if not chapters_to_process:
                return {'error': 'No chapters match the specified orders'}
            
            # Get existing characters
            existing_characters = self.get_existing_characters(project_id)
            
            if not existing_characters:
                return {'error': 'No characters found in this project. Extract entities first.'}
            
            # Determine which characters to process
            characters_to_process = []
            if character_ids:
                # User selected specific characters
                for c in existing_characters:
                    if str(c.get('vertex_id')) in [str(id) for id in character_ids] and c.get('name'):
                        characters_to_process.append(c.get('name'))
            else:
                # All characters
                characters_to_process = [c.get('name') for c in existing_characters if c.get('name')]
            
            if not characters_to_process:
                return {'error': 'No valid characters to analyze'}
            
            # Validate 1-to-1 mode has exactly 2 characters after resolution
            if focus_mode == '1-to-1' and len(characters_to_process) != 2:
                logger.error(f"1-to-1 mode requires exactly 2 characters but got {len(characters_to_process)}: {characters_to_process}")
                return {'error': f'1-to-1 mode requires exactly 2 characters. Found: {len(characters_to_process)}. Check that both selected characters exist.'}
            
            logger.info("=== EXTRACTION START ===")
            logger.info(f"Focus mode: {focus_mode}")
            logger.info(f"Processing {len(characters_to_process)} characters across {len(chapters_to_process)} chapters")
            logger.info(f"Characters: {characters_to_process}")
            
            all_interactions = []
            chapter_results = []
            seen_interactions = set()  # Avoid duplicates
            
            # ============================================================
            # 1-TO-1 MODE: Use dedicated prompt for just the two characters
            # ============================================================
            if focus_mode == '1-to-1' and len(characters_to_process) == 2:
                char1 = characters_to_process[0]
                char2 = characters_to_process[1]
                logger.info(f"=== 1-TO-1 MODE: Extracting ONLY {char1} <-> {char2} ===")
                
                for chapter in chapters_to_process:
                    # Always convert 0-indexed order to 1-indexed chapter number
                    raw_order = chapter.get('order', 0)
                    chapter_number = raw_order + 1
                    chapter_name = chapter.get('chapter_name', f"Chapter {chapter_number}")
                    chapter_content = chapter.get('content', '')
                    
                    if not chapter_content or not chapter_content.strip():
                        chapter_results.append({
                            'chapter': chapter_name,
                            'chapter_number': chapter_number,
                            'status': 'skipped',
                            'reason': 'empty content'
                        })
                        continue
                    
                    # Use the dedicated 1-to-1 prompt
                    result = self._extract_1to1_interactions(
                        project_id=project_id,
                        workspace_id=workspace_id,
                        character_1=char1,
                        character_2=char2,
                        chapter_name=chapter_name,
                        chapter_number=chapter_number,
                        chapter_content=chapter_content,
                        model=model,
                        provider=provider
                    )
                    
                    chapter_interaction_count = 0
                    if result.get('interactions'):
                        for interaction in result['interactions']:
                            key = (
                                interaction.get('source_character', '').lower(),
                                interaction.get('target_character', '').lower(),
                                chapter_number,
                                interaction.get('interaction_type', '')
                            )
                            if key not in seen_interactions:
                                seen_interactions.add(key)
                                all_interactions.append(interaction)
                                chapter_interaction_count += 1
                    
                    chapter_results.append({
                        'chapter': chapter_name,
                        'chapter_number': chapter_number,
                        'status': 'success',
                        'interactions_found': chapter_interaction_count,
                        'interactions_stored': chapter_interaction_count
                    })
                    logger.info(f"Chapter {chapter_number}: Found {chapter_interaction_count} interactions between {char1} <-> {char2}")
            
            # ============================================================
            # ALL/SELECTED MODE: DECONSTRUCTOR PATTERN - One character at a time
            # ============================================================
            else:
                logger.info("=== DECONSTRUCTOR PATTERN ===")
                character_results = []
                
                for character_name in characters_to_process:
                    logger.info(f"--- Processing character: {character_name} ---")
                    character_interactions = []
                    
                    for chapter in chapters_to_process:
                        # Always convert 0-indexed order to 1-indexed chapter number
                        raw_order = chapter.get('order', 0)
                        chapter_number = raw_order + 1
                        chapter_name = chapter.get('chapter_name', f"Chapter {chapter_number}")
                        chapter_content = chapter.get('content', '')
                        
                        if not chapter_content or not chapter_content.strip():
                            continue
                        
                        # Get all character names for AI context
                        all_character_names = [c.get('name') for c in existing_characters if c.get('name')]
                        
                        result = self._extract_single_character_interactions(
                            project_id=project_id,
                            workspace_id=workspace_id,
                            character_name=character_name,
                            chapter_name=chapter_name,
                            chapter_number=chapter_number,
                            chapter_content=chapter_content,
                            model=model,
                            provider=provider,
                            known_characters=all_character_names
                        )
                        
                        if result.get('interactions'):
                            for interaction in result['interactions']:
                                key = (
                                    interaction.get('source_character', '').lower(),
                                    interaction.get('target_character', '').lower(),
                                    chapter_number,
                                    interaction.get('interaction_type', '')
                                )
                                if key not in seen_interactions:
                                    seen_interactions.add(key)
                                    character_interactions.append(interaction)
                    
                    all_interactions.extend(character_interactions)
                    character_results.append({
                        'character': character_name,
                        'interactions_found': len(character_interactions)
                    })
                    logger.info(f"Found {len(character_interactions)} interactions for {character_name}")
            
            # Aggregate interactions into relationships
            aggregated_relationships = self._aggregate_interactions_to_relationships(
                project_id=project_id,
                interactions=all_interactions,
                focus_mode=focus_mode,
                focused_characters=characters_to_process if focus_mode == '1-to-1' else None
            )
            
            logger.info("=== EXTRACTION COMPLETE ===")
            logger.info(f"Total interactions: {len(all_interactions)}")
            logger.info(f"Relationships built: {len(aggregated_relationships)}")
            
            # Return results - use chapter_results for 1-to-1 mode, character_results for others
            return {
                'success': True,
                'characters_processed': len(characters_to_process),
                'chapter_results': chapter_results if focus_mode == '1-to-1' else None,
                'character_results': character_results if focus_mode != '1-to-1' else None,
                'total_interactions': len(all_interactions),
                'interactions': all_interactions,
                'relationships': aggregated_relationships,
                'model_used': model
            }
            
        except Exception as e:
            logger.error(f"Error in extract_relationships: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _extract_single_character_interactions(
        self,
        project_id: str,
        workspace_id: str,
        character_name: str,
        chapter_name: str,
        chapter_number: int,
        chapter_content: str,
        model: str,
        provider: str,
        known_characters: List[str] = None
    ) -> Dict[str, Any]:
        """
        Extract interactions for ONE SPECIFIC CHARACTER from one chapter.
        
        This is the DECONSTRUCTOR approach - small focused requests = reliable parsing.
        """
        try:
            caller = self._create_caller(project_id, workspace_id)
            engine = self._get_generation_engine(model, provider, caller)
            
            # Format known characters list for prompt
            known_chars_str = ", ".join(known_characters) if known_characters else "Unknown"
            
            # Use the focused single-character prompt
            prompt = self._get_single_character_prompt().format(
                character_name=character_name,
                chapter_name=chapter_name,
                chapter_content=chapter_content[:15000],  # Limit content per request
                known_characters=known_chars_str
            )
            
            engine.request.prompt = prompt
            engine.request.instruction = f"Extract interactions for {character_name}. Return JSON only."
            
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                logger.warning(f"AI failed for {character_name} in {chapter_name}: {response.error_message}")
                return {'interactions': []}
            
            # Simple, aggressive JSON extraction
            response_text = response.text.strip()
            
            # Remove markdown
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            
            # Fix encoding issues
            response_text = response_text.replace('"', '"').replace('"', '"')
            response_text = response_text.replace(''', "'").replace(''', "'")
            response_text = re.sub(r'ΓÇ[£¥öô]', '"', response_text)
            response_text = re.sub(r'ΓÇÖ', "'", response_text)
            
            # Find JSON - try object first, then array
            json_text = None
            interactions_data = []
            
            # Try to find object format {"interactions": [...]}
            obj_match = re.search(r'\{[\s\S]*"interactions"[\s\S]*\}', response_text)
            # Try to find array format [{...}, {...}]
            arr_match = re.search(r'\[[\s\S]*\]', response_text)
            
            if obj_match:
                json_text = obj_match.group()
            elif arr_match:
                # AI returned array directly - wrap it
                json_text = '{"interactions": ' + arr_match.group() + '}'
                logger.info(f"Converted array format to object format for {character_name}")
            
            # Handle truncated/missing JSON - try to salvage
            if not json_text:
                logger.warning(f"No JSON found for {character_name} in {chapter_name}")
                return {'interactions': []}
            
            # Check for truncation (unbalanced braces)
            if json_text.count('{') != json_text.count('}'):
                logger.warning(f"Truncated JSON for {character_name} in {chapter_name}, attempting salvage")
                # Find last complete interaction object
                last_complete = json_text.rfind('},')
                if last_complete > 0:
                    json_text = json_text[:last_complete + 1] + ']}'
                    logger.info(f"Salvaged truncated JSON for {character_name}")
            
            # Try to parse
            try:
                parsed = json.loads(json_text)
                # Handle both formats: {"interactions": [...]} or direct list
                if isinstance(parsed, list):
                    interactions_data = parsed
                else:
                    interactions_data = parsed.get('interactions', [])
                logger.info(f"Parsed {len(interactions_data)} interactions for {character_name} from {chapter_name}")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed for {character_name}: {e}, trying salvage")
                # Try to find last complete interaction and rebuild
                last_complete = json_text.rfind('},')
                if last_complete > 0:
                    salvaged = json_text[:last_complete + 1] + ']}'
                    try:
                        parsed = json.loads(salvaged)
                        if isinstance(parsed, list):
                            interactions_data = parsed
                        else:
                            interactions_data = parsed.get('interactions', [])
                        logger.info(f"Salvaged {len(interactions_data)} interactions after truncation repair")
                    except json.JSONDecodeError:
                        # Final fallback to JSONResponseParser
                        parsed, _ = JSONResponseParser.parse_response(json_text, "dict", {})
                        interactions_data = parsed.get('interactions', []) if isinstance(parsed, dict) else parsed
                else:
                    # Final fallback to JSONResponseParser  
                    parsed, _ = JSONResponseParser.parse_response(json_text, "dict", {})
                    interactions_data = parsed.get('interactions', []) if isinstance(parsed, dict) else parsed
            
            # Process interactions with quality validation
            processed = []
            known_chars_lower = [c.lower().strip() for c in known_characters] if known_characters else []
            
            for i in interactions_data:
                source = i.get('source_character', '').strip()
                target = i.get('target_character', '').strip()
                
                if not source or not target:
                    continue
                
                # QUALITY GATE 1: Validate characters are from known list
                if known_chars_lower:
                    source_valid = any(source.lower() in kc or kc in source.lower() for kc in known_chars_lower)
                    target_valid = any(target.lower() in kc or kc in target.lower() for kc in known_chars_lower)
                    if not source_valid or not target_valid:
                        logger.debug(f"Skipping interaction - characters not in known list: {source} -> {target}")
                        continue
                
                # QUALITY GATE 2: Require substantial text evidence
                text_evidence = i.get('text_evidence', '').strip()
                if len(text_evidence) < 20:
                    logger.debug(f"Skipping interaction - evidence too short ({len(text_evidence)} chars): {source} -> {target}")
                    continue
                
                # USE AI-PROVIDED SENTIMENT SCORE DIRECTLY (new approach)
                # Fall back to formula-based calculation only if AI didn't provide a score
                ai_sentiment = i.get('sentiment_score')
                ai_reasoning = i.get('sentiment_reasoning', '')
                
                if ai_sentiment is not None:
                    # Use AI's direct assessment - it understands context better
                    try:
                        sentiment = int(ai_sentiment)
                        sentiment = max(-100, min(100, sentiment))  # Clamp to valid range
                        reasons = [ai_reasoning] if ai_reasoning else [f"AI scored: {sentiment}"]
                    except (ValueError, TypeError):
                        # AI returned invalid score, fall back to formula
                        sentiment, reasons = self.calculate_sentiment_score(
                            emotional_tone=i.get('emotional_tone', 'neutral'),
                            context=i.get('context', ''),
                            relationship_type=i.get('interaction_type', '')
                        )
                else:
                    # Legacy: Calculate sentiment using formula (backward compatibility)
                    sentiment, reasons = self.calculate_sentiment_score(
                        emotional_tone=i.get('emotional_tone', 'neutral'),
                        context=i.get('context', ''),
                        relationship_type=i.get('interaction_type', '')
                    )
                
                # Derive emotional_tone from sentiment if not provided
                emotional_tone = i.get('emotional_tone', '')
                if not emotional_tone:
                    emotional_tone = self._sentiment_to_tone(sentiment)
                
                interaction = {
                    'source_character': source,
                    'target_character': target,
                    'chapter_number': chapter_number,
                    'chapter_name': chapter_name,
                    'interaction_type': i.get('interaction_type', 'INTERACTS').upper(),
                    'emotional_tone': emotional_tone,
                    'sentiment_modifier': sentiment,
                    'sentiment_reasoning': ai_reasoning,
                    'context': i.get('context', ''),
                    'text_evidence': text_evidence[:200]  # Limit evidence length
                }
                
                # Try to store in graph
                try:
                    vertex_id = self.records_manager.create_interaction(
                        project_id=project_id,
                        source_character=source,
                        target_character=target,
                        chapter_number=chapter_number,
                        chapter_name=chapter_name,
                        interaction_type=interaction['interaction_type'],
                        emotional_tone=interaction['emotional_tone'],
                        sentiment_modifier=sentiment,
                        context=interaction['context'],
                        text_evidence=interaction['text_evidence'],
                        properties={
                            'sentiment_reasons': reasons,
                            'sentiment_reasoning': ai_reasoning,
                            'ai_scored': ai_sentiment is not None
                        }
                    )
                    interaction['vertex_id'] = vertex_id
                except Exception as e:
                    logger.warning(f"Could not store interaction: {e}")
                
                processed.append(interaction)
            
            logger.info(f"Extracted {len(processed)} interactions for {character_name} from {chapter_name}")
            return {'interactions': processed}
            
        except Exception as e:
            logger.error(f"Error extracting for {character_name}: {e}")
            return {'interactions': []}
    
    def _extract_1to1_interactions(
        self,
        project_id: str,
        workspace_id: str,
        character_1: str,
        character_2: str,
        chapter_name: str,
        chapter_number: int,
        chapter_content: str,
        model: str,
        provider: str
    ) -> Dict[str, Any]:
        """
        Extract interactions ONLY between two specific characters from one chapter.
        
        This is the SIMPLE 1-TO-1 approach - tell the AI exactly what we want.
        No post-processing filtering needed!
        """
        try:
            caller = self._create_caller(project_id, workspace_id)
            engine = self._get_generation_engine(model, provider, caller)
            
            # Use the dedicated 1-to-1 prompt
            prompt = self._get_1to1_prompt().format(
                character_1=character_1,
                character_2=character_2,
                chapter_name=chapter_name,
                chapter_content=chapter_content[:15000]  # Limit content per request
            )
            
            engine.request.prompt = prompt
            engine.request.instruction = f"Extract interactions ONLY between {character_1} and {character_2}. Return JSON only."
            
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                logger.warning(f"AI failed for 1-to-1 ({character_1} <-> {character_2}) in {chapter_name}: {response.error_message}")
                return {'interactions': []}
            
            # Simple, aggressive JSON extraction
            response_text = response.text.strip()
            
            # Remove markdown
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            
            # Fix encoding issues
            response_text = response_text.replace('"', '"').replace('"', '"')
            response_text = response_text.replace(''', "'").replace(''', "'")
            response_text = re.sub(r'ΓÇ[£¥öô]', '"', response_text)
            response_text = re.sub(r'ΓÇÖ', "'", response_text)
            
            # Find JSON
            json_text = None
            interactions_data = []
            
            obj_match = re.search(r'\{[\s\S]*"interactions"[\s\S]*\}', response_text)
            arr_match = re.search(r'\[[\s\S]*\]', response_text)
            
            if obj_match:
                json_text = obj_match.group()
            elif arr_match:
                json_text = '{"interactions": ' + arr_match.group() + '}'
            
            if not json_text:
                logger.warning(f"No JSON found for 1-to-1 ({character_1} <-> {character_2}) in {chapter_name}")
                return {'interactions': []}
            
            # Handle truncated JSON
            if json_text.count('{') != json_text.count('}'):
                last_complete = json_text.rfind('},')
                if last_complete > 0:
                    json_text = json_text[:last_complete + 1] + ']}'
            
            # Parse JSON
            try:
                parsed = json.loads(json_text)
                if isinstance(parsed, list):
                    interactions_data = parsed
                else:
                    interactions_data = parsed.get('interactions', [])
                logger.info(f"Parsed {len(interactions_data)} 1-to-1 interactions from {chapter_name}")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed for 1-to-1: {e}")
                return {'interactions': []}
            
            # Process and store interactions with STRICT 1-to-1 validation
            processed = []
            char1_lower = character_1.lower().strip()
            char2_lower = character_2.lower().strip()
            
            # STRICTER matching - only exact match or contained match, no first-word matching
            def strict_matches_char(name, char_full):
                """Strict character matching - avoids false positives like 'Akheatoon guards' matching 'Akheatoon King'"""
                name_lower = name.lower().strip()
                return (name_lower == char_full or 
                        char_full == name_lower or
                        (len(char_full) > 3 and char_full in name_lower) or
                        (len(name_lower) > 3 and name_lower in char_full))
            
            for i in interactions_data:
                source = i.get('source_character', '').strip()
                target = i.get('target_character', '').strip()
                
                if not source or not target:
                    continue
                
                # STRICT validation: BOTH must be exactly our two characters
                src_is_char1 = strict_matches_char(source, char1_lower)
                src_is_char2 = strict_matches_char(source, char2_lower)
                tgt_is_char1 = strict_matches_char(target, char1_lower)
                tgt_is_char2 = strict_matches_char(target, char2_lower)
                
                # Only include if it's char1->char2 or char2->char1 (no other combinations)
                if not ((src_is_char1 and tgt_is_char2) or (src_is_char2 and tgt_is_char1)):
                    logger.debug(f"1-to-1 STRICT validation rejected: {source} -> {target}")
                    continue
                
                # QUALITY GATE: Require substantial text evidence
                text_evidence = i.get('text_evidence', '').strip()
                if len(text_evidence) < 20:
                    logger.debug(f"1-to-1 skipping - evidence too short ({len(text_evidence)} chars)")
                    continue
                
                # USE AI-PROVIDED SENTIMENT SCORE DIRECTLY
                ai_sentiment = i.get('sentiment_score')
                ai_reasoning = i.get('sentiment_reasoning', '')
                
                if ai_sentiment is not None:
                    try:
                        sentiment = int(ai_sentiment)
                        sentiment = max(-100, min(100, sentiment))
                        reasons = [ai_reasoning] if ai_reasoning else [f"AI scored: {sentiment}"]
                    except (ValueError, TypeError):
                        sentiment, reasons = self.calculate_sentiment_score(
                            emotional_tone=i.get('emotional_tone', 'neutral'),
                            context=i.get('context', ''),
                            relationship_type=i.get('interaction_type', '')
                        )
                else:
                    sentiment, reasons = self.calculate_sentiment_score(
                        emotional_tone=i.get('emotional_tone', 'neutral'),
                        context=i.get('context', ''),
                        relationship_type=i.get('interaction_type', '')
                    )
                
                # Derive emotional_tone from sentiment if not provided
                emotional_tone = i.get('emotional_tone', '')
                if not emotional_tone:
                    emotional_tone = self._sentiment_to_tone(sentiment)
                
                interaction = {
                    'source_character': source,
                    'target_character': target,
                    'chapter_number': chapter_number,
                    'chapter_name': chapter_name,
                    'interaction_type': i.get('interaction_type', 'INTERACTS').upper(),
                    'emotional_tone': emotional_tone,
                    'sentiment_modifier': sentiment,
                    'sentiment_reasoning': ai_reasoning,
                    'context': i.get('context', ''),
                    'text_evidence': text_evidence[:200]
                }
                
                # Store in graph database
                try:
                    vertex_id = self.records_manager.create_interaction(
                        project_id=project_id,
                        source_character=source,
                        target_character=target,
                        chapter_number=chapter_number,
                        chapter_name=chapter_name,
                        interaction_type=interaction['interaction_type'],
                        emotional_tone=interaction['emotional_tone'],
                        sentiment_modifier=sentiment,
                        context=interaction['context'],
                        text_evidence=interaction['text_evidence'],
                        properties={
                            'sentiment_reasons': reasons,
                            'sentiment_reasoning': ai_reasoning,
                            'ai_scored': ai_sentiment is not None
                        }
                    )
                    interaction['vertex_id'] = vertex_id
                except Exception as e:
                    logger.warning(f"Could not store 1-to-1 interaction: {e}")
                
                processed.append(interaction)
            
            logger.info(f"1-to-1 extracted {len(processed)} interactions between {character_1} <-> {character_2} from {chapter_name}")
            return {'interactions': processed}
            
        except Exception as e:
            logger.error(f"Error in 1-to-1 extraction ({character_1} <-> {character_2}): {e}")
            return {'interactions': []}

    def _extract_chapter_interactions(
        self,
        project_id: str,
        workspace_id: str,
        chapter_name: str,
        chapter_number: int,
        chapter_content: str,
        character_context: str,
        model: str,
        provider: str
    ) -> Dict[str, Any]:
        """
        LEGACY: Extract individual interactions from a single chapter.
        Kept for backward compatibility but new code uses _extract_single_character_interactions.
        
        Returns:
            Dictionary with interactions list and storage info
        """
        try:
            # Create generation engine
            caller = self._create_caller(project_id, workspace_id)
            engine = self._get_generation_engine(model, provider, caller)
            
            # Prepare prompt for this chapter
            prompt = self._get_interaction_extraction_prompt().format(
                chapter_name=chapter_name,
                chapter_content=chapter_content[:30000],  # Limit per chapter
                character_context=character_context
            )
            
            engine.request.prompt = prompt
            engine.request.instruction = "Extract character interactions from this chapter."
            
            # Generate
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                return {'error': f'AI generation failed: {response.error_message}'}
            
            # Parse response - aggressive cleaning for AI responses
            response_text = response.text
            
            # Step 1: Remove markdown code blocks
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = response_text.strip()
            
            # Step 2: Fix mojibake FIRST (before smart quotes)
            # CRITICAL: Mojibake inside JSON strings must be replaced with ESCAPED quotes
            # ΓÇ£ (left quote), ΓÇ¥ (right quote) -> \" 
            # ΓÇÖ (apostrophe) -> '
            # Common mojibake patterns from CP1252 interpreted as UTF-8
            response_text = re.sub(r'ΓÇ£', '\\"', response_text)  # Left double quote mojibake
            response_text = re.sub(r'ΓÇ¥', '\\"', response_text)  # Right double quote mojibake  
            response_text = re.sub(r'ΓÇô', '\\"', response_text)  # Another double quote variant
            response_text = re.sub(r'ΓÇö', '\\"', response_text)  # Another double quote variant
            response_text = re.sub(r'ΓÇÖ', "'", response_text)    # Apostrophe mojibake
            response_text = re.sub(r'ΓÇÿ', "'", response_text)    # Another apostrophe variant
            
            # Step 3: Fix smart quotes OUTSIDE of JSON strings (at JSON structure level)
            # These are safe to replace with unescaped quotes as they're structural
            # But to be safe, we'll handle them more carefully
            # Smart double quotes used as JSON structure delimiters -> regular quotes
            response_text = response_text.replace('"', '"').replace('"', '"')
            # Smart single quotes -> regular single quotes (apostrophes)
            response_text = response_text.replace(''', "'").replace(''', "'")
            # Other quote variants
            response_text = response_text.replace('„', '"').replace('‟', '"')
            
            # Step 4: Fix AI double-quote issues
            # AI sometimes generates: "text_evidence": "...what?"" (double quote at end)
            # This pattern: ?"" or ."" at the end of a string value should be ?" or ."
            response_text = re.sub(r'([?!.\'])""\s*([,}\]])', r'\1"\2', response_text)
            # Also fix patterns like: some text"" -> some text"
            response_text = re.sub(r'([a-zA-Z0-9])""\s*([,}\]])', r'\1"\2', response_text)
            
            # Step 5: Find JSON object
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            
            # If no complete JSON found, check if truncated (common with MAX_TOKENS)
            if not json_match:
                # Try to find start of JSON and salvage partial response
                json_start = response_text.find('{"interactions"')
                if json_start != -1:
                    json_text = response_text[json_start:]
                    logger.warning(f"Response may be truncated for {chapter_name}, attempting to salvage")
                else:
                    logger.error(f"No JSON object found in response for {chapter_name}")
                    return {'error': 'No JSON found in AI response'}
            else:
                json_text = json_match.group()
            
            # Step 6: Handle truncated JSON (if response hit MAX_TOKENS)
            # Try to close incomplete JSON by finding the last complete interaction
            if json_text.count('{') != json_text.count('}'):
                logger.warning(f"Unbalanced braces in response for {chapter_name}, attempting repair")
                # Find the last complete interaction object (ends with })
                last_complete = json_text.rfind('},')
                if last_complete > 0:
                    # Truncate to last complete interaction and close the JSON
                    json_text = json_text[:last_complete + 1] + ']}'
                    logger.info(f"Salvaged truncated response for {chapter_name}")
            
            # Step 7: Try parsing
            interactions_data = []
            try:
                parsed = json.loads(json_text)
                interactions_data = parsed.get('interactions', [])
                logger.info(f"Direct JSON parsed {len(interactions_data)} interactions from {chapter_name}")
            except json.JSONDecodeError as e:
                logger.warning(f"Direct JSON failed for {chapter_name}: {e}, trying JSONResponseParser")
                # Fallback to JSONResponseParser
                parsed, format_type = JSONResponseParser.parse_response(json_text, expected_type="dict", fallback_value={})
                interactions_data = parsed.get('interactions', [])
                logger.info(f"JSONResponseParser parsed {len(interactions_data)} interactions from {chapter_name} (format: {format_type})")
            
            if not interactions_data:
                # Last resort: try to extract interactions array directly
                interactions_match = re.search(r'"interactions"\s*:\s*\[([\s\S]*?)\](?=\s*[,}]|\s*$)', json_text)
                if interactions_match:
                    try:
                        # Wrap in proper JSON structure
                        interactions_json = '{"interactions": [' + interactions_match.group(1) + ']}'
                        parsed = json.loads(interactions_json)
                        interactions_data = parsed.get('interactions', [])
                        logger.info(f"Regex extraction got {len(interactions_data)} interactions from {chapter_name}")
                    except Exception as e:
                        logger.error(f"Regex extraction also failed for {chapter_name}: {e}")
            
            # Process and store each interaction
            processed_interactions = []
            stored_count = 0
            
            for interaction_data in interactions_data:
                source = interaction_data.get('source_character', '').strip()
                target = interaction_data.get('target_character', '').strip()
                interaction_type = interaction_data.get('interaction_type', 'INTERACTS_WITH')
                emotional_tone = interaction_data.get('emotional_tone', 'neutral')
                context = interaction_data.get('context', '')
                text_evidence = interaction_data.get('text_evidence', '')
                
                if not source or not target:
                    continue
                
                # Calculate sentiment modifier for this interaction
                sentiment_modifier, reasons = self.calculate_sentiment_score(
                    emotional_tone=emotional_tone,
                    context=context,
                    relationship_type=interaction_type
                )
                
                # Store interaction in graph database
                try:
                    vertex_id = self.records_manager.create_interaction(
                        project_id=project_id,
                        source_character=source,
                        target_character=target,
                        chapter_number=chapter_number,
                        chapter_name=chapter_name,
                        interaction_type=interaction_type,
                        emotional_tone=emotional_tone,
                        sentiment_modifier=sentiment_modifier,
                        context=context,
                        text_evidence=text_evidence,
                        properties={'sentiment_reasons': reasons}
                    )
                    
                    if vertex_id:
                        stored_count += 1
                except Exception as e:
                    logger.warning(f"Could not store interaction: {e}")
                    vertex_id = None
                
                processed_interactions.append({
                    'vertex_id': vertex_id,
                    'source_character': source,
                    'target_character': target,
                    'chapter_number': chapter_number,
                    'chapter_name': chapter_name,
                    'interaction_type': interaction_type,
                    'emotional_tone': emotional_tone,
                    'sentiment_modifier': sentiment_modifier,
                    'sentiment_reasons': reasons,
                    'context': context,
                    'text_evidence': text_evidence
                })
            
            return {
                'interactions': processed_interactions,
                'stored_count': stored_count
            }
            
        except Exception as e:
            logger.error(f"Error extracting interactions from {chapter_name}: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _match_entity_name(self, extracted_name: str, known_entities: List[str]) -> Optional[str]:
        """
        Match an extracted character name to a known entity name.
        Handles cases like "Yurak" matching "Yurak the Barbarian".
        
        Args:
            extracted_name: Name extracted from AI (e.g., "Yurak")
            known_entities: List of known entity names (e.g., ["Yurak the Barbarian", "Ericon"])
            
        Returns:
            Matched entity name or None if no match
        """
        extracted_lower = extracted_name.lower().strip()
        
        # First try exact match
        for entity in known_entities:
            if entity.lower() == extracted_lower:
                return entity
        
        # Then try: extracted name is contained in entity name
        # e.g., "Yurak" is in "Yurak the Barbarian"
        for entity in known_entities:
            if extracted_lower in entity.lower():
                return entity
        
        # Then try: entity name is contained in extracted name
        # e.g., "King" could match "The King"
        for entity in known_entities:
            entity_lower = entity.lower()
            # Only match if it's a significant portion (avoid matching single letters)
            if len(entity_lower) >= 3 and entity_lower in extracted_lower:
                return entity
        
        # NOTE: First-word matching removed - too many false positives
        # (e.g., "Akheatoon guards" should NOT match "Akheatoon King")
        
        return None
    
    def _aggregate_interactions_to_relationships(
        self,
        project_id: str,
        interactions: List[Dict[str, Any]],
        existing_entity_names: List[str] = None,
        focus_mode: str = "all",
        focused_characters: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Aggregate individual interactions into DIRECTIONAL relationship summaries.
        
        IMPORTANT: Creates SEPARATE relationships for A→B and B→A because characters
        perceive each other differently. Yurak's view of Ericon may differ from 
        Ericon's view of Yurak.
        
        Groups interactions by (source, target) direction and calculates sentiment
        for how SOURCE perceives TARGET based on their interactions.
        """
        # Get existing entity names if not provided
        if existing_entity_names is None:
            existing_entities = self.get_existing_characters(project_id)
            existing_entity_names = [e.get('name', '') for e in existing_entities if e.get('name')]
        
        logger.info(f"Known entities for relationship creation: {existing_entity_names}")
        
        # Prepare 1-to-1 filter data upfront
        focused_lower = []
        if focus_mode == '1-to-1' and focused_characters and len(focused_characters) == 2:
            focused_lower = [c.lower().strip() for c in focused_characters]
            logger.info(f"1-to-1 mode active in aggregation: only creating relationships between {focused_characters}")
        
        # Stricter helper function for 1-to-1 matching (no first-word matching)
        def is_in_focused_pair(name):
            if not focused_lower:
                return True  # Not in 1-to-1 mode, include all
            name_lower = name.lower().strip()
            
            for fc in focused_lower:
                # Exact match or contained match (but minimum length check)
                if name_lower == fc:
                    return True
                if len(fc) > 3 and (fc in name_lower or name_lower in fc):
                    return True
            return False
        
        # Group interactions by DIRECTIONAL key (source → target)
        # This creates SEPARATE sentiment tracks for A→B vs B→A
        directional_interactions = {}
        
        for interaction in interactions:
            source = interaction.get('source_character', '')
            target = interaction.get('target_character', '')
            
            if not source or not target or source == target:
                continue
            
            # DIRECTIONAL key - source's perception of target
            direction_key = (source, target)
            
            if direction_key not in directional_interactions:
                directional_interactions[direction_key] = []
            
            directional_interactions[direction_key].append(interaction)
        
        # Build DIRECTIONAL aggregated relationships
        # Each direction (A→B) gets its own relationship showing how A perceives B
        relationships = []
        
        for direction_key, direction_data in directional_interactions.items():
            source_char, target_char = direction_key
            
            # ============================================================
            # 1-TO-1 FILTER: Skip if not in focused pair
            # ============================================================
            if focus_mode == '1-to-1' and focused_lower:
                source_in_focus = is_in_focused_pair(source_char)
                target_in_focus = is_in_focused_pair(target_char)
                
                if not (source_in_focus and target_in_focus):
                    logger.debug(f"1-to-1 filter: skipping {source_char} → {target_char}")
                    continue
            
            # Calculate sentiment: How SOURCE perceives TARGET
            # This is based on interactions WHERE SOURCE acts toward TARGET
            raw_sentiment = sum(i.get('sentiment_modifier', 0) for i in direction_data)
            
            # WEIGHTED CLAMPING: Scale based on number of interactions
            # More interactions = more confidence in the final score
            # Single interactions shouldn't swing to extremes
            interaction_count = len(direction_data)
            if interaction_count == 1:
                # Single interaction: cap at ±60
                total_sentiment = max(-60, min(60, raw_sentiment))
            elif interaction_count <= 3:
                # Few interactions: cap at ±80
                total_sentiment = max(-80, min(80, raw_sentiment))
            else:
                # Many interactions: full range
                total_sentiment = max(-100, min(100, raw_sentiment))
            
            # Find dominant emotional tone
            tone_counts = {}
            for i in direction_data:
                tone = i.get('emotional_tone', 'neutral')
                tone_counts[tone] = tone_counts.get(tone, 0) + 1
            dominant_tone = max(tone_counts, key=tone_counts.get) if tone_counts else 'neutral'
            
            # Find most common interaction type
            type_counts = {}
            for i in direction_data:
                itype = i.get('interaction_type', '')
                if itype:
                    type_counts[itype] = type_counts.get(itype, 0) + 1
            dominant_type = max(type_counts, key=type_counts.get) if type_counts else 'INTERACTS_WITH'
            
            # Collect text evidence with sentiment reasoning
            all_evidence = []
            all_reasoning = []
            for i in sorted(direction_data, key=lambda x: x.get('chapter_number', 0)):
                if i.get('text_evidence'):
                    all_evidence.append({
                        'quote': i['text_evidence'],
                        'chapter': i.get('chapter_name', ''),
                        'chapter_number': i.get('chapter_number', 0),
                        'interaction_type': i.get('interaction_type', ''),
                        'sentiment_modifier': i.get('sentiment_modifier', 0),
                        'reasoning': i.get('sentiment_reasoning', '')
                    })
                if i.get('sentiment_reasoning'):
                    all_reasoning.append(i['sentiment_reasoning'])
            
            # Build context from interactions
            context_parts = []
            for i in sorted(direction_data, key=lambda x: x.get('chapter_number', 0)):
                if i.get('context'):
                    context_parts.append(f"Ch{i.get('chapter_number', '?')}: {i['context']}")
            
            # Create relationship summary (DIRECTIONAL - source → target)
            relationship = {
                'source': source_char,
                'target': target_char,
                'relationship_type': dominant_type,
                'emotional_tone': dominant_tone,
                'sentiment_score': total_sentiment,
                'raw_sentiment_total': raw_sentiment,
                'interaction_count': interaction_count,
                'context': ' | '.join(context_parts[:5]),
                'text_evidence': all_evidence[:10],
                'sentiment_reasoning': all_reasoning[:5],  # Top 5 AI reasonings
                'tone_breakdown': tone_counts,
                'type_breakdown': type_counts,
                'chapter_range': {
                    'first': min(i.get('chapter_number', 0) for i in direction_data),
                    'last': max(i.get('chapter_number', 0) for i in direction_data)
                },
                'direction': f"{source_char} → {target_char}"  # Clear direction indicator
            }
            relationships.append(relationship)
            
            # Match extracted names to actual entity names in the database
            matched_source = self._match_entity_name(source_char, existing_entity_names)
            matched_target = self._match_entity_name(target_char, existing_entity_names)
            
            # Create/Update DIRECTIONAL relationship edge in database
            if matched_source and matched_target and matched_source != matched_target:
                try:
                    rel_properties = {
                        'sentiment_score': total_sentiment,
                        'raw_sentiment_total': raw_sentiment,
                        'emotional_tone': dominant_tone,
                        'context': ' | '.join(context_parts[:3]),
                        'interaction_count': interaction_count,
                        'aggregated_from_interactions': True,
                        'directional': True,  # Flag this as directional sentiment
                        'last_updated': datetime.utcnow().isoformat()
                    }
                    
                    # Use upsert to update existing relationship or create new one
                    # NOTE: This creates DIRECTIONAL edge (source → target)
                    self.records_manager.upsert_relationship(
                        project_id=project_id,
                        source_name=matched_source,
                        target_name=matched_target,
                        relationship_type=dominant_type,
                        properties=rel_properties
                    )
                    logger.info(f"Upserted DIRECTIONAL relationship: {matched_source} → {matched_target} (sentiment: {total_sentiment})")
                except Exception as e:
                    logger.warning(f"Could not create/update relationship edge for {matched_source} → {matched_target}: {e}")
            else:
                if matched_source == matched_target:
                    logger.debug(f"Skipping self-relationship: {source_char} and {target_char} matched to same entity")
                else:
                    logger.debug(f"Skipping edge {source_char} → {target_char}: could not match to database entities")
        
        return relationships
    
    def _get_synthesis_prompt(self) -> str:
        """Get prompt for synthesizing a holistic relationship summary from interactions."""
        return """Based on these interactions, synthesize how {source_character} perceives and feels about {target_character}.

INTERACTIONS (from {source_character}'s perspective toward {target_character}):
{interactions_summary}

SYNTHESIS TASK:
1. OVERALL SENTIMENT SCORE (-100 to +100): Considering ALL interactions together, what is {source_character}'s overall feeling toward {target_character}?
   - Don't just average the scores - consider narrative weight and recent developments
   - A single betrayal might override many small positive interactions
   - Recent interactions may carry more weight than earlier ones

2. RELATIONSHIP SUMMARY: In 2-3 sentences, describe how {source_character} views {target_character}. What do they feel? Trust? Fear? Love? Respect? Resentment?

3. KEY DYNAMICS: What are the most important aspects of how {source_character} relates to {target_character}?

Return JSON only:
{{
  "overall_sentiment_score": <number -100 to +100>,
  "relationship_summary": "How source perceives and feels about target",
  "key_dynamics": ["dynamic 1", "dynamic 2"],
  "emotional_foundation": "The core emotion driving this relationship (e.g., 'protective love', 'bitter rivalry', 'cautious respect')"
}}"""
    
    def synthesize_relationship(
        self,
        project_id: str,
        workspace_id: str,
        source_character: str,
        target_character: str,
        interactions: List[Dict[str, Any]],
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Synthesize a holistic relationship summary from individual interactions.
        
        This asks AI to consider ALL interactions together and produce a meaningful
        summary of how source_character perceives target_character.
        """
        if not interactions:
            return {
                'overall_sentiment_score': 0,
                'relationship_summary': f"No recorded interactions between {source_character} and {target_character}.",
                'key_dynamics': [],
                'emotional_foundation': 'neutral'
            }
        
        try:
            # Build interactions summary for the prompt
            interactions_summary_parts = []
            for i, interaction in enumerate(interactions[:15], 1):  # Limit to 15 most relevant
                score = interaction.get('sentiment_modifier', 0)
                itype = interaction.get('interaction_type', 'interacts with')
                context = interaction.get('context', '')
                evidence = interaction.get('text_evidence', '')
                reasoning = interaction.get('sentiment_reasoning', '')
                chapter = interaction.get('chapter_number', '?')
                
                part = f"{i}. Ch{chapter}: {source_character} {itype} {target_character} (score: {score:+d})"
                if context:
                    part += f"\n   Context: {context}"
                if evidence:
                    part += f"\n   Evidence: \"{evidence}\""
                if reasoning:
                    part += f"\n   Why: {reasoning}"
                interactions_summary_parts.append(part)
            
            interactions_summary = "\n\n".join(interactions_summary_parts)
            
            # Create AI call
            caller = self._create_caller(project_id, workspace_id)
            engine = self._get_generation_engine(model, provider, caller)
            
            prompt = self._get_synthesis_prompt().format(
                source_character=source_character,
                target_character=target_character,
                interactions_summary=interactions_summary
            )
            
            engine.request.prompt = prompt
            engine.request.instruction = f"Synthesize how {source_character} perceives {target_character}. Return JSON only."
            
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                logger.warning(f"Synthesis AI call failed: {response.error_message}")
                # Fallback: return basic aggregation
                total = sum(i.get('sentiment_modifier', 0) for i in interactions)
                return {
                    'overall_sentiment_score': max(-100, min(100, total)),
                    'relationship_summary': f"Based on {len(interactions)} interactions.",
                    'key_dynamics': [],
                    'emotional_foundation': self._sentiment_to_tone(total)
                }
            
            # Parse response
            response_text = response.text.strip()
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    synthesis = json.loads(json_match.group())
                    # Validate and clamp score
                    score = synthesis.get('overall_sentiment_score', 0)
                    try:
                        score = int(score)
                        score = max(-100, min(100, score))
                    except:
                        score = 0
                    synthesis['overall_sentiment_score'] = score
                    return synthesis
                except json.JSONDecodeError:
                    pass
            
            # Fallback if parsing fails
            total = sum(i.get('sentiment_modifier', 0) for i in interactions)
            return {
                'overall_sentiment_score': max(-100, min(100, total)),
                'relationship_summary': f"Based on {len(interactions)} interactions.",
                'key_dynamics': [],
                'emotional_foundation': self._sentiment_to_tone(total)
            }
            
        except Exception as e:
            logger.error(f"Error in relationship synthesis: {e}")
            total = sum(i.get('sentiment_modifier', 0) for i in interactions)
            return {
                'overall_sentiment_score': max(-100, min(100, total)),
                'relationship_summary': f"Error during synthesis: {str(e)}",
                'key_dynamics': [],
                'emotional_foundation': 'neutral'
            }
    
    # Legacy method for backward compatibility
    def extract_relationships_legacy(
        self,
        project_id: str,
        workspace_id: str,
        character_ids: Optional[List[str]] = None,
        chapter_orders: Optional[List[int]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Legacy extraction method that combines all chapters (non-interaction-based).
        Kept for backward compatibility.
        """
        try:
            all_chapters = self.get_chapters(project_id, workspace_id)
            
            if not all_chapters:
                return {'error': 'No chapters found for this project'}
            
            chapters_to_process = all_chapters
            if chapter_orders is not None:
                chapters_to_process = [
                    ch for ch in all_chapters 
                    if ch.get('order') in chapter_orders
                ]
            
            if not chapters_to_process:
                return {'error': 'No chapters match the specified orders'}
            
            manuscript_content = ""
            for chapter in chapters_to_process:
                chapter_name = chapter.get('chapter_name', f"Chapter {chapter.get('order', '')}")
                chapter_content = chapter.get('content', '')
                if chapter_content:
                    manuscript_content += f"\n\n--- {chapter_name} ---\n{chapter_content}"
            
            if not manuscript_content.strip():
                return {'error': 'No content found in chapters'}
            
            existing_characters = self.get_existing_characters(project_id)
            character_context = ""
            
            if existing_characters:
                if character_ids:
                    existing_characters = [
                        c for c in existing_characters 
                        if str(c.get('vertex_id')) in [str(id) for id in character_ids]
                    ]
                
                if existing_characters:
                    character_names = [c.get('name', '') for c in existing_characters if c.get('name')]
                    if character_names:
                        character_context = f"\nKNOWN CHARACTERS (focus on relationships between these):\n{', '.join(character_names)}"
            
            caller = self._create_caller(project_id, workspace_id)
            engine = self._get_generation_engine(model, provider, caller)
            
            prompt = self._get_relationship_extraction_prompt().format(
                manuscript_content=manuscript_content[:50000],
                character_context=character_context
            )
            
            engine.request.prompt = prompt
            engine.request.instruction = "Extract character relationships with sentiment analysis."
            
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                return {
                    'error': f'AI generation failed: {response.error_message}',
                    'chapters_analyzed': len(chapters_to_process)
                }
            
            try:
                parsed, _ = JSONResponseParser.parse_response(response.text, expected_type="dict", fallback_value={})
                relationships_data = parsed.get('relationships', [])
            except Exception as e:
                logger.error(f"Failed to parse AI response: {e}")
                try:
                    json_match = re.search(r'\{[\s\S]*\}', response.text)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        relationships_data = parsed.get('relationships', [])
                    else:
                        return {'error': f'Could not parse AI response: {e}'}
                except:
                    return {'error': f'Could not parse AI response: {e}'}
            
            # Process relationships - calculate sentiment and store
            processed_relationships = []
            stored_count = 0
            
            for rel_data in relationships_data:
                source = rel_data.get('source', '').strip()
                target = rel_data.get('target', '').strip()
                rel_type = rel_data.get('relationship_type', 'INTERACTS_WITH')
                emotional_tone = rel_data.get('emotional_tone', 'neutral')
                context = rel_data.get('context', '')
                text_evidence = rel_data.get('text_evidence', [])
                
                if not source or not target:
                    continue
                
                # Calculate sentiment score
                sentiment_score, sentiment_reasons = self.calculate_sentiment_score(
                    emotional_tone=emotional_tone,
                    context=context,
                    relationship_type=rel_type
                )
                
                # Build relationship properties
                rel_properties = {
                    'context': context,
                    'emotional_tone': emotional_tone,
                    'sentiment_score': sentiment_score,
                    'sentiment_reasons': sentiment_reasons,
                    'text_evidence': text_evidence,
                    'extracted_at': datetime.utcnow().isoformat(),
                    'extraction_model': model
                }
                
                # Store in Apache AGE
                try:
                    edge_id = self.records_manager.create_relationship(
                        project_id=project_id,
                        source_name=source,
                        target_name=target,
                        relationship_type=rel_type,
                        properties=rel_properties
                    )
                    
                    if edge_id:
                        stored_count += 1
                        rel_properties['edge_id'] = str(edge_id)
                except Exception as e:
                    logger.warning(f"Could not store relationship {source}->{target}: {e}")
                    # Still add to results even if storage failed
                    rel_properties['storage_error'] = str(e)
                
                processed_relationships.append({
                    'source': source,
                    'target': target,
                    'relationship_type': rel_type,
                    'emotional_tone': emotional_tone,
                    'sentiment_score': sentiment_score,
                    'sentiment_reasons': sentiment_reasons,
                    'context': context,
                    'text_evidence': text_evidence,
                    'edge_id': rel_properties.get('edge_id')
                })
            
            return {
                'success': True,
                'relationships': processed_relationships,
                'total_extracted': len(processed_relationships),
                'stored_in_graph': stored_count,
                'chapters_analyzed': len(chapters_to_process),
                'character_filter': character_ids,
                'model_used': model
            }
            
        except Exception as e:
            logger.error(f"Relationship extraction failed: {e}")
            return {'error': str(e)}
    
    # =========================================================================
    # RELATIONSHIP CHANGE DETECTION
    # =========================================================================
    
    def scan_relationship_changes(
        self,
        project_id: str,
        workspace_id: str,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Scan for relationship changes by comparing stored vs current state.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID
            model: AI model to use
            provider: AI provider
            
        Returns:
            Dictionary with detected changes
        """
        try:
            # Get currently stored relationships
            stored_relationships = self.records_manager.get_project_relationships(project_id)
            
            # Extract fresh relationships from current manuscript
            extraction_result = self.extract_relationships(
                project_id=project_id,
                workspace_id=workspace_id,
                model=model,
                provider=provider
            )
            
            if 'error' in extraction_result:
                return extraction_result
            
            new_relationships = extraction_result.get('relationships', [])
            
            # Compare stored vs new
            changes = {
                'new_relationships': [],
                'modified_relationships': [],
                'potentially_removed': [],
                'unchanged': []
            }
            
            # Build lookup for stored relationships
            stored_lookup = {}
            for rel in stored_relationships:
                key = f"{rel.get('source')}|{rel.get('target')}|{rel.get('relationship_type')}"
                stored_lookup[key] = rel
            
            # Check new relationships
            new_keys = set()
            for new_rel in new_relationships:
                key = f"{new_rel.get('source')}|{new_rel.get('target')}|{new_rel.get('relationship_type')}"
                new_keys.add(key)
                
                if key in stored_lookup:
                    stored_rel = stored_lookup[key]
                    stored_props = stored_rel.get('properties', {})
                    
                    # Check for significant changes
                    old_tone = stored_props.get('emotional_tone', 'neutral')
                    new_tone = new_rel.get('emotional_tone', 'neutral')
                    old_score = stored_props.get('sentiment_score', 0)
                    new_score = new_rel.get('sentiment_score', 0)
                    
                    # Significant change if tone changed OR score changed by more than 20
                    if old_tone != new_tone or abs(old_score - new_score) > 20:
                        changes['modified_relationships'].append({
                            'source': new_rel.get('source'),
                            'target': new_rel.get('target'),
                            'relationship_type': new_rel.get('relationship_type'),
                            'old_emotional_tone': old_tone,
                            'new_emotional_tone': new_tone,
                            'old_sentiment_score': old_score,
                            'new_sentiment_score': new_score,
                            'new_context': new_rel.get('context'),
                            'edge_id': stored_rel.get('edge_id')
                        })
                    else:
                        changes['unchanged'].append({
                            'source': new_rel.get('source'),
                            'target': new_rel.get('target'),
                            'relationship_type': new_rel.get('relationship_type')
                        })
                else:
                    # New relationship not in stored
                    changes['new_relationships'].append(new_rel)
            
            # Check for removed relationships (in stored but not in new)
            for key, stored_rel in stored_lookup.items():
                if key not in new_keys:
                    changes['potentially_removed'].append({
                        'source': stored_rel.get('source'),
                        'target': stored_rel.get('target'),
                        'relationship_type': stored_rel.get('relationship_type'),
                        'edge_id': stored_rel.get('edge_id'),
                        'note': 'This relationship was not detected in the current scan - may have been removed from text or character renamed'
                    })
            
            return {
                'success': True,
                'changes': changes,
                'summary': {
                    'new_count': len(changes['new_relationships']),
                    'modified_count': len(changes['modified_relationships']),
                    'removed_count': len(changes['potentially_removed']),
                    'unchanged_count': len(changes['unchanged']),
                    'total_stored': len(stored_relationships),
                    'total_detected': len(new_relationships)
                }
            }
            
        except Exception as e:
            logger.error(f"Relationship change scan failed: {e}")
            return {'error': str(e)}
    
    def apply_relationship_changes(
        self,
        project_id: str,
        changes_to_apply: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply selected relationship changes to the database.
        
        Args:
            project_id: Project UUID
            changes_to_apply: List of change objects to apply
            
        Returns:
            Result of applying changes
        """
        results = {
            'updated': 0,
            'created': 0,
            'deleted': 0,
            'errors': []
        }
        
        for change in changes_to_apply:
            action = change.get('action', 'update')
            
            try:
                if action == 'update' and change.get('edge_id'):
                    # Update existing relationship
                    new_props = {
                        'emotional_tone': change.get('new_emotional_tone'),
                        'sentiment_score': change.get('new_sentiment_score'),
                        'context': change.get('new_context'),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    
                    success = self.records_manager.update_relationship(
                        project_id=project_id,
                        edge_id=int(change.get('edge_id')),
                        properties=new_props
                    )
                    
                    if success:
                        results['updated'] += 1
                    else:
                        results['errors'].append(f"Failed to update edge {change.get('edge_id')}")
                
                elif action == 'create':
                    # Create new relationship
                    edge_id = self.records_manager.create_relationship(
                        project_id=project_id,
                        source_name=change.get('source'),
                        target_name=change.get('target'),
                        relationship_type=change.get('relationship_type'),
                        properties={
                            'context': change.get('context', ''),
                            'emotional_tone': change.get('emotional_tone', 'neutral'),
                            'sentiment_score': change.get('sentiment_score', 0),
                            'created_at': datetime.utcnow().isoformat()
                        }
                    )
                    
                    if edge_id:
                        results['created'] += 1
                    else:
                        results['errors'].append(f"Failed to create relationship {change.get('source')} -> {change.get('target')}")
                
                elif action == 'delete' and change.get('edge_id'):
                    # Delete relationship
                    success = self.records_manager.delete_relationship(
                        project_id=project_id,
                        edge_id=int(change.get('edge_id'))
                    )
                    
                    if success:
                        results['deleted'] += 1
                    else:
                        results['errors'].append(f"Failed to delete edge {change.get('edge_id')}")
                        
            except Exception as e:
                results['errors'].append(f"Error processing change: {e}")
        
        results['success'] = len(results['errors']) == 0
        return results


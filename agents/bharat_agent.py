"""
bharat_agent.py - Bharat Connect Cross-Language AI Agent
=========================================================
Intelligent agent that handles multilingual search with graceful fallback

Features:
- Searches in user's preferred language first
- Falls back to other languages if no results found
- Translates cross-language results to user's language
- Provides transparency about original source language
- Summarizes content intelligently

Author: Bharat Connect Team
Date: 2025-10-25
Version: 2.0
"""

import vertexai
from agents.agent_tools import BigQuerySearchTool, TranslationTool, SummarizationTool
import json
from datetime import datetime

# ============================================================================
# LANGUAGE MAPPING
# ============================================================================

LANGUAGE_MAP = {
    'Hindi': 'hi',
    'English': 'en',
    'Telugu': 'te',
    'Tamil': 'ta',
    'Marathi': 'mr',
    'Gujarati': 'gu',
    'Kannada': 'kn',
    'Malayalam': 'ml',
    'Bengali': 'bn',
    'Punjabi': 'pa'
}

LANGUAGE_NAMES = {
    'hi': 'Hindi',
    'en': 'English',
    'te': 'Telugu',
    'ta': 'Tamil',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'bn': 'Bengali',
    'pa': 'Punjabi'
}

# ============================================================================
# BHARAT CONNECT AGENT
# ============================================================================

class BharatConnectAgent:
    """
    Cross-language intelligent agent for content discovery.
    
    Smart search strategy:
    1. Try user's language first
    2. If no results, try all languages
    3. Translate results to user's language
    4. Mark translated content with original language
    """
    
    def __init__(self, project_id: str, location: str, user_language: str = "English"):
        """
        Initialize agent with user's preferred language.
        
        Args:
            project_id: GCP project ID
            location: GCP location (e.g., 'us-central1')
            user_language: User's preferred language (full name, e.g., 'Hindi')
        """
        print(f"Initializing Bharat Connect Agent...")
        print(f"   Project: {project_id}")
        print(f"   Location: {location}")
        print(f"   User Language: {user_language}")
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Store user's language
        self.user_language = user_language
        self.user_language_code = LANGUAGE_MAP.get(user_language, 'en')
        
        # Initialize tools
        self.searcher = BigQuerySearchTool(project_id)
        self.translator = TranslationTool()
        self.summarizer = SummarizationTool()
        
        print(f"Agent ready for {user_language} (code: {self.user_language_code})")
    
    def process_query(self, query: str, filters: dict = None) -> dict:
        """
        Process user query with intelligent cross-language search.
        
        Args:
            query: User's search query in their preferred language
            filters: Optional filters (content_type, limit, etc.)
        
        Returns:
            dict: {
                "query": original query,
                "user_language": user's language,
                "results_count": number of results,
                "cross_language_used": True if results from other languages,
                "results": list of processed results
            }
        """
        print(f"\n{'='*70}")
        print(f"PROCESSING QUERY")
        print(f"{'='*70}")
        print(f"Query: {query}")
        print(f"User Language: {self.user_language} ({self.user_language_code})")
        print(f"Filters: {filters}")
        print(f"{'='*70}\n")
        
        filters = filters or {}
        limit = filters.get('limit', 5)
        content_type = filters.get('content_type', 'All')
        
        # ====================================================================
        # STEP 1: Try user's language first
        # ====================================================================
        
        print(f"Step 1: Searching in {self.user_language}...")
        
        results = self.searcher.search(
            query,
            limit=limit * 2,  # Get extra for filtering
            languages=[self.user_language_code]
        )
        
        cross_language_used = False
        
        # ====================================================================
        # STEP 2: If no results, try all languages
        # ====================================================================
        
        if not results or len(results) == 0:
            print(f" No results in {self.user_language}")
            print(f"Step 2: Searching in ALL languages...")
            
            results = self.searcher.search(
                query,
                limit=limit * 3,  # Get more for cross-language
                languages=None  # All languages
            )
            
            cross_language_used = True
            
            if results and len(results) > 0:
                print(f"Found {len(results)} results in other languages")
            else:
                print(f"No results in any language")
        else:
            print(f"Found {len(results)} results in {self.user_language}")
        
        # ====================================================================
        # STEP 3: Handle no results case
        # ====================================================================
        
        if not results or len(results) == 0:
            return {
                "error": f"No content found for '{query}' in any language.",
                "query": query,
                "user_language": self.user_language,
                "results_count": 0,
                "cross_language_used": False,
                "results": []
            }
        
        # ====================================================================
        # STEP 4: Process and translate results
        # ====================================================================
        
        print(f"\nStep 3: Processing {len(results)} results...")
        
        processed_results = []
        
        for idx, article in enumerate(results[:limit], 1):
            print(f"\n   [{idx}/{min(limit, len(results))}] Processing article...")
            
            # Determine original language
            original_lang_code = article.get('language', 'en')
            original_lang_name = LANGUAGE_NAMES.get(original_lang_code, 'Unknown')
            
            print(f"      Original Language: {original_lang_name} ({original_lang_code})")
            
            # Check if translation needed
            needs_translation = (original_lang_code != self.user_language_code)
            
            # Get title
            original_title = article.get('title', 'No title')
            title = original_title
            
            if needs_translation:
                print(f"      Translating title to {self.user_language}...")
                title = self.translator.translate(original_title, target_language=self.user_language)
            
            # Get content for summarization
            content = article.get('description', '') or article.get('content', '') or original_title
            
            # Limit content length
            if len(content) > 500:
                content = content[:500]
            
            # Translate content if needed
            if needs_translation:
                print(f"      Translating content to {self.user_language}...")
                content = self.translator.translate(content, target_language=self.user_language)
            
            # Summarize
            print(f"      Generating summary...")
            summary = self.summarizer.summarize(content)
            
            # Determine content type
            source = article.get('source', 'unknown').lower()
            content_type_determined = 'education' if 'diksha' in source else 'news'
            
            # Build result object
            result = {
                "title": title,
                "original_title": original_title,
                "original_language": original_lang_name,
                "original_language_code": original_lang_code,
                "was_translated": needs_translation,
                "summary": summary,
                "source": article.get('source', 'Unknown'),
                "url": article.get('url', article.get('diksha_url', '#')),
                "date": str(article.get('published_date', article.get('created_on', 'N/A'))),
                "content_type": content_type_determined
            }
            
            # Add education-specific fields if applicable
            if content_type_determined == 'education':
                grade_level = article.get('grade_level', [])
                subject = article.get('subject', [])
                
                result.update({
                    "board": article.get('board', 'N/A'),
                    "grade": ', '.join(grade_level) if isinstance(grade_level, list) else str(grade_level),
                    "subject": ', '.join(subject) if isinstance(subject, list) else str(subject)
                })
            
            processed_results.append(result)
            print(f"      Done")
        
        # ====================================================================
        # STEP 5: Return results
        # ====================================================================
        
        print(f"\n{'='*70}")
        print(f"QUERY COMPLETE")
        print(f"{'='*70}")
        print(f"Results: {len(processed_results)}")
        print(f"Cross-language search used: {cross_language_used}")
        print(f"{'='*70}\n")
        
        return {
            "query": query,
            "user_language": self.user_language,
            "user_language_code": self.user_language_code,
            "results_count": len(processed_results),
            "cross_language_used": cross_language_used,
            "results": processed_results
        }

# ============================================================================
# TEST BLOCK
# ============================================================================

if __name__ == "__main__":
    import os
    
    PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'bharat-connect-000')
    LOCATION = os.getenv('GCP_LOCATION', 'us-central1')
    
    print("="*70)
    print(" " * 20 + "AGENT TEST SUITE")
    print("="*70)
    
    # Test 1: Hindi query
    print("\n" + "="*70)
    print("TEST 1: Hindi Query (पंतप्रधान)")
    print("="*70)
    agent_hi = BharatConnectAgent(project_id=PROJECT_ID, location=LOCATION, user_language="Hindi")
    response = agent_hi.process_query("पंतप्रधान")
    print("\nResponse:")
    print(json.dumps(response, indent=2, ensure_ascii=False))
    
    # Test 2: English query
    print("\n" + "="*70)
    print("TEST 2: English Query (education)")
    print("="*70)
    agent_en = BharatConnectAgent(project_id=PROJECT_ID, location=LOCATION, user_language="English")
    response = agent_en.process_query("Class 10 Mathematics")
    print("\nResponse:")
    print(json.dumps(response, indent=2, ensure_ascii=False))
    
    # Test 3: Cross-language query (Telugu query with Hindi agent)
    print("\n" + "="*70)
    print("TEST 3: Cross-Language (Telugu query, Hindi interface)")
    print("="*70)
    agent_hi2 = BharatConnectAgent(project_id=PROJECT_ID, location=LOCATION, user_language="Hindi")
    response = agent_hi2.process_query("తెలుగు వార్తలు")
    print("\nResponse:")
    print(json.dumps(response, indent=2, ensure_ascii=False))

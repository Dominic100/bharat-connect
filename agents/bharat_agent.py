"""
bharat_agent.py - Bharat Connect Cross-Language AI Agent
=========================================================
"""

import vertexai
from agents.agent_tools import BigQuerySearchTool, TranslationTool, SummarizationTool
import json
from datetime import datetime

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

class BharatConnectAgent:
    """Cross-language intelligent agent."""
    
    def __init__(self, project_id: str, location: str, user_language: str = "English"):
        print(f"Initializing Bharat Connect Agent...")
        print(f"   Project: {project_id}")
        print(f"   Location: {location}")
        print(f"   User Language: {user_language}")
        
        vertexai.init(project=project_id, location=location)
        
        self.user_language = user_language
        self.user_language_code = LANGUAGE_MAP.get(user_language, 'en')
        
        self.searcher = BigQuerySearchTool(project_id)
        self.translator = TranslationTool()
        self.summarizer = SummarizationTool()
        
        print(f"Agent ready for {user_language} (code: {self.user_language_code})")
    
    def process_query(self, query: str, filters: dict = None) -> dict:
        """Process user query with cross-language search."""
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
        
        # STEP 1: Try user's language first
        print(f"Step 1: Searching in {self.user_language}...")
        
        results = self.searcher.search(
            query,
            limit=limit * 2,
            languages=[self.user_language_code]
        )
        
        cross_language_used = False
        
        # STEP 2: If no results, try all languages
        if not results or len(results) == 0:
            print(f"  No results in {self.user_language}")
            print(f"Step 2: Searching in ALL languages...")
            
            # Try both original query and English translation
            queries_to_try = [query]
            
            if self.user_language_code != 'en':
                try:
                    translated_query = self.translator.translate(query, target_language="English")
                    print(f"  Translated: {query} → {translated_query}")
                    queries_to_try.append(translated_query)
                except Exception as e:
                    print(f"  Translation failed: {e}")
            
            # Search with all query variants
            for q in queries_to_try:
                results = self.searcher.search(
                    q,
                    limit=limit * 2,
                    languages=None
                )
                if results and len(results) > 0:
                    break  # Stop on first successful search
            
            cross_language_used = True
        
        # STEP 3: Handle no results
        if not results or len(results) == 0:
            return {
                "error": f"No content found for '{query}' in any language.",
                "query": query,
                "user_language": self.user_language,
                "results_count": 0,
                "cross_language_used": False,
                "results": []
            }
        
        # STEP 4: Process and translate results
        print(f"\nStep 3: Processing {len(results)} results...")
        
        processed_results = []
        
        for idx, article in enumerate(results[:limit], 1):
            print(f"\n   [{idx}/{min(limit, len(results))}] Processing article...")
            
            # FIXED: Handle language as list or string
            original_lang_raw = article.get('language', 'en')
            
            if isinstance(original_lang_raw, list):
                original_lang_code = original_lang_raw[0] if original_lang_raw else 'en'
            else:
                original_lang_code = original_lang_raw
            
            original_lang_name = LANGUAGE_NAMES.get(original_lang_code, 'Unknown')
            
            print(f"      Original Language: {original_lang_name} ({original_lang_code})")
            
            needs_translation = True # to force quality assurance
            
            # Get title
            original_title = article.get('title', 'No title')
            title = original_title
            
            if needs_translation:
                print(f"      Translating title to {self.user_language}...")
                title = self.translator.translate(original_title, target_language=self.user_language)
            
            # Get content
            content = article.get('description', '') or article.get('content', '') or original_title
            
            if len(content) > 500:
                content = content[:500]
            
            if needs_translation:
                print(f"      Translating content to {self.user_language}...")
                content = self.translator.translate(content, target_language=self.user_language)
            
            # Summarize
            print(f"      Generating summary...")
            summary = self.summarizer.summarize(content, target_language=self.user_language)  # ADD target_language
            
            # Determine content type
            source = article.get('source', 'unknown').lower()
            content_type_determined = 'education' if 'diksha' in source else 'news'
            
            # Build result
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
            
            # Add education fields
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
        
        # STEP 5: Return results
        print(f"\n{'='*70}")
        print(f"QUERY COMPLETE")
        print(f"{'='*70}")
        print(f"Results: {len(processed_results)}")
        print(f"Cross-language: {cross_language_used}")
        print(f"{'='*70}\n")
        
        return {
            "query": query,
            "user_language": self.user_language,
            "user_language_code": self.user_language_code,
            "results_count": len(processed_results),
            "cross_language_used": cross_language_used,
            "results": processed_results
        }
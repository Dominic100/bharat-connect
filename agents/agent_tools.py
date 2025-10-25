"""
agent_tools.py - Bharat Connect Agent Tools
============================================
Production-ready tools for BigQuery search, translation, and summarization

Tools:
1. BigQuerySearchTool - Search across RSS and DIKSHA content
2. TranslationTool - Translate content using Gemini
3. SummarizationTool - Summarize content intelligently

Author: Bharat Connect Team
Date: 2025-10-25
Version: 2.0
"""

import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import bigquery
import re
import time

# ============================================================================
# TOOL 1: BIGQUERY SEARCH (CROSS-LANGUAGE)
# ============================================================================

class BigQuerySearchTool:
    """
    Tool to search both RSS and DIKSHA content in BigQuery.
    
    Supports:
    - Multi-language search
    - Content type filtering (news/education)
    - Word-based matching
    - Cross-table queries
    """
    
    def __init__(self, project_id: str):
        """
        Initialize BigQuery client.
        
        Args:
            project_id: GCP project ID
        """
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
        
        # Table paths
        self.rss_table = f"{project_id}.rss_connector.rss_content"
        self.diksha_table = f"{project_id}.diksha_connector.diksha_content"
        
        print(f"BigQuerySearchTool initialized")
        print(f"   RSS table: {self.rss_table}")
        print(f"   DIKSHA table: {self.diksha_table}")
    
    def search(self, query: str, limit: int = 5, languages: list = None, 
               content_type: str = "All") -> list:
        """
        Search across RSS and DIKSHA content.
        
        Args:
            query: Search query
            limit: Maximum results to return
            languages: List of language codes (e.g., ['hi', 'en']). None = all languages
            content_type: "All", "News", or "Education"
        
        Returns:
            List of matching articles/content
        """
        print(f"\nBigQuery Search")
        print(f"   Query: {query}")
        print(f"   Languages: {languages or 'All'}")
        print(f"   Content Type: {content_type}")
        print(f"   Limit: {limit}")
        
        # Split query into words for matching
        words = re.split(r'\s+', query.strip())
        if not words:
            print(f"   Empty query")
            return []
        
        # Build WHERE clause for word matching
        where_clauses = []
        for word in words:
            if word:
                # Escape single quotes
                escaped_word = word.replace("'", "\\'")
                # Match in title, content, or description
                where_clauses.append(
                    f"(LOWER(title) LIKE LOWER('%{escaped_word}%') OR "
                    f"LOWER(CAST(content AS STRING)) LIKE LOWER('%{escaped_word}%') OR "
                    f"LOWER(CAST(description AS STRING)) LIKE LOWER('%{escaped_word}%'))"
                )
        
        where_condition = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Language filter
        language_condition = ""
        if languages and len(languages) > 0:
            # Handle both array and string language fields
            lang_list = "', '".join(languages)
            language_condition = f"AND (language IN ('{lang_list}') OR '{lang_list}' IN UNNEST(language))"
        
        results = []
        
        # ====================================================================
        # Query RSS table (News)
        # ====================================================================
        
        if content_type in ["All", "News"]:
            rss_sql = f"""
            SELECT
                id,
                title,
                content,
                language,
                source,
                url,
                published_date,
                'rss' as content_source,
                'news' as content_type
            FROM
                `{self.rss_table}`
            WHERE
                ({where_condition})
                {language_condition}
            ORDER BY
                published_date DESC
            LIMIT {limit}
            """
            
            try:
                print(f"   Querying RSS table...")
                rss_results = self.client.query(rss_sql).result()
                rss_count = 0
                for row in rss_results:
                    results.append(dict(row))
                    rss_count += 1
                print(f"   RSS: {rss_count} results")
            except Exception as e:
                print(f"   RSS search failed: {e}")
        
        # ====================================================================
        # Query DIKSHA table (Education)
        # ====================================================================
        
        if content_type in ["All", "Education"]:
            diksha_sql = f"""
            SELECT
                content_id as id,
                title,
                description,
                ARRAY_TO_STRING(language, ', ') as language,
                'DIKSHA' as source,
                board,
                grade_level,
                subject,
                diksha_url as url,
                created_on as published_date,
                'diksha' as content_source,
                'education' as content_type
            FROM
                `{self.diksha_table}`
            WHERE
                ({where_condition})
                {language_condition}
            ORDER BY
                created_on DESC
            LIMIT {limit}
            """
            
            try:
                print(f"   Querying DIKSHA table...")
                diksha_results = self.client.query(diksha_sql).result()
                diksha_count = 0
                for row in diksha_results:
                    results.append(dict(row))
                    diksha_count += 1
                print(f"   DIKSHA: {diksha_count} results")
            except Exception as e:
                print(f"   DIKSHA search failed: {e}")
        
        print(f"   Total results: {len(results)}")
        
        # Return limited results
        return results[:limit]

# ============================================================================
# TOOL 2: TRANSLATION (GEMINI)
# ============================================================================

class TranslationTool:
    """
    Translation tool using Gemini 2.0 Flash.
    
    Supports all major Indian languages.
    """
    
    def __init__(self):
        """Initialize Gemini model."""
        self.model = GenerativeModel("gemini-2.0-flash")
        print(f"TranslationTool initialized (Gemini 2.0 Flash)")
    
    def translate(self, text: str, target_language: str = "English") -> str:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_language: Target language (e.g., 'Hindi', 'English', 'Telugu')
        
        Returns:
            Translated text
        """
        if not text or len(text.strip()) == 0:
            return ""
        
        print(f"   Translating to {target_language}...")
        
        prompt = f"""Translate the following text to {target_language}.

If the text is already in {target_language}, return it as-is.

IMPORTANT: Provide ONLY the translation. Do not add any explanations, notes, or metadata.

Text: "{text}"

{target_language} Translation:"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 1024,
                }
            )
            
            translation = response.text.strip()
            
            # Remove any leading/trailing quotes
            translation = translation.strip('"').strip("'")
            
            print(f"   Translated ({len(translation)} chars)")
            
            # Rate limiting (Gemini 2.0 Flash: 10 QPM free tier)
            time.sleep(0.5)
            
            return translation
            
        except Exception as e:
            print(f"   Translation failed: {e}")
            return text  # Return original text on failure

# ============================================================================
# TOOL 3: SUMMARIZATION (GEMINI)
# ============================================================================

class SummarizationTool:
    """
    Summarization tool using Gemini 2.0 Flash.
    
    Generates concise 3-bullet point summaries.
    """
    
    def __init__(self):
        """Initialize Gemini model."""
        self.model = GenerativeModel("gemini-2.0-flash-exp")
        print(f"SummarizationTool initialized (Gemini 2.0 Flash)")
    
    def summarize(self, text: str) -> str:
        """
        Summarize text in 3 concise bullet points.
        
        Args:
            text: Text to summarize
        
        Returns:
            Summary (3 bullet points)
        """
        if not text or len(text.strip()) == 0:
            return "No content available for summarization."
        
        print(f"   Generating summary...")
        
        prompt = f"""Summarize the following content in EXACTLY 3 concise bullet points.

Each bullet point should be:
- One clear sentence
- 15-25 words maximum
- Focused on key information

Content: "{text}"

Summary (3 bullets):"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 512,
                }
            )
            
            summary = response.text.strip()
            
            print(f"   Summary generated ({len(summary)} chars)")
            
            # Rate limiting
            time.sleep(0.5)
            
            return summary
            
        except Exception as e:
            print(f"   Summarization failed: {e}")
            return "Summary unavailable."

# ============================================================================
# TEST BLOCK
# ============================================================================

if __name__ == "__main__":
    import os
    
    PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'bharat-connect-000')
    
    print("="*70)
    print(" " * 20 + "AGENT TOOLS TEST")
    print("="*70)
    
    # Test 1: BigQuery Search
    print("\n" + "="*70)
    print("TEST 1: BigQuery Search (Hindi query)")
    print("="*70)
    
    searcher = BigQuerySearchTool(PROJECT_ID)
    results = searcher.search("पंतप्रधान", limit=3, languages=['hi'])
    
    print(f"\nResults: {len(results)}")
    for idx, result in enumerate(results, 1):
        print(f"\n{idx}. {result.get('title', 'No title')}")
        print(f"   Language: {result.get('language', 'unknown')}")
        print(f"   Source: {result.get('source', 'unknown')}")
    
    # Test 2: Translation
    print("\n" + "="*70)
    print("TEST 2: Translation (Hindi to English)")
    print("="*70)
    
    translator = TranslationTool()
    hindi_text = "पंतप्रधान नरेंद्र मोदी ने आज एक महत्वपूर्ण घोषणा की।"
    english_text = translator.translate(hindi_text, target_language="English")
    
    print(f"\nOriginal (Hindi): {hindi_text}")
    print(f"Translated (English): {english_text}")
    
    # Test 3: Summarization
    print("\n" + "="*70)
    print("TEST 3: Summarization")
    print("="*70)
    
    summarizer = SummarizationTool()
    long_text = """
    Prime Minister Narendra Modi today announced a new initiative for digital 
    education across rural India. The program will provide free internet access 
    and digital devices to students in over 100,000 villages. This is part of 
    the government's Digital India mission to bridge the technology gap between 
    urban and rural areas. The initiative will be implemented over the next two 
    years with a budget of Rs 10,000 crores.
    """
    summary = summarizer.summarize(long_text)
    
    print(f"\nOriginal Text: {long_text.strip()[:100]}...")
    print(f"\nSummary:\n{summary}")
    
    print("\n" + "="*70)
    print("✅ All tests completed")
    print("="*70)

"""
agent_tools.py - Bharat Connect Agent Tools
============================================
BigQuery search, translation, and summarization

RSS Table Fields: content_id, title, description, content, language (STRING), 
                  source, source_type, url, published_date, id
                  
DIKSHA Table Fields: content_id, title, description, language (JSON), 
                     board, grade_level (JSON), subject (JSON), diksha_url, 
                     created_on, status

Author: Bharat Connect Team
Date: 2025-10-25
"""

import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import bigquery
import re
import time
import json as json_module

class BigQuerySearchTool:
    """Search across RSS and DIKSHA tables."""
    
    def __init__(self, project_id: str):
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
        
        self.rss_table = f"{project_id}.rss_connector.rss_content"
        self.diksha_table = f"{project_id}.diksha_connector.diksha_content"
        
        print(f"BigQuerySearchTool initialized")
        print(f"   RSS: {self.rss_table}")
        print(f"   DIKSHA: {self.diksha_table}")
    
    def search(self, query: str, limit: int = 5, languages: list = None, 
               content_type: str = "All") -> list:
        """
        Search across RSS and DIKSHA tables.
        
        Args:
            query: Search query
            limit: Maximum results
            languages: List of language codes
            content_type: "All", "News", or "Education"
        
        Returns:
            List of results
        """
        print(f"\nBigQuery Search")
        print(f"   Query: {query}")
        print(f"   Languages: {languages or 'All'}")
        print(f"   Limit: {limit}")
        
        words = re.split(r'\s+', query.strip())
        if not words:
            return []
        
        results = []
        
        # RSS TABLE
        if content_type in ["All", "News"]:
            where_clauses = []
            for word in words:
                if word:
                    esc = word.replace("'", "\\'")
                    where_clauses.append(
                        f"(LOWER(title) LIKE LOWER('%{esc}%') OR "
                        f"LOWER(COALESCE(description, '')) LIKE LOWER('%{esc}%') OR "
                        f"LOWER(COALESCE(content, '')) LIKE LOWER('%{esc}%'))"
                    )
            
            where_condition = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            lang_filter = ""
            if languages:
                lang_list = "', '".join(languages)
                lang_filter = f"AND language IN ('{lang_list}')"
            
            rss_sql = f"""
            SELECT
                id,
                title,
                content,
                description,
                language,
                source,
                url,
                published_date,
                'rss' as content_source
            FROM
                `{self.rss_table}`
            WHERE
                ({where_condition})
                {lang_filter}
            ORDER BY
                published_date DESC
            LIMIT {limit}
            """
            
            try:
                print(f"   Querying RSS...")
                rss_results = self.client.query(rss_sql).result()
                count = 0
                for row in rss_results:
                    results.append(dict(row))
                    count += 1
                print(f"   RSS: {count} results")
            except Exception as e:
                print(f"   RSS error: {e}")
        
        # DIKSHA TABLE
        if content_type in ["All", "Education"]:
            where_clauses = []
            for word in words:
                if word:
                    esc = word.replace("'", "\\'")
                    where_clauses.append(
                        f"(LOWER(title) LIKE LOWER('%{esc}%') OR "
                        f"LOWER(COALESCE(description, '')) LIKE LOWER('%{esc}%'))"
                    )
            
            where_condition = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            lang_filter = ""
            if languages:
                lang_conditions = []
                for lang in languages:
                    lang_conditions.append(
                        f"JSON_QUERY(language, '$') LIKE '%\"{lang}\"%'"
                    )
                lang_filter = f"AND ({' OR '.join(lang_conditions)})"
            
            diksha_sql = f"""
            SELECT
                content_id as id,
                title,
                description,
                language,
                'DIKSHA' as source,
                board,
                grade_level,
                subject,
                diksha_url as url,
                created_on as published_date,
                'diksha' as content_source
            FROM
                `{self.diksha_table}`
            WHERE
                ({where_condition})
                {lang_filter}
            ORDER BY
                created_on DESC
            LIMIT {limit}
            """
            
            try:
                print(f"   Querying DIKSHA...")
                diksha_results = self.client.query(diksha_sql).result()
                count = 0
                for row in diksha_results:
                    row_dict = dict(row)
                    if 'language' in row_dict and isinstance(row_dict['language'], str):
                        try:
                            row_dict['language'] = json_module.loads(row_dict['language'])
                        except:
                            pass
                    results.append(row_dict)
                    count += 1
                print(f"   DIKSHA: {count} results")
            except Exception as e:
                print(f"   DIKSHA error: {e}")
        
        print(f"   Total: {len(results)} results")
        return results[:limit]

class TranslationTool:
    """Translation using Gemini."""
    
    def __init__(self):
        self.model = GenerativeModel("gemini-2.0-flash")
        print(f"TranslationTool initialized")
    
    def translate(self, text: str, target_language: str = "English") -> str:
        """Translate text to target language."""
        if not text or len(text.strip()) == 0:
            return ""
        
        print(f"   Translating to {target_language}...")
        
        prompt = f"""Translate to {target_language}. If already in {target_language}, return unchanged. Only the translation, no explanations.

Text: "{text}"

{target_language}:"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 1024}
            )
            translation = response.text.strip().strip('"').strip("'")
            print(f"   Translation complete")
            time.sleep(0.5)
            return translation
        except Exception as e:
            print(f"   Translation error: {e}")
            return text

class SummarizationTool:
    """Summarization using Gemini."""
    
    def __init__(self):
        self.model = GenerativeModel("gemini-2.0-flash")
        print(f"SummarizationTool initialized")
    
    def summarize(self, text: str) -> str:
        """Generate 3-bullet summary."""
        if not text or len(text.strip()) == 0:
            return "No content available for summarization."
        
        print(f"   Generating summary...")
        
        prompt = f"""Summarize in exactly 3 bullet points. Each bullet should be 15-25 words.

Content: "{text}"

Summary:"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": 0.3, "max_output_tokens": 512}
            )
            summary = response.text.strip()
            print(f"   Summary complete")
            time.sleep(0.5)
            return summary
        except Exception as e:
            print(f"   Summarization error: {e}")
            return "Summary unavailable."

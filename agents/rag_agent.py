"""
rag_agent.py - Universal Production-Ready RAG Agent
====================================================

A self-learning RSS feed discovery system that works for ANY domain.

Key Features:
1. Dynamically learns URL patterns (no hardcoded parameters)
2. Uses Gemini AI for intelligent pattern inference
3. Generates and validates candidate URLs
4. Cleans internal metadata before validation
5. Iteratively improves discovery quality

Optimized for: Government sites, news portals, blogs, aggregators
Compatible with: validator_agent.py, learning_agent.py, coordinator.py

Author: Bharat Connect
Date: 2025-10-24
Version: 2.0 (Universal)
"""

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import time
import requests
import feedparser
from validator_agent import AIValidatorAgent
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from urllib.parse import urlparse, parse_qs, parse_qsl, urlencode, urlunparse
import re
import logging
import itertools
import random
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PART 1: UNIVERSAL URL STRUCTURE ANALYZER
# ============================================================================

class URLStructureAnalyzer:
    """
    Analyzes URL structures dynamically for any domain.
    
    Extracts:
    - Query parameters (?key=value)
    - Parameter types (numeric, categorical, boolean)
    - Value ranges and patterns
    - Path structures
    
    Works with: pib.gov.in, news sites, WordPress, custom CMSs
    """
    
    def __init__(self, feeds: List[Dict]):
        """
        Initialize analyzer with discovered feeds.
        
        Args:
            feeds: List of feed dicts with 'url' key
        """
        self.feeds = feeds
        self.parameters = {}
        self.domain = None
        self.path = None
        self.path_patterns = []
        
        logger.info(f"URLStructureAnalyzer initialized with {len(feeds)} feeds")
    
    def analyze(self) -> Dict:
        """
        Perform complete URL structure analysis.
        
        Returns:
            Dict with domain, path, parameters, and patterns
        """
        if not self.feeds:
            logger.warning("No feeds to analyze")
            return {}
        
        # Extract from all feeds
        for feed in self.feeds:
            url = feed.get("url")
            if not url:
                continue
            
            self._extract_url_components(url)
        
        # Summarize patterns
        summary = self._summarize_patterns()
        
        logger.info(f"Extracted {len(self.parameters)} unique parameters")
        
        return summary
    
    def _extract_url_components(self, url: str):
        """Extract domain, path, and query parameters from URL."""
        try:
            parsed = urlparse(url)
            
            # Set domain and path (first occurrence)
            if not self.domain:
                self.domain = parsed.netloc
                self.path = parsed.path
            
            # Extract query parameters
            params = parse_qs(parsed.query)
            
            for param_name, param_values in params.items():
                # Skip internal metadata
                if param_name.lower() in ["confidence", "reasoning"]:
                    continue
                
                # Store all observed values
                if param_name not in self.parameters:
                    self.parameters[param_name] = set()
                
                for value in param_values:
                    if value:  # Skip empty values
                        self.parameters[param_name].add(value)
            
            # Store path patterns
            if parsed.path and parsed.path != "/":
                self.path_patterns.append(parsed.path)
        
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
    
    def _summarize_patterns(self) -> Dict:
        """Summarize extracted patterns."""
        
        summary = {
            "domain": self.domain,
            "path": self.path,
            "path_patterns": list(set(self.path_patterns)),
            "parameters": {}
        }
        
        # Analyze each parameter
        for param_name, param_values in self.parameters.items():
            param_values = list(param_values)
            
            # Detect parameter type
            is_numeric = self._is_numeric_param(param_values)
            is_boolean = self._is_boolean_param(param_values)
            
            param_info = {
                "observed_values": param_values[:50],  # Limit for readability
                "value_count": len(param_values),
                "type": self._determine_param_type(param_values, is_numeric, is_boolean)
            }
            
            # Add numeric range if applicable
            if is_numeric:
                numeric_values = [int(v) for v in param_values if v.isdigit()]
                if numeric_values:
                    param_info["numeric_range"] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values)
                    }
            
            summary["parameters"][param_name] = param_info
        
        return summary
    
    def _is_numeric_param(self, values: List[str]) -> bool:
        """Check if parameter values are numeric."""
        if not values:
            return False
        numeric_count = sum(1 for v in values if v.isdigit())
        return numeric_count / len(values) > 0.8
    
    def _is_boolean_param(self, values: List[str]) -> bool:
        """Check if parameter is boolean-like."""
        bool_values = {"true", "false", "0", "1", "yes", "no"}
        return all(v.lower() in bool_values for v in values)
    
    def _determine_param_type(self, values: List[str], is_numeric: bool, is_boolean: bool) -> str:
        """Determine parameter type."""
        if is_boolean:
            return "boolean"
        elif is_numeric:
            return "numeric"
        elif len(values) <= 10:
            return "categorical"
        else:
            return "string"


# ============================================================================
# PART 2: GEMINI PATTERN LEARNER (Universal)
# ============================================================================

class GeminiPatternLearner:
    """
    Uses Gemini AI to learn URL patterns intelligently.
    
    Capabilities:
    - Identifies parameter relationships
    - Suggests new combinations
    - Estimates coverage
    - Provides reasoning for suggestions
    """
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        """
        Initialize Gemini pattern learner.
        
        Args:
            project_id: Google Cloud project ID
            location: Vertex AI location
        """
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Initialize Gemini model
        self.model = GenerativeModel("gemini-2.0-flash")
        self.config = GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
            response_mime_type="application/json"
        )
        
        # Rate limiting: prefer one call per minute to respect strict quotas
        self.api_delay = 60.0
        self.last_api_call = 0.0
        
        logger.info(f"Gemini Pattern Learner initialized (project: {project_id})")
    
    def _wait_for_api_slot(self, max_wait: Optional[float] = None) -> bool:
        """Wait until api_delay seconds have passed since last response.

        Args:
            max_wait: maximum seconds willing to wait (None = wait indefinitely)

        Returns:
            True if slot became available within max_wait, False otherwise.
        """
        elapsed = time.time() - self.last_api_call
        if elapsed >= self.api_delay:
            return True
        wait = self.api_delay - elapsed
        if max_wait is not None and wait > max_wait:
            return False
        time.sleep(wait)
        return True
    
    def learn_patterns(self, feeds: List[Dict], domain: str) -> Dict:
        """
        Analyze feed URLs and learn patterns using Gemini.
        
        Args:
            feeds: List of discovered feeds
            domain: Domain being analyzed
            
        Returns:
            Dict with learned patterns and suggestions
        """
        
        # Prepare feed summaries for Gemini
        feed_summaries = []
        for feed in feeds[:20]:  # Limit to 20 for context window
            url = feed.get("url", "")
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            feed_summaries.append({
                "url": url,
                "parameters": {k: v[0] if v else None for k, v in params.items()}
            })
        
    # Construct prompt
        prompt = f"""
You are an expert at discovering hidden RSS/Atom feed patterns on websites.

Analyze these {len(feed_summaries)} discovered feeds from domain "{domain}":

{json.dumps(feed_summaries, indent=2)}

Your task:
1. Identify all unique parameter names and their observed values
2. Detect parameter types (numeric, categorical, boolean)
3. Identify relationships between parameters (e.g., region depends on language)
4. Suggest at least 15 new parameter combinations that might lead to valid feeds
5. Estimate coverage (what % of possible feeds have we discovered)

Respond with JSON in this exact format:
{{
  "parameters": {{
    "param_name": {{
      "type": "numeric|categorical|boolean",
      "observed_values": ["val1", "val2"],
      "range": [min, max],  // for numeric only
      "confidence": 0.0-1.0,
      "interpretation": "what this parameter likely controls"
    }}
  }},
  "dependencies": [
    {{"parameter": "param1", "depends_on": "param2", "relationship": "description"}}
  ],
  "suggestions": [
    {{
      "param1": "value1",
      "param2": "value2",
      "confidence": 0.0-1.0,
      "reasoning": "why this combination might work"
    }}
  ],
  "coverage": {{
    "estimated_total_feeds": 100,
    "discovered_so_far": 20,
    "coverage_percent": 20
  }}
}}
"""
        
        logger.info("Sending feeds to Gemini for pattern analysis...")

    # Bounded retry/time budget and slot enforcement (1 call per minute).
        max_total_wait = 60.0
        backoff = 2
        attempt = 0
        start_time = time.time()

        while True:
            attempt += 1
            elapsed_total = time.time() - start_time
            remaining_time = max_total_wait - elapsed_total
            if remaining_time <= 0:
                logger.error("Gemini pattern learning retries/time budget exhausted; returning empty patterns")
                return {}

            slot_ok = self._wait_for_api_slot(max_wait=remaining_time)
            if not slot_ok:
                logger.warning("Not enough time to wait for API slot; returning empty patterns")
                return {}

            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.config
                )

                # Record response time (slot starts from here)
                self.last_api_call = time.time()

                # Parse response
                response_text = response.text.strip()

                # Remove markdown code blocks if present (robustly)
                if response_text.startswith("```"):
                    parts = response_text.split("```")
                    if len(parts) >= 2:
                        response_text = parts[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]

                # Defensive JSON parsing: Gemini may return a list or wrapped JSON
                try:
                    patterns = json.loads(response_text)
                except json.JSONDecodeError:
                    # Try to salvage by extracting braces substring
                    start = response_text.find('{')
                    end = response_text.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        try:
                            patterns = json.loads(response_text[start:end+1])
                        except Exception:
                            logger.error("Failed to parse Gemini response after salvage attempt")
                            return {}
                    else:
                        logger.error("Failed to parse Gemini response: no JSON object found")
                        return {}

                # If Gemini returned a list, prefer the first dict element
                if isinstance(patterns, list):
                    if len(patterns) > 0 and isinstance(patterns[0], dict):
                        patterns = patterns[0]
                    else:
                        logger.warning("Gemini returned a JSON list that couldn't be interpreted; returning empty patterns")
                        return {}

                logger.info("Pattern analysis complete")

                return patterns

            except Exception as e:
                msg = str(e)
                logger.error(f"Gemini pattern learning error (attempt {attempt}): {msg}")
                if ("429" in msg) or ("Resource exhausted" in msg) or ("quota" in msg.lower()):
                    # treat as a response (we got a quota) and back off
                    self.last_api_call = time.time()
                    elapsed_total = time.time() - start_time
                    remaining_time = max_total_wait - elapsed_total
                    if remaining_time <= 0:
                        logger.error("Gemini quota exceeded after retries; returning empty patterns")
                        return {}
                    sleep = min(backoff * (2 ** (attempt - 1)), max(1, remaining_time))
                    logger.warning(f"Gemini quota/429 detected, backing off for {sleep}s and retrying...")
                    time.sleep(sleep)
                    continue
                else:
                    return {}


# ============================================================================
# PART 3: INTELLIGENT URL GENERATOR (Universal)
# ============================================================================

class IntelligentURLGenerator:
    """
    Generates intelligent candidate URLs based on learned patterns.
    
    Strategies:
    - Suggested: Use Gemini's high-confidence suggestions
    - Systematic: Generate all combinations methodically
    - Hybrid: Mix of both approaches
    """
    
    def __init__(self, base_url: str, patterns: Optional[Dict] = None):
        """
        Initialize URL generator.
        
        Args:
            base_url: Base feed URL
            patterns: Learned patterns from Gemini
        """
        self.base_url = base_url
        self.patterns = patterns or {}
        self.generated_urls = set()
        
        logger.info("URL Generator initialized")
    
    def _strip_internal_params(self, url: str) -> str:
        """
        Remove internal metadata parameters from URL.
        
        Args:
            url: URL with potential internal params
            
        Returns:
            Clean URL without confidence/reasoning params
        """
        try:
            parsed = urlparse(url)
            
            # Parse query and filter out internal params
            clean_params = [
                (k, v) for k, v in parse_qsl(parsed.query)
                if k.lower() not in ["confidence", "reasoning"]
            ]
            
            # Rebuild URL
            clean_url = urlunparse(
                parsed._replace(query=urlencode(clean_params))
            )
            
            return clean_url
        
        except Exception as e:
            logger.error(f"Error stripping params from {url}: {e}")
            return url
    
    def generate_candidates(self, strategy: str = "hybrid", max_candidates: int = 50) -> List[str]:
        """
        Generate candidate URLs using specified strategy.
        
        Args:
            strategy: Generation strategy (suggested|systematic|hybrid)
            max_candidates: Maximum URLs to generate
            
        Returns:
            List of candidate URLs
        """
        
        if not self.patterns:
            logger.warning("No patterns available for URL generation")
            return []
        
        candidates = []
        
        if strategy == "suggested":
            candidates = self._generate_from_suggestions()
        elif strategy == "systematic":
            candidates = self._generate_systematic()
        else:  # hybrid
            suggested = self._generate_from_suggestions()
            systematic = self._generate_systematic()
            candidates = suggested + systematic
        
        # Remove duplicates and clean
        unique_candidates = []
        seen = set()
        
        for url in candidates:
            clean_url = self._strip_internal_params(url)
            if clean_url not in seen:
                unique_candidates.append(clean_url)
                seen.add(clean_url)
        
        # Limit to max_candidates
        final_candidates = unique_candidates[:max_candidates]
        
        logger.info(f"Generated {len(final_candidates)} candidate URLs using {strategy}")
        
        return final_candidates
    
    def _generate_from_suggestions(self) -> List[str]:
        """Generate URLs from Gemini suggestions."""
        urls = []
        
        suggestions = self.patterns.get("suggestions", [])
        
        for suggestion in suggestions:
            # Remove confidence and reasoning from params
            params = {k: v for k, v in suggestion.items()
                     if k not in ["confidence", "reasoning"]}
            
            url = self._build_url(params)
            urls.append(url)
        
        return urls
    
    def _generate_systematic(self) -> List[str]:
        """Generate URLs systematically from parameter combinations."""
        urls = []
        
        parameters = self.patterns.get("parameters", {})
        
        if not parameters:
            return urls
        
        # Extract parameter names and values
        param_names = list(parameters.keys())
        param_value_lists = []
        
        for param_name in param_names:
            param_info = parameters[param_name]
            observed_values = param_info.get("observed_values", [])
            
            # Limit values to prevent combinatorial explosion
            param_value_lists.append(observed_values[:5])
        
        # Generate combinations
        for combination in itertools.product(*param_value_lists):
            params = dict(zip(param_names, combination))
            url = self._build_url(params)
            urls.append(url)
            
            if len(urls) >= 25:  # Limit systematic generation
                break
        
        return urls
    
    def _build_url(self, params: Dict) -> str:
        """
        Build URL from parameters.
        
        Args:
            params: Dict of parameters
            
        Returns:
            Complete URL
        """
        # Get base URL without query string
        base = self.base_url.split('?')[0]
        
        # Filter out None/empty values
        clean_params = [(k, v) for k, v in params.items()
                       if v not in (None, '', 'None')]
        
        # Build query string
        query_string = urlencode(clean_params)
        
        return f"{base}?{query_string}"


# ============================================================================
# PART 4: FEED VALIDATOR (Lightweight wrapper)
# ============================================================================

class FeedValidator:
    """
    Lightweight feed validator.
    
    Note: This is a simple validator. For production, use validator_agent.py
    with Gemini-powered validation for better accuracy.
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize validator.
        
        Args:
            timeout: HTTP request timeout
        """
        self.timeout = timeout
        self.cache = {}
        
        logger.info("Feed Validator initialized")
    
    def validate(self, url: str) -> Tuple[bool, Dict]:
        """
        Validate if URL is a valid RSS/Atom feed.
        
        Args:
            url: Feed URL to validate
            
        Returns:
            Tuple of (is_valid, metadata)
        """
        
        # Check cache
        if url in self.cache:
            return self.cache[url]
        
        try:
            # Use GET with a browser-like User-Agent to avoid simple bot blocks
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; BharatConnect/2.0; +https://example.com)"
            }
            response = requests.get(url, timeout=self.timeout, allow_redirects=True, headers=headers)

            if response.status_code >= 400:
                self.cache[url] = (False, {"error": f"HTTP {response.status_code}", "http_status": response.status_code})
                logger.info(f"   HEAD/GET failed for {url} -> HTTP {response.status_code}")
                return False, {"error": f"HTTP {response.status_code}", "http_status": response.status_code}

            content = response.text

            # Parse feed from fetched content (more reliable than letting feedparser fetch)
            feed = feedparser.parse(content)

            # Check if valid (has entries and feed-level info)
            item_count = len(feed.entries) if hasattr(feed, 'entries') else 0
            is_valid = item_count > 0

            metadata = {
                "url": url,
                "title": feed.feed.get("title", "Untitled") if getattr(feed, 'feed', None) else "Untitled",
                "item_count": item_count,
                "valid": is_valid,
                "http_status": response.status_code,
                "sample": content[:500]
            }

            logger.info(f"   Feed fetched {url} -> HTTP {response.status_code}, items={item_count}")

            self.cache[url] = (is_valid, metadata)

            return is_valid, metadata
        
        except Exception as e:
            self.cache[url] = (False, {"error": str(e)})
            return False, {"error": str(e)}
    
    def validate_batch(self, urls: List[str]) -> List[Dict]:
        """
        Validate multiple URLs.
        
        Args:
            urls: List of URLs
            
        Returns:
            List of valid feed metadata
        """
        valid_feeds = []
        
        for url in urls:
            is_valid, metadata = self.validate(url)
            if is_valid:
                valid_feeds.append(metadata)
        
        return valid_feeds


# ============================================================================
# PART 5: MAIN RAG AGENT
# ============================================================================

class RAGAgent:
    """
    Main RAG (Retrieval-Augmented Generation) Agent for feed discovery.
    
    Orchestrates:
    - Pattern learning
    - URL generation
    - Feed validation
    - Iterative improvement
    """
    
    def __init__(self,
                 project_id: str,
                 base_url: str,
                 location: str = "us-central1"):
        """
        Initialize RAG Agent.
        
        Args:
            project_id: Google Cloud project ID
            base_url: Base feed URL
            location: Vertex AI location
        """
        self.project_id = project_id
        self.base_url = base_url
        self.location = location
        
    # Initialize components
        self.pattern_learner = GeminiPatternLearner(project_id, location)
        self.url_generator = IntelligentURLGenerator(base_url)
        self.feed_validator = FeedValidator()
        # Use AI validator for RAG candidate validation to match legit URL flow
        try:
            self.ai_validator = AIValidatorAgent(project_id=project_id)
        except Exception:
            # If AI validator cannot be initialized (no credentials / env),
            # fall back to lightweight validator to keep process working.
            self.ai_validator = None
        
        # State
        self.learned_patterns = {}
        self.discovered_feeds = []
        self.iteration_count = 0
        # Optional run id (set by Coordinator when running under an experiment)
        self.run_id = None
        
        # Statistics
        self.stats = {
            "total_urls_generated": 0,
            "total_urls_tested": 0,
            "total_feeds_discovered": 0,
            "iterations": []
        }
        
        logger.info(f"RAG Agent initialized for {base_url}")
    
    def learn_patterns(self, feeds: List[Dict]) -> Dict:
        """
        Learn patterns from discovered feeds.
        
        Args:
            feeds: List of discovered feeds
            
        Returns:
            Learned patterns
        """
        logger.info(f"Learning patterns from {len(feeds)} feeds...")
        
        # Analyze URL structure
        analyzer = URLStructureAnalyzer(feeds)
        structure = analyzer.analyze()
        
        logger.info(f"   Parameters found: {list(structure.get('parameters', {}).keys())}")
        
        # Learn with Gemini
        domain = urlparse(self.base_url).netloc
        patterns = self.pattern_learner.learn_patterns(feeds, domain)
        
        # Merge structure and patterns
        self.learned_patterns = {**structure, **patterns}

        logger.info("Pattern learning complete")
        
        return self.learned_patterns
    
    def generate_candidates(self, strategy: str = "hybrid", num_candidates: int = 50) -> List[str]:
        """
        Generate candidate URLs.
        
        Args:
            strategy: Generation strategy
            num_candidates: Number of candidates to generate
            
        Returns:
            List of candidate URLs
        """
        
        # Update generator with learned patterns
        self.url_generator.patterns = self.learned_patterns
        
        # Generate candidates
        candidates = self.url_generator.generate_candidates(strategy, num_candidates)
        
        self.stats["total_urls_generated"] += len(candidates)
        
        # Log top candidates
        logger.info("Top candidates:")
        for i, url in enumerate(candidates[:5], 1):
            logger.info(f"   {i}. {url}")
        
        return candidates
    
    def validate_candidates(self, candidates: List[str]) -> List[Dict]:
        """
        Validate candidate URLs.
        
        Args:
            candidates: List of candidate URLs
            
        Returns:
            List of valid feeds
        """
        logger.info(f"Validating {len(candidates)} candidates using AI validator...")

        # Prefer AI validator to perform the same validation as legit URLs.
        if self.ai_validator:
            result = self.ai_validator.validate_batch(candidates, source='rag', run_id=getattr(self, 'run_id', None))
            validated = result.get("validated_feeds", [])
            rejected = result.get("rejected_feeds", [])

            self.stats["total_urls_tested"] += len(candidates)
            self.stats["total_feeds_discovered"] += len(validated)

            # AI validator returns rich reports for this batch; append them to discovered_feeds
            for rep in validated:
                if isinstance(rep, dict) and rep.get("url"):
                    self.discovered_feeds.append(rep)

            logger.info(f"Validation complete: {len(validated)} new feeds found (AI)")
            return {
                "validated": validated,
                "rejected": rejected,
                "validated_reports": validated,
                "rejected_reports": rejected
            }
        else:
            # Fallback to lightweight validator if AI is unavailable
            logger.warning("AI validator unavailable, falling back to lightweight validator")
            valid_feeds = self.feed_validator.validate_batch(candidates)

            self.stats["total_urls_tested"] += len(candidates)
            self.stats["total_feeds_discovered"] += len(valid_feeds)

            # normalize lightweight metadata into discovered_feeds
            for meta in valid_feeds:
                self.discovered_feeds.append(meta)

            logger.info(f"Validation complete: {len(valid_feeds)} new feeds found (lightweight)")
            return {
                "validated": valid_feeds,
                "rejected": [],
                "validated_reports": valid_feeds,
                "rejected_reports": []
            }
    
    def run_iteration(self,
                     current_feeds: List[Dict],
                     strategy: str = "hybrid",
                     num_candidates: int = 50) -> Dict:
        """
        Run single RAG iteration.
        
        Args:
            current_feeds: Currently discovered feeds
            strategy: Generation strategy
            num_candidates: Number of candidates to generate
            
        Returns:
            Iteration results
        """
        
        self.iteration_count += 1
        
        logger.info(f"\nRAG Iteration {self.iteration_count}")
        logger.info("=" * 80)
        
        # Learn patterns
        self.learn_patterns(current_feeds)

        # Generate candidates
        candidates = self.generate_candidates(strategy, num_candidates)

        # Validate
        validation_outcome = self.validate_candidates(candidates)

        validated = validation_outcome.get("validated", [])
        rejected = validation_outcome.get("rejected", [])

        # Record iteration
        iteration_result = {
            "iteration": self.iteration_count,
            "candidates_generated": len(candidates),
            "validated_count": len(validated),
            "rejected_count": len(rejected),
            "new_feeds_found": len(validated),
            "total_feeds": len(self.discovered_feeds),
            "strategy": strategy,
            "validated_reports": validation_outcome.get("validated_reports", []),
            "rejected_reports": validation_outcome.get("rejected_reports", [])
        }
        
        self.stats["iterations"].append(iteration_result)
        
        logger.info(f"Iteration {self.iteration_count} Summary:")
        logger.info(f"   Generated: {len(candidates)}")
        logger.info(f"   Valid: {len(validated)}")
        logger.info(f"   Total so far: {len(self.discovered_feeds)}")

        return iteration_result
    
    def should_stop_iteration(self) -> Tuple[bool, str]:
        """
        Check if iterations should stop (convergence detection).
        
        Returns:
            Tuple of (should_stop, reason)
        """
        if self.iteration_count < 2:
            return False, "Need more iterations"
        
        # Check last 2 iterations
        recent = self.stats["iterations"][-2:]
        
        if all(it["new_feeds_found"] == 0 for it in recent):
            return True, "No new feeds in last 2 iterations"
        
        return False, "Still discovering feeds"
    
    def get_stats(self) -> Dict:
        """Get discovery statistics."""
        return {
            "total_discovered_feeds": len(self.discovered_feeds),
            "total_urls_generated": self.stats["total_urls_generated"],
            "total_urls_tested": self.stats["total_urls_tested"],
            "success_rate": (len(self.discovered_feeds) / max(1, self.stats["total_urls_tested"])),
            "iterations_completed": self.iteration_count,
            "iteration_history": self.stats["iterations"]
        }
    
    def save_results(self, filename: str = "rag_results.json"):
        """Save results to file."""
        results = {
            "metadata": {
                "base_url": self.base_url,
                "timestamp": datetime.now().isoformat(),
                "iterations": self.iteration_count
            },
            "discovered_feeds": self.discovered_feeds,
            "statistics": self.get_stats(),
            "learned_patterns": self.learned_patterns
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")


# ============================================================================
# PART 6: EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of the RAG Agent.
    """
    
    # Configuration
    PROJECT_ID = "bharat-connect-000"
    BASE_URL = "https://pib.gov.in/RssMain.aspx"
    
    # Initialize RAG Agent
    rag_agent = RAGAgent(PROJECT_ID, BASE_URL)
    
    # Example: Seed feeds from initial discovery
    seed_feeds = [
        {"url": "https://pib.gov.in/RssMain.aspx?ModId=1&Lang=8&Regid=1"},
        {"url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=18&Regid=2"},
    ]
    
    # Run iteration
    result = rag_agent.run_iteration(
        current_feeds=seed_feeds,
        strategy="hybrid",
        num_candidates=50
    )
    
    print(f"\nIteration complete: {result['new_feeds_found']} new feeds discovered")
    
    # Save results
    rag_agent.save_results("rag_discovery_results.json")
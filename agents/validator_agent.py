"""
validator_agent.py - AI-Powered Feed Validator (Gemini-based)
=============================================================

Uses Gemini AI to intelligently validate RSS feeds instead of hard rules.

This agent is responsible for:
1. Fetching feed content
2. Using Gemini to assess quality
3. Extracting meaningful insights
4. Quality scoring (0-100)
5. Duplicate detection
"""

import feedparser
import requests
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
import json
import time
from validation_store import ValidationStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIValidatorAgent:
    """
    AI-powered feed validator using Gemini.
    
    Purpose: Use AI to intelligently validate feeds instead of hard rules
    
    Benefits:
    - Understands feed context and relevance
    - Can assess content quality semantically
    - Adapts to different feed types
    - Provides reasoning for validation decisions
    """
    
    def __init__(self, 
                 project_id: str,
                 min_quality_score: int = 60,
                 timeout: int = 10,
                 location: str = "us-central1"):
        """
        Initialize AI validator agent.
        
        Args:
            project_id: Google Cloud project ID
            min_quality_score: Minimum quality score to accept (0-100)
            timeout: HTTP request timeout in seconds
            location: Vertex AI location
        """
        
        self.project_id = project_id
        self.min_quality_score = min_quality_score
        self.timeout = timeout
        
        # Initialize Gemini
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel("gemini-2.0-flash")
        self.config = GenerationConfig(
            temperature=0.3,  # Slightly lower for consistency
            max_output_tokens=1024,
            response_mime_type="application/json"
        )
        
        # Enforce one call per `api_delay` seconds (counted from the moment
        # the previous call's response was received). Use 60s to respect
        # strict per-minute quotas.
        self.api_delay = 60.0  # seconds
        self.last_api_call = 0.0
        
        # State tracking
        self.validation_cache = {}
        self.url_hashes = {}
        self.validated_feeds = []
        self.rejected_feeds = []
        # Persistence store
        try:
            self.store = ValidationStore()
        except Exception:
            self.store = None
        
        logger.info(f"AIValidatorAgent initialized (min_quality: {min_quality_score})")
    
    def _rate_limit(self):
        """Enforce API rate limiting."""
        current = time.time()
        elapsed = current - self.last_api_call
        if elapsed < self.api_delay:
            time.sleep(self.api_delay - elapsed)
        self.last_api_call = time.time()

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
    
    def validate_feed(self, url: str, source: str = "legit", run_id: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        Validate feed using Gemini AI.
        
        Args:
            url: RSS feed URL to validate
            
        Returns:
            Tuple of (is_valid, validation_report)
        """
        
        # Handle dict input (from checkpoint)
        if isinstance(url, dict):
            url = url.get("url", "")
            if not url:
                report = {"url": url, "valid": False, "errors": ["No URL in feed dictionary"], "timestamp": datetime.now().isoformat()}
                if getattr(self, 'store', None):
                    try:
                        self.store.save_report(url=url, source=source, validator='ai', valid=False, report=report, run_id=run_id)
                    except Exception:
                        pass
                return False, report
        
        url = str(url).strip()
        
        if not url or not url.startswith("http"):
            report = {"url": url, "valid": False, "errors": ["Invalid URL format"], "timestamp": datetime.now().isoformat()}
            if getattr(self, 'store', None):
                try:
                    self.store.save_report(url=url, source=source, validator='ai', valid=False, report=report, run_id=run_id)
                except Exception:
                    pass
            return False, report
        
        # Check cache
        if url in self.validation_cache:
            return self.validation_cache[url]
        
        report = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "valid": False,
            "score": 0,
            "reasoning": "",
            "errors": [],
            "warnings": []
        }
        
        logger.info(f"AI Validating: {url[:60]}...")
        
        # Step 1: Fetch content
        try:
            response = requests.get(url, timeout=self.timeout)
            content = response.text[:5000]  # First 5000 chars
            report["http_status"] = response.status_code
            
            if response.status_code >= 400:
                report["errors"].append(f"HTTP {response.status_code}")
                self.validation_cache[url] = (False, report)
                self.rejected_feeds.append(report)
                if getattr(self, 'store', None):
                    try:
                        self.store.save_report(url=url, source=source, validator='ai', valid=False, report=report, run_id=run_id)
                    except Exception:
                        pass
                return False, report
        
        except requests.exceptions.Timeout:
            report["errors"].append("HTTP request timeout")
            self.validation_cache[url] = (False, report)
            self.rejected_feeds.append(report)
            if getattr(self, 'store', None):
                try:
                    self.store.save_report(url=url, source=source, validator='ai', valid=False, report=report, run_id=run_id)
                except Exception:
                    pass
            return False, report
        
        except Exception as e:
            report["errors"].append(f"Connection failed: {str(e)[:50]}")
            self.validation_cache[url] = (False, report)
            self.rejected_feeds.append(report)
            if getattr(self, 'store', None):
                try:
                    self.store.save_report(url=url, source=source, validator='ai', valid=False, report=report, run_id=run_id)
                except Exception:
                    pass
            return False, report
        
        # Step 2: Check if it's RSS/Atom
        if not self._is_feed_format(content):
            report["errors"].append("Not a valid RSS/Atom feed")
            self.validation_cache[url] = (False, report)
            self.rejected_feeds.append(report)
            if getattr(self, 'store', None):
                try:
                    self.store.save_report(url=url, source=source, validator='ai', valid=False, report=report, run_id=run_id)
                except Exception:
                    pass
            return False, report
        
        # Step 3: Use Gemini for AI validation
        try:
            ai_assessment = self._assess_with_gemini(url, content)
            
            report.update(ai_assessment)
            
            # Final decision
            report["valid"] = (report["score"] >= self.min_quality_score and 
                             len(report["errors"]) == 0)
            
            if report["valid"]:
                logger.info(f"   Valid (AI score: {report['score']}/100)")
                self.validated_feeds.append(report)
            else:
                logger.info(f"   Invalid (AI score: {report['score']}/100)")
                self.rejected_feeds.append(report)

            # Persist report
            if getattr(self, 'store', None):
                try:
                    self.store.save_report(url=url, source=source, validator='ai', valid=report.get('valid', False), report=report, quality_score=report.get('score'), run_id=run_id)
                except Exception:
                    pass

            self.validation_cache[url] = (report["valid"], report)
            return report["valid"], report
        
        except Exception as e:
            logger.error(f"AI assessment failed: {e}")
            report["errors"].append(f"AI assessment failed: {str(e)[:50]}")
            self.validation_cache[url] = (False, report)
            self.rejected_feeds.append(report)
            return False, report
    
    def _is_feed_format(self, content: str) -> bool:
        """Quick check if content is RSS/Atom."""
        signatures = ["<rss", "<feed", "<?xml", "xmlns"]
        return any(sig in content.lower()[:2000] for sig in signatures)
    
    def _assess_with_gemini(self, url: str, content: str) -> Dict:
        """Use Gemini to assess feed quality."""
        
        # Parse with feedparser first to get basic info
        feed = feedparser.parse(content)
        
        prompt = f"""Analyze this RSS feed and provide a quality assessment.

URL: {url}
Feed Title: {feed.feed.get('title', 'N/A')}
Feed Description: {feed.feed.get('description', 'N/A')[:200]}
Number of Items: {len(feed.entries)}
First Item Title: {feed.entries[0].get('title', 'N/A') if feed.entries else 'N/A'}
Feed Language: {feed.feed.get('language', 'N/A')}

First 500 chars of feed content:
{content[:500]}

Assess this feed on these criteria:
1. Feed Validity: Is it a legitimate, well-formed feed?
2. Content Quality: Does it have meaningful content?
3. Update Frequency: Based on timestamps, how active is it?
4. Metadata Completeness: Does it have proper title, description, etc?
5. Usefulness: Would this feed be valuable to aggregate?

Respond ONLY with this JSON (no other text):
{{
  "is_valid": true/false,
  "quality_score": 0-100,
  "reasoning": "Brief explanation",
  "feed_type": "RSS/Atom/etc",
  "content_type": "News/Blog/etc",
  "update_frequency": "Daily/Weekly/etc",
  "recommendation": "Accept/Reject/Review"
}}
"""
        
        # Enforce a total retry/time budget for Gemini calls (e.g. 60s).
        max_total_wait = 60.0
        backoff = 2
        attempt = 0
        start_time = time.time()

        fallback_assessment = {
            "score": 50,
            "reasoning": "Fallback due to Gemini error or quota",
            "feed_type": "Unknown",
            "content_type": "Unknown",
            "update_frequency": "Unknown",
            "recommendation": "Review"
        }

        while True:
            attempt += 1
            elapsed_total = time.time() - start_time
            remaining_time = max_total_wait - elapsed_total
            if remaining_time <= 0:
                logger.error("Gemini retries/time budget exhausted; returning fallback assessment")
                return fallback_assessment

            # Wait for API slot (measured from last response time). If we
            # don't have enough time to wait, bail out with fallback.
            slot_ok = self._wait_for_api_slot(max_wait=remaining_time)
            if not slot_ok:
                logger.warning("Not enough time to wait for API slot; returning fallback assessment")
                return fallback_assessment

            try:
                response = self.model.generate_content(prompt, generation_config=self.config)

                # We received a response — record the response time as
                # the last_api_call so next call will be delayed from now.
                self.last_api_call = time.time()

                # Parse response
                text = response.text.strip()
                if text.startswith("```"):
                    # strip fenced code block
                    parts = text.split("```")
                    if len(parts) >= 2:
                        text = parts[1]
                        if text.startswith("json"):
                            text = text[4:]

                # Load JSON (Gemini sometimes returns arrays)
                try:
                    assessment = json.loads(text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Gemini response (attempt {attempt}): {e}")
                    # If we still have time, back off a bit and retry.
                    elapsed_total = time.time() - start_time
                    remaining_time = max_total_wait - elapsed_total
                    if remaining_time <= 0:
                        return fallback_assessment
                    sleep = min(backoff * (2 ** (attempt - 1)), max(1, remaining_time))
                    time.sleep(sleep)
                    continue

                # If we got a list, try to pick the first object
                if isinstance(assessment, list):
                    if len(assessment) > 0 and isinstance(assessment[0], dict):
                        assessment = assessment[0]
                    else:
                        logger.warning("Gemini returned a JSON list that couldn't be interpreted; falling back to neutral assessment")
                        return fallback_assessment

                # Defensive: ensure assessment is a dict
                if not isinstance(assessment, dict):
                    logger.warning("Gemini response parsed but is not an object; using fallback assessment")
                    return fallback_assessment

                return {
                    "score": assessment.get("quality_score", 0),
                    "reasoning": assessment.get("reasoning", ""),
                    "feed_type": assessment.get("feed_type", "Unknown"),
                    "content_type": assessment.get("content_type", "Unknown"),
                    "update_frequency": assessment.get("update_frequency", "Unknown"),
                    "recommendation": assessment.get("recommendation", "Review")
                }

            except Exception as e:
                msg = str(e)
                logger.error(f"Gemini assessment error (attempt {attempt}): {msg}")
                # If it's a quota/resource issue, treat it as a response time
                # (we got a quota response) and back off then retry until
                # the total time budget is exhausted.
                if ("429" in msg) or ("Resource exhausted" in msg) or ("quota" in msg.lower()):
                    # mark last_api_call so next call will wait from now
                    self.last_api_call = time.time()
                    elapsed_total = time.time() - start_time
                    remaining_time = max_total_wait - elapsed_total
                    if remaining_time <= 0:
                        logger.error("Gemini quota exceeded after retries; returning fallback assessment")
                        return fallback_assessment
                    sleep = min(backoff * (2 ** (attempt - 1)), max(1, remaining_time))
                    logger.warning(f"Gemini quota/429 detected, backing off for {sleep}s and retrying...")
                    time.sleep(sleep)
                    continue
                # Non-retryable error -> raise to let caller record it
                raise
    
    def validate_batch(self, feeds: List, source: str = "legit", run_id: Optional[str] = None) -> Dict:
        """
        Validate multiple feeds using AI.
        
        Args:
            feeds: List of feed dicts or URLs
            
        Returns:
            Validation summary
        """
        
        logger.info(f"AI Validating {len(feeds)} feeds...")

        # Extract URLs
        urls_to_validate = []
        for feed in feeds:
            if isinstance(feed, dict):
                url = feed.get("url")
                if url:
                    urls_to_validate.append(url)
            elif isinstance(feed, str):
                urls_to_validate.append(feed)

        # Validate each and collect batch-local results
        batch_validated = []
        batch_rejected = []

        for url in urls_to_validate:
            try:
                valid, report = self.validate_feed(url, source=source, run_id=run_id)
            except Exception as e:
                # If validate_feed raises, record as rejected
                report = {"url": url, "valid": False, "errors": [str(e)], "timestamp": datetime.now().isoformat()}
                valid = False

            if valid:
                batch_validated.append(report)
            else:
                batch_rejected.append(report)

        valid_count = len(batch_validated)
        invalid_count = len(batch_rejected)
        total = len(urls_to_validate)

        return {
            "total_tested": total,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "success_rate": valid_count / max(1, total),
            "validated_feeds": batch_validated,
            "rejected_feeds": batch_rejected
        }
    
    def get_stats(self) -> Dict:
        """Get validation statistics."""
        
        total = len(self.validated_feeds) + len(self.rejected_feeds)
        
        if total == 0:
            return {
                "total_validated": 0,
                "valid_count": 0,
                "rejected_count": 0,
                "success_rate": 0,
                "avg_quality_score": 0
            }
        
        avg_quality = sum(f.get("score", 0) for f in self.validated_feeds) / len(self.validated_feeds) if self.validated_feeds else 0
        
        return {
            "total_validated": total,
            "valid_count": len(self.validated_feeds),
            "rejected_count": len(self.rejected_feeds),
            "success_rate": len(self.validated_feeds) / total,
            "avg_quality_score": avg_quality
        }


# Keep old class name for backward compatibility
class ValidatorAgent(AIValidatorAgent):
    """Backward compatible alias for AIValidatorAgent."""
    pass


if __name__ == "__main__":
    validator = AIValidatorAgent(
        project_id="bharat-connect-000",
        min_quality_score=60
    )
    
    # Test URLs
    test_feeds = [
        {"url": "https://pib.gov.in/RssMain.aspx?ModId=1&Lang=8&Regid=1"},
        "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=18&Regid=2"
    ]
    
    results = validator.validate_batch(test_feeds)

    print(f"\nAI Validation Results:")
    print(f"   Valid: {results['valid_count']}")
    print(f"   Invalid: {results['invalid_count']}")
    print(f"   Success Rate: {results['success_rate']:.1%}")
    print(f"   Avg Quality: {validator.get_stats()['avg_quality_score']:.1f}/100")

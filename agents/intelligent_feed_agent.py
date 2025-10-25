"""
ultimate_ai_scraper.py - TWO-STAGE INTELLIGENT FEED DISCOVERY

Stage 1: Fast heuristic-based link discovery using Selenium
Stage 2: Deep AI-powered analysis for non-obvious feeds
"""

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
from typing import List, Dict, Set, Tuple
from datetime import datetime
import time
import requests
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import NoAlertPresentException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium_stealth import stealth
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("WARNING: Install: pip install selenium selenium-stealth webdriver-manager")


class UltimateAIScraper:
    def __init__(self, project_id: str, location: str = "us-central1"):
        print("\n" + "="*80)
        print("TWO-STAGE INTELLIGENT RSS DISCOVERY")
        print("="*80 + "\n")
        
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel("gemini-2.0-flash-exp")
        self.config = GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            max_output_tokens=8192,
            response_mime_type="application/json"
        )
        
        self.driver = None
        self.discovered_feeds: List[Dict] = []
        self.visited_urls: Set[str] = set()
        self.seen_feed_urls: Set[str] = set()
        
        # API rate limiting: prefer one call per minute to avoid quota
        self.api_delay = 60.0  # seconds
        self.last_api_call = 0.0
        
        print("Gemini 2.0 Flash initialized\n")

    def _wait_for_api_slot(self, max_wait: float = None) -> bool:
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

    def _init_selenium(self):
        if self.driver or not SELENIUM_AVAILABLE:
            return
        
        print("Initializing Selenium...")
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        stealth(self.driver, 
                languages=["en-US"], 
                vendor="Google Inc.",
                platform="Win32", 
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine", 
                fix_hairline=True)
        
        print("Selenium ready\n")

    def _extract_cascading_dropdowns_live(self, url: str) -> List[Dict]:
        """Extract ALL dropdown combinations by interacting with cascading dropdowns."""
        print("Extracting cascading dropdown values using Selenium...\n")
        
        self._init_selenium()
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            all_combos = []
            
            selects = self.driver.find_elements(By.TAG_NAME, 'select')
            
            if len(selects) == 0:
                print("No dropdowns found\n")
                return []
            
            primary_select = selects[0]
            primary_name = primary_select.get_attribute('name')
            primary_obj = Select(primary_select)
            
            primary_options = []
            for opt in primary_obj.options:
                value = opt.get_attribute('value')
                text = opt.text
                if value and value.strip() and value != "0":
                    primary_options.append({'value': value.strip(), 'text': text.strip()})
            
            print(f"Primary dropdown '{primary_name}': {len(primary_options)} options")
            
            for i, primary_opt in enumerate(primary_options, 1):
                print(f"  [{i}/{len(primary_options)}] Testing {primary_opt['text']}...")
                
                try:
                    self.driver.get(url)
                    time.sleep(2)
                    
                    primary_select = self.driver.find_element(By.NAME, primary_name)
                    primary_obj = Select(primary_select)
                    primary_obj.select_by_value(primary_opt['value'])
                    time.sleep(2)
                    
                    current_combo = {primary_name: primary_opt['value']}
                    current_selects = self.driver.find_elements(By.TAG_NAME, 'select')
                    
                    for select_elem in current_selects:
                        name = select_elem.get_attribute('name')
                        if name == primary_name:
                            continue
                        
                        select_obj = Select(select_elem)
                        
                        for opt in select_obj.options:
                            value = opt.get_attribute('value')
                            if value and value.strip() and value != "0":
                                combo_copy = current_combo.copy()
                                combo_copy[name] = value.strip()
                                all_combos.append(combo_copy)
                
                except Exception as e:
                    print(f"    Error: {str(e)[:60]}")
                    continue
            
            print(f"\nTotal combinations discovered: {len(all_combos)}\n")
            return all_combos
            
        except Exception as e:
            print(f"Error extracting cascading dropdowns: {e}\n")
            return []

    def _stage1_fast_heuristic_extraction(self, page_html: str, base_url: str) -> List[Dict]:
        """STAGE 1: Comprehensive heuristic-based extraction."""
        print("Stage 1: Comprehensive heuristic extraction...")
        
        feeds = []
        
        try:
            soup = BeautifulSoup(page_html, 'html.parser')
            all_links = soup.find_all('a', href=True)
            
            print(f"    Analyzing {len(all_links)} links on page...")
            
            for link in all_links:
                try:
                    href = link.get('href', '').strip()
                    text = link.get_text().strip()
                    title_attr = link.get('title', '').strip()
                    
                    if not href:
                        continue
                    
                    is_feed = False
                    confidence = 'low'
                    
                    # Strategy 1: URL patterns
                    url_patterns = [
                        r'\.xml$',
                        r'\.rss$',
                        r'/feed/',
                        r'/rss/',
                        r'RelId=',
                        r'rss',
                        r'feed',
                        r'atom',
                        r'RssMain',
                    ]
                    
                    for pattern in url_patterns:
                        if re.search(pattern, href, re.IGNORECASE):
                            is_feed = True
                            if pattern in [r'\.xml$', r'\.rss$']:
                                confidence = 'high'
                            else:
                                confidence = 'medium'
                            break
                    
                    # Strategy 2: Link text contains RSS/Feed keywords
                    text_keywords = ['rss', 'feed', 'atom', 'xml', 'subscribe']
                    if text.lower() in text_keywords or any(keyword in text.lower() for keyword in text_keywords):
                        is_feed = True
                        if confidence == 'low':
                            confidence = 'medium'
                    
                    # Strategy 3: Title attribute
                    if any(keyword in title_attr.lower() for keyword in text_keywords):
                        is_feed = True
                        if confidence == 'low':
                            confidence = 'medium'
                    
                    # Strategy 4: Link class or id
                    link_class = ' '.join(link.get('class', [])).lower()
                    link_id = link.get('id', '').lower()
                    if 'rss' in link_class or 'feed' in link_class or 'rss' in link_id or 'feed' in link_id:
                        is_feed = True
                        if confidence == 'low':
                            confidence = 'medium'
                    
                    if is_feed:
                        full_url = urljoin(base_url, href)
                        
                        if full_url in self.seen_feed_urls:
                            continue
                        
                        feed_title = text if text else (title_attr if title_attr else 'RSS Feed')
                        
                        feeds.append({
                            'url': full_url,
                            'title': feed_title,
                            'confidence': confidence
                        })
                        self.seen_feed_urls.add(full_url)
                        
                        print(f"    Found: {feed_title[:40]} [{confidence}]")
                        
                except Exception as e:
                    continue
            
            print(f"    Extracted {len(feeds)} potential feed URLs\n")
            return feeds
            
        except Exception as e:
            print(f"    Extraction error: {e}\n")
            return []

    def _stage2_ai_deep_analysis(self, html: str, url: str) -> List[Dict]:
        """STAGE 2: Deep AI-powered analysis for non-obvious feeds."""
        print("Stage 2: AI deep analysis...")
        
        html_sample = html[:150000]
        
        prompt = f"""Analyze this page to find RSS/Atom feed URLs that might not be obvious.

URL: {url}

HTML:
{html_sample}

YOUR TASK:
Find feed URLs that might be hidden or non-obvious:
1. JavaScript-generated URLs
2. Data attributes (data-feed-url, etc.)
3. Hidden links or buttons
4. API endpoints that serve feeds
5. URLs in <link rel="alternate"> tags
6. Embedded JSON/JavaScript containing feed URLs

Be creative - look beyond obvious <a> tags.

RESPOND WITH JSON:
[
  {{"url": "https://actual-feed-url.xml", "title": "Feed Title", "confidence": "high"}},
  {{"url": "https://api.site.com/feed/123", "title": "API Feed", "confidence": "medium"}}
]

Return [] if none found.
"""
        
        # Use bounded retry/time budget and respect api slot (1/min). On
        # exhaustion return an empty list (no suggestions).
        max_total_wait = 60.0
        backoff = 2
        attempt = 0
        start_time = time.time()

        while True:
            attempt += 1
            elapsed_total = time.time() - start_time
            remaining_time = max_total_wait - elapsed_total
            if remaining_time <= 0:
                print("    AI analysis retries/time budget exhausted; returning no feeds\n")
                return []

            slot_ok = self._wait_for_api_slot(max_wait=remaining_time)
            if not slot_ok:
                print("    Not enough time to wait for API slot; returning no feeds\n")
                return []

            try:
                response = self.model.generate_content(prompt, generation_config=self.config)

                # Record response time
                self.last_api_call = time.time()

                cleaned = response.text
                cleaned = re.sub(r'\s*```$', '', cleaned)
                feeds = json.loads(cleaned.strip())

                new_feeds = [f for f in feeds if f.get('url') not in self.seen_feed_urls]

                for feed in new_feeds:
                    self.seen_feed_urls.add(feed.get('url', ''))

                print(f"    Found {len(new_feeds)} additional feed URLs\n")
                return new_feeds if isinstance(new_feeds, list) else []

            except Exception as e:
                msg = str(e)
                print(f"    AI analysis error (attempt {attempt}): {msg}\n")
                if ("429" in msg) or ("Resource exhausted" in msg) or ("quota" in msg.lower()):
                    # treat as response time and back off
                    self.last_api_call = time.time()
                    elapsed_total = time.time() - start_time
                    remaining_time = max_total_wait - elapsed_total
                    if remaining_time <= 0:
                        print("    Gemini quota exceeded after retries; returning no feeds\n")
                        return []
                    sleep = min(backoff * (2 ** (attempt - 1)), max(1, remaining_time))
                    print(f"    Gemini quota/429 detected, backing off for {sleep}s and retrying...")
                    time.sleep(sleep)
                    continue
                else:
                    return []

    def _intelligent_feed_discovery(self, page_html: str, page_url: str) -> List[Dict]:
        """Two-stage intelligent feed discovery with fallback."""
        stage1_feeds = self._stage1_fast_heuristic_extraction(page_html, page_url)
        
        if len(stage1_feeds) >= 2:
            print(f"    Stage 1 sufficient ({len(stage1_feeds)} feeds)\n")
            return stage1_feeds
        
        print(f"    Stage 1 found only {len(stage1_feeds)} feeds - triggering Stage 2")
        stage2_feeds = self._stage2_ai_deep_analysis(page_html, page_url)
        
        all_feeds = stage1_feeds + stage2_feeds
        print(f"    Total: {len(all_feeds)} feeds\n")
        
        return all_feeds

    def _learn_url_pattern_robust(self, base_url: str, test_combos: List[Dict], num_tests: int = 5) -> Dict:
        """Learn URL parameter pattern by testing multiple combinations."""
        print(f"Learning URL parameter pattern (testing up to {num_tests} combos)...\n")
        
        param_mapping = {}
        successful_tests = 0
        
        try:
            for attempt, combo in enumerate(test_combos[:num_tests], 1):
                print(f"  [Test {attempt}/{min(num_tests, len(test_combos))}]")
                print(f"    Combo: {combo}")
                
                self.driver.get(base_url)
                time.sleep(2)
                
                all_set = True
                for dropdown_name, value in combo.items():
                    try:
                        select_elem = self.driver.find_element(By.NAME, dropdown_name)
                        select_obj = Select(select_elem)
                        select_obj.select_by_value(value)
                        time.sleep(0.8)
                    except Exception as e:
                        print(f"    Could not set {dropdown_name}={value}")
                        all_set = False
                        break
                
                if not all_set:
                    continue
                
                time.sleep(3)
                
                current_url = self.driver.current_url
                print(f"    Result: {current_url}")
                
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(current_url)
                params = parse_qs(parsed.query)
                
                if params:
                    successful_tests += 1
                    print(f"    Parameters: {list(params.keys())}")
                    
                    for param_name, param_values in params.items():
                        if param_values:
                            param_value = param_values[0]
                            
                            for dropdown_name, dropdown_value in combo.items():
                                if param_value == dropdown_value:
                                    if dropdown_name not in param_mapping:
                                        param_mapping[dropdown_name] = param_name
                                        print(f"    Learned: {dropdown_name.split('$')[-1]} → {param_name}")
                                    break
                else:
                    print(f"    No parameters in URL (might be default)")
                
                print()
                
                if len(param_mapping) >= len(combo):
                    print(f"Complete parameter mapping learned after {attempt} tests!")
                    print(f"   Mapping: {param_mapping}\n")
                    return param_mapping
            
            if param_mapping:
                print(f"Learned mapping from {successful_tests} successful tests:")
                print(f"   {param_mapping}\n")
                return param_mapping
            else:
                print(f"Could not learn URL pattern from {num_tests} tests\n")
                return {}
            
        except Exception as e:
            print(f"  Error during pattern learning: {e}\n")
            return {}

    def _construct_url_from_combo(self, base_url: str, combo: Dict, param_mapping: Dict) -> str:
        """Construct URL using learned parameter mapping."""
        from urllib.parse import urlencode
        
        mapped_params = {}
        for full_name, value in combo.items():
            short_name = param_mapping.get(full_name, full_name)
            mapped_params[short_name] = value
        
        param_string = urlencode(mapped_params)
        
        if '?' in base_url:
            return f"{base_url}&{param_string}"
        else:
            return f"{base_url}?{param_string}"

    def _safe_get(self, url: str) -> Tuple[bool, str]:
        """Safely navigate to URL and wait for JavaScript content."""
        try:
            self.driver.get(url)
            
            # Check for alert first
            try:
                alert = self.driver.switch_to.alert
                alert.accept()
                return False, ""
            except NoAlertPresentException:
                pass
            
            # Wait for RSS links to appear
            try:
                print(f"    Waiting for RSS links...")
                WebDriverWait(self.driver, 10).until(
                    lambda d: len(d.find_elements(By.XPATH, "//a[contains(@href, 'RssMain') or contains(@href, 'rss') or contains(@href, 'feed')]")) > 0
                )
                print(f"    Links loaded")
            except:
                print(f"    Fallback wait (5s)...")
                time.sleep(5)
            
            html = self.driver.page_source
            return True, html
                
        except Exception as e:
            return False, ""

    def discover(self, start_url: str, max_pages: int = 500) -> List[Dict]:
        """Main discovery method with robust URL pattern learning."""
        print(f"Target: {start_url}\n")
        
        start_time = datetime.now()
        
        combos = self._extract_cascading_dropdowns_live(start_url)
        
        if not combos:
            print("No dropdown combinations found - testing base URL\n")
            combos = [{}]
        
        if len(combos) > 5:
            test_indices = [
                0,
                len(combos) // 4,
                len(combos) // 2,
                3 * len(combos) // 4,
                len(combos) - 1
            ]
            test_combos = [combos[i] for i in test_indices]
        else:
            test_combos = combos
        
        print(f"Will test {len(test_combos)} combos for URL pattern learning\n")
        
        param_mapping = self._learn_url_pattern_robust(start_url, test_combos, num_tests=5)
        
        if len(combos) > max_pages:
            print(f"Limiting from {len(combos)} to {max_pages} combinations\n")
            combos = combos[:max_pages]
        
        print(f"Testing {len(combos)} combinations with two-stage extraction...\n")
        print("="*80 + "\n")
        
        for i, combo in enumerate(combos, 1):
            combo_key = str(sorted(combo.items()))
            if combo_key in self.visited_urls:
                continue
            
            self.visited_urls.add(combo_key)
            
            combo_display = ', '.join([f"{k.split('$')[-1]}={v}" for k, v in combo.items()]) if combo else "base page"
            print(f"[{i}/{len(combos)}] {combo_display[:70]}...")
            
            try:
                if combo and param_mapping:
                    test_url = self._construct_url_from_combo(start_url, combo, param_mapping)
                    print(f"  🔗 {test_url}")
                elif combo:
                    print(f"  No URL pattern - attempting form submission...")
                    self.driver.get(start_url)
                    time.sleep(2)
                    
                    for dropdown_name, value in combo.items():
                        try:
                            select_elem = self.driver.find_element(By.NAME, dropdown_name)
                            select_obj = Select(select_elem)
                            select_obj.select_by_value(value)
                            time.sleep(0.5)
                        except:
                            pass
                    
                    time.sleep(3)
                    test_url = self.driver.current_url
                    page_html = self.driver.page_source
                    success = True
                else:
                    test_url = start_url
                
                if not combo or param_mapping:
                    success, page_html = self._safe_get(test_url)
                
                if not success:
                    print(f"  Could not load\n")
                    continue
                
                feeds = self._intelligent_feed_discovery(page_html, test_url)
                
                if feeds:
                    print(f"  Discovered {len(feeds)} unique feeds")
                    
                    for feed_info in feeds:
                        url = feed_info.get('url', '')
                        title = feed_info.get('title', 'Untitled')
                        confidence = feed_info.get('confidence', 'unknown')
                        
                        if url and url not in [f['url'] for f in self.discovered_feeds]:
                            self.discovered_feeds.append({
                                'url': url,
                                'title': title,
                                'confidence': confidence,
                                'source_page': test_url,
                                'combo': combo,
                                'discovered_at': datetime.now().isoformat()
                            })
                            print(f"     {title[:50]} ({confidence})")
                else:
                    print(f"  No feeds found")
                    
            except Exception as e:
                print(f"  Error: {str(e)[:80]}")
            
            print()
        
        if self.driver:
            self.driver.quit()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*80)
        print("DISCOVERY COMPLETE")
        print("="*80)
        print(f"Duration: {duration:.1f}s")
        print(f"Combinations tested: {len(self.visited_urls)}")
        print(f"Unique feeds discovered: {len(self.discovered_feeds)}")
        print("="*80 + "\n")
        
        return self.discovered_feeds

    def save_results(self, filename: str = "discovered_feeds.json"):
        """Save results."""
        output = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_feeds': len(self.discovered_feeds),
                'combinations_tested': len(self.visited_urls)
            },
            'feeds': self.discovered_feeds
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Saved to: {filename}\n")


def main():
    """Main execution."""
    PROJECT_ID = "bharat-connect-000"
    TARGET_URL = "https://www.pib.gov.in/ViewRss.aspx"
    
    scraper = UltimateAIScraper(project_id=PROJECT_ID)
    feeds = scraper.discover(TARGET_URL, max_pages=500)
    scraper.save_results("pib_feeds_complete.json")
    
    print("DISCOVERED FEEDS:")
    print("-" * 80)
    for i, feed in enumerate(feeds[:50], 1):
        conf = feed.get('confidence', '?')
        print(f"{i:3d}. [{conf:6s}] {feed['title'][:55]:<55}")
    
    if len(feeds) > 50:
        print(f"\n... and {len(feeds) - 50} more feeds")


if __name__ == "__main__":
    main()

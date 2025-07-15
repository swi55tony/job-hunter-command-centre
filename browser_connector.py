# browser_connector.py - Connect to your existing browser session
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
from typing import Dict, List, Optional
from job_fetcher import Job
import logging
import re
from urllib.parse import urlencode

class ExistingBrowserConnector:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        """Connect to existing browser session"""
        self.playwright = await async_playwright().start()
        
        # Connect to existing Chrome instance
        # First, you need to start Chrome with debugging enabled
        try:
            print("🔗 Connecting to existing browser session...")
            self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            # Get the existing contexts/pages
            contexts = self.browser.contexts
            if contexts:
                # Use the first context
                context = contexts[0]
                pages = context.pages
                
                if pages:
                    # Use existing page or create new one
                    self.page = pages[0]
                    print(f"✅ Connected to existing page: {await self.page.title()}")
                else:
                    # Create new page in existing context
                    self.page = await context.new_page()
                    print("✅ Created new page in existing browser")
            else:
                print("❌ No contexts found in browser")
                return None
                
            self.is_connected = True
            return self
            
        except Exception as e:
            print(f"❌ Failed to connect to existing browser: {e}")
            print("💡 Make sure Chrome is running with --remote-debugging-port=9222")
            return None
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close the browser - we're just disconnecting
        if self.playwright:
            await self.playwright.stop()
    
    async def navigate_to_upwork(self):
        """Navigate to Upwork in the existing browser"""
        try:
            current_url = self.page.url
            print(f"📍 Current page: {current_url}")
            
            if 'upwork.com' not in current_url:
                print("🌐 Navigating to Upwork...")
                await self.page.goto('https://www.upwork.com/nx/find-work/')
                await asyncio.sleep(3)
            
            # Check if we're logged in
            page_content = await self.page.inner_text('body')
            if 'login' in page_content.lower() or 'sign in' in page_content.lower():
                print("❌ Not logged in to Upwork")
                print("💡 Please log in manually in your browser first")
                return False
            else:
                print("✅ Already logged in to Upwork!")
                return True
                
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False
    
    async def search_jobs(self, query: str, filters: Dict = None) -> List[Job]:
        """Search for jobs using the existing browser session"""
        if not self.is_connected:
            print("❌ Not connected to browser")
            return []
        
        jobs = []
        
        try:
            # Build search URL
            search_url = self.build_search_url(query, filters)
            
            print(f"🔍 Searching for jobs: {query}")
            await self.page.goto(search_url)
            await asyncio.sleep(5)  # Give page time to load
            
            # Check if we hit Cloudflare
            page_title = await self.page.title()
            if "just a moment" in page_title.lower():
                print("🛡️ Cloudflare detected - waiting...")
                await self._wait_for_page_load()
            
            # Look for job tiles with multiple selectors
            job_selectors = [
                '[data-test="job-tile"]',
                '[data-cy="job-tile"]', 
                '.job-tile',
                'article[data-test]',
                '.up-card-section'
            ]
            
            job_tiles = []
            for selector in job_selectors:
                job_tiles = await self.page.query_selector_all(selector)
                if job_tiles:
                    print(f"✅ Found {len(job_tiles)} jobs with selector: {selector}")
                    break
            
            if not job_tiles:
                print("❌ No job tiles found")
                # Debug: save page screenshot
                await self.page.screenshot(path="debug_search_page.png")
                print("📷 Saved debug screenshot: debug_search_page.png")
                return []
            
            # Parse each job tile
            for i, tile in enumerate(job_tiles):
                try:
                    job = await self.parse_job_tile(tile)
                    if job:
                        jobs.append(job)
                        print(f"✅ Parsed job {i+1}: {job.title}")
                except Exception as e:
                    print(f"⚠️ Error parsing job {i+1}: {e}")
            
            print(f"🎯 Successfully found {len(jobs)} jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    async def _wait_for_page_load(self):
        """Wait for page to fully load (handles Cloudflare)"""
        for i in range(30):  # Wait up to 30 seconds
            await asyncio.sleep(1)
            page_title = await self.page.title()
            
            if "just a moment" not in page_title.lower():
                print("✅ Page loaded successfully")
                await asyncio.sleep(2)  # Extra buffer
                return
                
            if i % 5 == 0 and i > 0:
                print(f"⏳ Still loading... ({i}s)")
        
        print("⚠️ Page took longer than expected to load")
    
    def build_search_url(self, query: str, filters: Dict = None) -> str:
        """Build Upwork search URL with filters"""
        base_url = "https://www.upwork.com/nx/search/jobs"
        
        params = {
            'q': query,
            'sort': 'recency'
        }
        
        if filters:
            if 'budget_min' in filters:
                params['budget'] = f"[{filters['budget_min']} TO *]"
            if 'hourly_rate_min' in filters:
                params['hourly_rate'] = f"[{filters['hourly_rate_min']} TO *]"
            if 'job_type' in filters:
                params['job_type'] = filters['job_type']
        
        return f"{base_url}?{urlencode(params)}"
    
    async def parse_job_tile(self, tile) -> Optional[Job]:
        """Parse individual job tile"""
        try:
            # Title and URL
            title_selectors = [
                '[data-test="job-tile-title"] a',
                '.job-tile-title a',
                'h2 a',
                'h3 a'
            ]
            
            title = "No title"
            job_url = ""
            
            for selector in title_selectors:
                title_elem = await tile.query_selector(selector)
                if title_elem:
                    title = await title_elem.inner_text()
                    job_url = await title_elem.get_attribute('href')
                    break
            
            if job_url and not job_url.startswith('http'):
                job_url = f"https://www.upwork.com{job_url}"
            
            job_id = job_url.split('/')[-1].split('?')[0] if job_url else f"job_{datetime.now().timestamp()}"
            
            # Description
            desc_selectors = [
                '[data-test="job-description"]',
                '.job-description',
                '.description'
            ]
            
            description = ""
            for selector in desc_selectors:
                desc_elem = await tile.query_selector(selector)
                if desc_elem:
                    description = await desc_elem.inner_text()
                    break
            
            # Enhanced Budget Detection
            budget = "Not specified"
            
            # Get all text from the tile for budget analysis
            try:
                full_tile_text = await tile.inner_text()
                budget = self._extract_budget_from_text(full_tile_text)
            except:
                pass
            
            # If still not found, try specific selectors
            if budget == "Not specified":
                budget_selectors = [
                    '[data-test="job-type-and-budget"]',
                    '[data-test="budget"]',
                    '.budget',
                    '.job-budget',
                    '[data-cy="budget"]',
                    'small',
                    '.text-muted',
                    '.secondary-text'
                ]
                
                for selector in budget_selectors:
                    try:
                        budget_elem = await tile.query_selector(selector)
                        if budget_elem:
                            budget_text = await budget_elem.inner_text()
                            extracted_budget = self._extract_budget_from_text(budget_text)
                            if extracted_budget != "Not specified":
                                budget = extracted_budget
                                break
                    except:
                        continue
            
            # Skills
            skill_selectors = [
                '[data-test="token-skill"]',
                '.skill-tag',
                '.token'
            ]
            
            skills = []
            for selector in skill_selectors:
                skill_elems = await tile.query_selector_all(selector)
                for skill_elem in skill_elems:
                    skill_text = await skill_elem.inner_text()
                    skills.append(skill_text.strip())
                if skills:  # If we found skills with this selector, stop trying others
                    break
            
            return Job(
                id=job_id,
                title=title.strip(),
                description=description.strip(),
                url=job_url,
                client="Client",  # Will be extracted if element found
                budget=budget.strip(),
                budget_type="unknown",
                posted_time="Recent",
                skills=skills,
                proposals=None,
                client_rating=None,
                client_spent=None,
                raw_data={'source': 'existing_browser'}
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing job tile: {e}")
            return None
    
    def _extract_budget_from_text(self, text: str) -> str:
        """Extract budget information from text using comprehensive patterns"""
        if not text:
            return "Not specified"
        
        import re
        
        # Comprehensive budget patterns
        budget_patterns = [
            # Hourly rates
            (r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*-\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/\s*hr', 'hourly_range'),
            (r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/\s*hr', 'hourly'),
            (r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*per\s*hour', 'hourly'),
            (r'(\d+(?:,\d+)?(?:\.\d+)?)\s*-\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*/\s*hour', 'hourly_range_no_dollar'),
            
            # Fixed prices
            (r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*-\s*\$(\d+(?:,\d+)?(?:\.\d+)?)', 'fixed_range'),
            (r'\$(\d+(?:,\d+)?(?:\.\d+)?)', 'fixed'),
            (r'(\d+(?:,\d+)?(?:\.\d+)?)\s*-\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*USD', 'fixed_range_usd'),
            
            # Special cases
            (r'Fixed\s*price\s*\$(\d+(?:,\d+)?(?:\.\d+)?)', 'fixed_price'),
            (r'Hourly\s*\$(\d+(?:,\d+)?(?:\.\d+)?)', 'hourly_rate'),
            (r'Budget:\s*\$(\d+(?:,\d+)?(?:\.\d+)?)', 'budget'),
            
            # Text-based
            (r'Fixed\s*price', 'fixed_text'),
            (r'Hourly', 'hourly_text'),
        ]
        
        for pattern, pattern_type in budget_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if pattern_type == 'hourly_range':
                    return f"${match.group(1)}-${match.group(2)}/hr"
                elif pattern_type == 'hourly':
                    return f"${match.group(1)}/hr"
                elif pattern_type == 'hourly_range_no_dollar':
                    return f"${match.group(1)}-${match.group(2)}/hr"
                elif pattern_type == 'fixed_range':
                    return f"${match.group(1)}-${match.group(2)}"
                elif pattern_type == 'fixed':
                    return f"${match.group(1)}"
                elif pattern_type == 'fixed_range_usd':
                    return f"${match.group(1)}-${match.group(2)}"
                elif pattern_type in ['fixed_price', 'hourly_rate', 'budget']:
                    return f"${match.group(1)}"
                elif pattern_type in ['fixed_text', 'hourly_text']:
                    return match.group(0)
        
        return "Not specified"
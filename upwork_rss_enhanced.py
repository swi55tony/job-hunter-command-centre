# enhanced_upwork_rss.py - Production-ready RSS connector
"""
Enhanced Upwork RSS Connector - More reliable than API for job discovery
"""

import aiohttp
import asyncio
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import re
import urllib.parse

@dataclass
class UpworkJob:
    """Structured job data from Upwork RSS"""
    id: str
    title: str
    description: str
    url: str
    budget: str
    budget_type: str
    skills: List[str]
    posted_time: str
    client_rating: Optional[float] = None
    client_spent: Optional[str] = None
    campaign_score: float = 0.0
    military_relevance: float = 0.0

class EnhancedUpworkRSS:
    """Production-ready Upwork RSS connector"""
    
    def __init__(self):
        self.rss_base_url = "https://www.upwork.com/ab/feed/jobs/rss"
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        
        # Military/executive keywords for scoring
        self.military_keywords = [
            'military', 'veteran', 'leadership', 'operations', 'strategic',
            'tactical', 'command', 'management', 'scale', 'growth'
        ]
        
        self.executive_keywords = [
            'coo', 'ceo', 'director', 'vp', 'executive', 'fractional',
            'interim', 'senior', 'head of', 'chief'
        ]
    
    async def search_jobs(self, campaigns: Dict[str, Dict]) -> List[UpworkJob]:
        """
        Search multiple campaigns and return consolidated results
        
        campaigns = {
            'executive_suite': {'query': 'fractional COO', 'budget_min': 80},
            'strategic_consulting': {'query': 'business strategy consultant', 'budget_min': 60}
        }
        """
        all_jobs = []
        
        for campaign_name, config in campaigns.items():
            try:
                campaign_jobs = await self._search_campaign(campaign_name, config)
                all_jobs.extend(campaign_jobs)
                
                # Rate limiting - be respectful
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Campaign {campaign_name} failed: {e}")
                continue
        
        return self._deduplicate_jobs(all_jobs)
    
    async def _search_campaign(self, campaign_name: str, config: Dict) -> List[UpworkJob]:
        """Search single campaign via RSS"""
        
        # Build RSS parameters
        params = {
            'q': config['query'],
            'sort': 'recency',
            'paging': '0%3B50'  # Get more results
        }
        
        # Add budget filter if specified
        if 'budget_min' in config:
            params['budget'] = f"[{config['budget_min']}+TO+*]"
        
        # Add job type filter
        if 'job_type' in config:
            params['job_type'] = config['job_type']
        
        # Construct URL
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{self.rss_base_url}?{param_string}"
        
        print(f"Searching {campaign_name}: {config['query']}")
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url, headers=self._get_headers()) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        jobs = self._parse_rss_feed(xml_content, campaign_name)
                        print(f"Found {len(jobs)} jobs for {campaign_name}")
                        return jobs
                    else:
                        raise Exception(f"RSS request failed: {response.status}")
        
        except Exception as e:
            print(f"RSS error for {campaign_name}: {e}")
            return []
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'Accept-Language': 'en-GB,en;q=0.9',
        }
    
    def _parse_rss_feed(self, xml_content: str, campaign_name: str) -> List[UpworkJob]:
        """Parse jobs from RSS XML with enhanced data extraction"""
        jobs = []
        
        try:
            # Clean XML content
            xml_content = self._clean_xml(xml_content)
            root = ET.fromstring(xml_content)
            
            for item in root.findall('.//item'):
                try:
                    # Extract basic data
                    title = self._get_text(item, 'title', 'No title')
                    description = self._get_text(item, 'description', 'No description')
                    link = self._get_text(item, 'link', '')
                    pub_date = self._get_text(item, 'pubDate', 'Unknown')
                    
                    # Skip if no proper link
                    if not link or 'upwork.com' not in link:
                        continue
                    
                    # Extract job ID from URL
                    job_id = self._extract_job_id(link)
                    
                    # Extract enhanced data from description
                    budget_info = self._extract_budget_info(description)
                    skills = self._extract_skills(description)
                    client_info = self._extract_client_info(description)
                    
                    # Calculate relevance scores
                    military_score = self._calculate_military_relevance(title, description)
                    campaign_score = self._calculate_campaign_score(title, description, campaign_name)
                    
                    job = UpworkJob(
                        id=job_id,
                        title=title.strip(),
                        description=self._clean_description(description),
                        url=link,
                        budget=budget_info['budget_text'],
                        budget_type=budget_info['budget_type'],
                        skills=skills,
                        posted_time=pub_date,
                        client_rating=client_info.get('rating'),
                        client_spent=client_info.get('spent'),
                        campaign_score=campaign_score,
                        military_relevance=military_score
                    )
                    
                    jobs.append(job)
                    
                except Exception as e:
                    print(f"Error parsing job item: {e}")
                    continue
        
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
        
        return jobs
    
    def _clean_xml(self, xml_content: str) -> str:
        """Clean XML content for parsing"""
        # Remove CDATA sections that might cause issues
        xml_content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', xml_content, flags=re.DOTALL)
        
        # Fix common XML issues
        xml_content = xml_content.replace('&nbsp;', ' ')
        xml_content = xml_content.replace('&amp;', '&')
        
        return xml_content
    
    def _get_text(self, element, tag: str, default: str = '') -> str:
        """Safely get text from XML element"""
        child = element.find(tag)
        return child.text if child is not None and child.text else default
    
    def _extract_job_id(self, url: str) -> str:
        """Extract job ID from Upwork URL"""
        # Look for job ID pattern in URL
        match = re.search(r'/jobs/~([a-f0-9]+)', url)
        if match:
            return match.group(1)
        
        # Fallback to timestamp-based ID
        return f"rss_{int(datetime.now().timestamp())}"
    
    def _extract_budget_info(self, description: str) -> Dict:
        """Extract comprehensive budget information"""
        budget_patterns = [
            # Hourly ranges
            (r'Budget:\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*-\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/hr', 'hourly_range'),
            # Single hourly rate
            (r'Budget:\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/hr', 'hourly_single'),
            # Fixed budget
            (r'Budget:\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:fixed|total)', 'fixed'),
            # Generic dollar amounts
            (r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/\s*hr', 'hourly_single'),
            (r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*per\s*hour', 'hourly_single')
        ]
        
        for pattern, budget_type in budget_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                groups = match.groups()
                if budget_type == 'hourly_range' and len(groups) >= 2:
                    return {
                        'budget_text': f"${groups[0]}-${groups[1]}/hr",
                        'budget_type': 'hourly',
                        'min_rate': float(groups[0].replace(',', '')),
                        'max_rate': float(groups[1].replace(',', ''))
                    }
                elif len(groups) >= 1:
                    rate = float(groups[0].replace(',', ''))
                    if 'fixed' in budget_type:
                        return {
                            'budget_text': f"${groups[0]} fixed",
                            'budget_type': 'fixed',
                            'amount': rate
                        }
                    else:
                        return {
                            'budget_text': f"${groups[0]}/hr",
                            'budget_type': 'hourly',
                            'min_rate': rate
                        }
        
        return {
            'budget_text': 'Not specified',
            'budget_type': 'unknown'
        }
    
    def _extract_skills(self, description: str) -> List[str]:
        """Extract skills from job description"""
        # Look for skills section
        skills_match = re.search(r'Skills:\s*(.+?)(?:\n|$)', description, re.IGNORECASE)
        if skills_match:
            skills_text = skills_match.group(1)
            # Split on common delimiters
            skills = re.split(r'[,;|]', skills_text)
            return [skill.strip() for skill in skills if skill.strip()]
        
        return []
    
    def _extract_client_info(self, description: str) -> Dict:
        """Extract client information from description"""
        info = {}
        
        # Client rating
        rating_match = re.search(r'rating:\s*(\d+(?:\.\d+)?)', description, re.IGNORECASE)
        if rating_match:
            info['rating'] = float(rating_match.group(1))
        
        # Client spend
        spend_match = re.search(r'\$(\d+(?:,\d+)?(?:\.\d+)?[kK]?)\s*spent', description, re.IGNORECASE)
        if spend_match:
            info['spent'] = spend_match.group(1)
        
        return info
    
    def _calculate_military_relevance(self, title: str, description: str) -> float:
        """Calculate military relevance score (0-1)"""
        text = f"{title} {description}".lower()
        
        score = 0.0
        for keyword in self.military_keywords:
            if keyword in text:
                score += 0.1
        
        # Bonus for multiple matches
        if score > 0.3:
            score *= 1.2
        
        return min(score, 1.0)
    
    def _calculate_campaign_score(self, title: str, description: str, campaign: str) -> float:
        """Calculate campaign relevance score (0-10)"""
        text = f"{title} {description}".lower()
        
        base_score = 5.0  # Start with medium score
        
        # Executive roles get higher base score
        for keyword in self.executive_keywords:
            if keyword in text:
                base_score = 7.0
                break
        
        # Add points for military keywords
        military_boost = self._calculate_military_relevance(title, description) * 2
        
        # Campaign-specific boosts
        if 'executive' in campaign and any(word in text for word in ['coo', 'ceo', 'director']):
            base_score += 1.5
        
        if 'strategic' in campaign and 'strategy' in text:
            base_score += 1.0
        
        return min(base_score + military_boost, 10.0)
    
    def _clean_description(self, description: str) -> str:
        """Clean and truncate description"""
        # Remove HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        
        # Remove excessive whitespace
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Truncate if too long
        if len(description) > 800:
            description = description[:800] + "..."
        
        return description
    
    def _deduplicate_jobs(self, jobs: List[UpworkJob]) -> List[UpworkJob]:
        """Remove duplicate jobs based on ID"""
        seen_ids = set()
        unique_jobs = []
        
        for job in jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                unique_jobs.append(job)
        
        return unique_jobs

# Integration function for your Streamlit app
async def run_upwork_campaign(mode: str) -> List[Dict]:
    """
    Run Upwork RSS campaign - integrate this into your Streamlit app
    """
    connector = EnhancedUpworkRSS()
    
    # Define campaign configurations
    campaigns = {
        'full': {
            'executive_suite': {'query': 'fractional COO OR interim COO', 'budget_min': 80},
            'strategic_consulting': {'query': 'business strategy consultant', 'budget_min': 60},
            'revenue_operations': {'query': 'revenue operations director', 'budget_min': 70},
            'coaching_mentoring': {'query': 'executive coaching OR business mentor', 'budget_min': 50}
        },
        'executive': {
            'executive_suite': {'query': 'fractional COO OR interim CEO OR fractional CEO', 'budget_min': 100}
        },
        'strategic': {
            'strategic_consulting': {'query': 'business strategy OR strategic consulting', 'budget_min': 60}
        },
        'quick': {
            'high_value': {'query': 'fractional OR interim', 'budget_min': 80}
        }
    }
    
    # Get campaign config
    campaign_config = campaigns.get(mode, campaigns['quick'])
    
    # Run search
    jobs = await connector.search_jobs(campaign_config)
    
    # Convert to your app's format
    formatted_jobs = []
    for job in jobs:
        formatted_job = {
            'id': job.id,
            'title': job.title,
            'budget': job.budget,
            'campaign_score': job.campaign_score,
            'military_fit': job.military_relevance,
            'campaign': list(campaign_config.keys())[0],  # Primary campaign
            'priority': 'HIGH' if job.campaign_score >= 7.0 else 'MEDIUM',
            'url': job.url,
            'description': job.description,
            'timestamp': datetime.now().isoformat(),
            'skills': job.skills,
            'client_rating': job.client_rating,
            'client_spent': job.client_spent
        }
        formatted_jobs.append(formatted_job)
    
    return formatted_jobs

# Test function
async def test_enhanced_rss():
    """Test the enhanced RSS connector"""
    campaigns = {
        'executive_test': {'query': 'fractional COO', 'budget_min': 60}
    }
    
    connector = EnhancedUpworkRSS()
    jobs = await connector.search_jobs(campaigns)
    
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:3]:
        print(f"- {job.title}")
        print(f"  Budget: {job.budget}")
        print(f"  Score: {job.campaign_score:.1f}")
        print(f"  Military: {job.military_relevance:.1%}")
        print(f"  URL: {job.url}")
        print()

if __name__ == "__main__":
    asyncio.run(test_enhanced_rss())
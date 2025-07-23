# upwork_api_connector.py - Official Upwork API Integration
"""
Upwork API Connector for Job Hunting
Note: Upwork API has limited freelancer job search capabilities
"""

import aiohttp
import asyncio
import os
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class UpworkJob:
    """Structured job data from Upwork API"""
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

class UpworkAPIConnector:
    def __init__(self):
        # Get API credentials from environment or Streamlit secrets
        self.client_id = self._get_credential('upwork_client_id')
        self.client_secret = self._get_credential('upwork_client_secret')
        self.access_token = self._get_credential('upwork_access_token')
        
        self.base_url = "https://www.upwork.com/api"
        self.api_version = "v1"
        
    def _get_credential(self, key: str) -> Optional[str]:
        """Get credential from environment or Streamlit secrets"""
        # Try environment variables first
        value = os.getenv(key.upper())
        if value:
            return value
            
        # Try Streamlit secrets
        try:
            import streamlit as st
            return st.secrets.get(key)
        except:
            return None
    
    async def search_jobs(self, query: str, filters: Dict = None) -> List[UpworkJob]:
        """
        Search for jobs using Upwork API
        
        Note: Upwork API job search is very limited for freelancers
        Most comprehensive job data requires web scraping
        """
        
        if not self.access_token:
            raise Exception("Upwork API access token required. See setup instructions.")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "JobHunterCommandCentre/1.0"
        }
        
        # Upwork API job search endpoint (limited functionality)
        search_params = {
            "q": query,
            "sort": "recency",
            "paging": "0;20"  # Get up to 20 results
        }
        
        if filters:
            if 'budget_min' in filters:
                search_params['budget'] = f"[{filters['budget_min']} TO *]"
            if 'job_type' in filters:
                search_params['job_type'] = filters['job_type']
        
        try:
            async with aiohttp.ClientSession() as session:
                # Note: This endpoint may not exist or may be restricted
                url = f"{self.base_url}/{self.api_version}/profiles/search/jobs"
                
                async with session.get(url, headers=headers, params=search_params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_job_results(data)
                    elif response.status == 401:
                        raise Exception("Unauthorized - check your Upwork API credentials")
                    elif response.status == 403:
                        raise Exception("Forbidden - your app may not have job search permissions")
                    else:
                        raise Exception(f"API request failed: {response.status}")
                        
        except Exception as e:
            print(f"Upwork API error: {e}")
            return []
    
    def _parse_job_results(self, data: Dict) -> List[UpworkJob]:
        """Parse job results from Upwork API response"""
        jobs = []
        
        # Note: Actual API response structure may be different
        job_results = data.get('jobs', {}).get('job', [])
        
        for job_data in job_results:
            try:
                job = UpworkJob(
                    id=job_data.get('id', ''),
                    title=job_data.get('title', 'No title'),
                    description=job_data.get('snippet', 'No description available'),
                    url=f"https://www.upwork.com/jobs/~{job_data.get('id', '')}",
                    budget=self._format_budget(job_data),
                    budget_type=job_data.get('job_type', 'unknown'),
                    skills=job_data.get('skills', []),
                    posted_time=job_data.get('date_created', 'Unknown'),
                    client_rating=job_data.get('client', {}).get('feedback', None),
                    client_spent=job_data.get('client', {}).get('total_spent', None)
                )
                jobs.append(job)
            except Exception as e:
                print(f"Error parsing job: {e}")
                continue
        
        return jobs
    
    def _format_budget(self, job_data: Dict) -> str:
        """Format budget information from API data"""
        budget_type = job_data.get('job_type', '')
        
        if budget_type == 'hourly':
            budget = job_data.get('budget', {})
            min_rate = budget.get('min', 0)
            max_rate = budget.get('max', 0)
            
            if min_rate and max_rate:
                return f"${min_rate}-${max_rate}/hr"
            elif min_rate:
                return f"${min_rate}+/hr"
            else:
                return "Hourly rate not specified"
        
        elif budget_type == 'fixed':
            budget = job_data.get('budget', {})
            amount = budget.get('amount', 0)
            if amount:
                return f"${amount} fixed"
            else:
                return "Fixed price not specified"
        
        return "Budget not specified"

# Alternative: RSS Feed Approach (More Reliable)
class UpworkRSSConnector:
    """
    Alternative approach using Upwork's RSS feeds
    More reliable than API for job searching
    """
    
    def __init__(self):
        self.rss_base_url = "https://www.upwork.com/ab/feed/jobs/rss"
    
    async def search_jobs_rss(self, query: str, filters: Dict = None) -> List[UpworkJob]:
        """Search jobs using Upwork RSS feeds"""
        import xml.etree.ElementTree as ET
        
        # Build RSS feed URL
        params = {
            'q': query,
            'sort': 'recency',
            'paging': '0%3B20'  # URL encoded paging
        }
        
        if filters:
            if 'budget_min' in filters:
                params['budget'] = f"[{filters['budget_min']}+TO+*]"
        
        # Construct URL
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{self.rss_base_url}?{param_string}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        return self._parse_rss_feed(xml_content)
                    else:
                        raise Exception(f"RSS feed request failed: {response.status}")
        
        except Exception as e:
            print(f"RSS feed error: {e}")
            return []
    
    def _parse_rss_feed(self, xml_content: str) -> List[UpworkJob]:
        """Parse jobs from RSS feed XML"""
        jobs = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for item in root.findall('.//item'):
                title = item.find('title').text if item.find('title') is not None else 'No title'
                description = item.find('description').text if item.find('description') is not None else 'No description'
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else 'Unknown'
                
                # Extract job ID from URL
                job_id = link.split('/')[-1] if link else f"rss_{datetime.now().timestamp()}"
                
                # Extract budget from description (RSS feeds include this)
                budget = self._extract_budget_from_description(description)
                
                job = UpworkJob(
                    id=job_id,
                    title=title,
                    description=description[:500] + "..." if len(description) > 500 else description,
                    url=link,
                    budget=budget,
                    budget_type='unknown',
                    skills=[],  # RSS doesn't include skills
                    posted_time=pub_date,
                    client_rating=None,
                    client_spent=None
                )
                
                jobs.append(job)
        
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
        
        return jobs
    
    def _extract_budget_from_description(self, description: str) -> str:
        """Extract budget information from job description"""
        import re
        
        # Look for budget patterns in description
        budget_patterns = [
            r'Budget:\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*-\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/hr',
            r'Budget:\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/hr',
            r'Budget:\s*\$(\d+(?:,\d+)?(?:\.\d+)?)',
            r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/\s*hr',
            r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*per\s*hour'
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    return f"${match.group(1)}-${match.group(2)}/hr"
                else:
                    return f"${match.group(1)}/hr"
        
        return "Not specified"

# Usage example
async def test_upwork_api():
    """Test function for Upwork API integration"""
    
    # Try API approach first
    api_connector = UpworkAPIConnector()
    
    try:
        jobs = await api_connector.search_jobs("fractional COO", {"budget_min": 60})
        print(f"Found {len(jobs)} jobs via API")
        
        for job in jobs[:3]:
            print(f"- {job.title} | {job.budget} | {job.url}")
    
    except Exception as e:
        print(f"API approach failed: {e}")
        
        # Fall back to RSS approach
        print("Trying RSS feed approach...")
        rss_connector = UpworkRSSConnector()
        
        try:
            jobs = await rss_connector.search_jobs_rss("fractional COO")
            print(f"Found {len(jobs)} jobs via RSS")
            
            for job in jobs[:3]:
                print(f"- {job.title} | {job.budget}")
        
        except Exception as rss_error:
            print(f"RSS approach also failed: {rss_error}")

if __name__ == "__main__":
    asyncio.run(test_upwork_api())

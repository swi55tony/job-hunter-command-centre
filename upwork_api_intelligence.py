# upwork_api_intelligence.py - Use API for client intelligence
"""
Use Upwork API to gather client intelligence for jobs found via RSS
This is where your API credentials actually add value
"""

import aiohttp
import asyncio
import os
from typing import Dict, Optional, List
from dataclasses import dataclass
import re

@dataclass
class ClientIntelligence:
    """Client intelligence from Upwork API"""
    client_id: str
    feedback_score: Optional[float] = None
    total_spent: Optional[float] = None
    total_jobs: Optional[int] = None
    last_activity: Optional[str] = None
    payment_verified: Optional[bool] = None
    avg_hourly_rate: Optional[float] = None
    repeat_hire_rate: Optional[float] = None
    country: Optional[str] = None

class UpworkAPIIntelligence:
    """Use Upwork API for client intelligence gathering"""
    
    def __init__(self):
        # Get your actual API credentials
        self.client_id = self._get_credential('upwork_client_id')
        self.client_secret = self._get_credential('upwork_client_secret')
        self.access_token = self._get_credential('upwork_access_token')
        
        if not all([self.client_id, self.client_secret, self.access_token]):
            raise Exception("Missing Upwork API credentials")
        
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
    
    async def enrich_jobs_with_intelligence(self, jobs: List[Dict]) -> List[Dict]:
        """
        Take jobs from RSS and enrich with API intelligence
        This is the killer feature - knowing which clients are worth pursuing
        """
        enriched_jobs = []
        
        for job in jobs:
            try:
                # Extract client info from job URL
                client_intel = await self.get_client_intelligence(job['url'])
                
                # Enhance job with intelligence
                enhanced_job = job.copy()
                if client_intel:
                    enhanced_job.update({
                        'client_feedback_score': client_intel.feedback_score,
                        'client_total_spent': client_intel.total_spent,
                        'client_total_jobs': client_intel.total_jobs,
                        'client_payment_verified': client_intel.payment_verified,
                        'client_country': client_intel.country,
                        'client_repeat_rate': client_intel.repeat_hire_rate
                    })
                    
                    # Recalculate priority with intelligence
                    enhanced_job['priority'] = self._calculate_priority_with_intel(job, client_intel)
                    enhanced_job['campaign_score'] = self._boost_score_with_intel(job['campaign_score'], client_intel)
                
                enriched_jobs.append(enhanced_job)
                
                # Rate limiting - be respectful
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Failed to enrich job {job.get('id', 'unknown')}: {e}")
                enriched_jobs.append(job)  # Keep original if enrichment fails
        
        return enriched_jobs
    
    async def get_client_intelligence(self, job_url: str) -> Optional[ClientIntelligence]:
        """
        Extract client intelligence from job URL
        This uses the API endpoints that actually work
        """
        try:
            # Extract client ID from job URL (you'll need to reverse engineer this)
            client_id = self._extract_client_id_from_url(job_url)
            if not client_id:
                return None
            
            # Use API to get client profile data
            client_data = await self._call_api(f"profiles/{client_id}")
            
            if not client_data:
                return None
            
            return ClientIntelligence(
                client_id=client_id,
                feedback_score=client_data.get('feedback_score'),
                total_spent=self._parse_amount(client_data.get('total_spent')),
                total_jobs=client_data.get('total_jobs'),
                payment_verified=client_data.get('payment_verified'),
                country=client_data.get('country'),
                repeat_hire_rate=client_data.get('repeat_hire_rate')
            )
            
        except Exception as e:
            print(f"Client intelligence error: {e}")
            return None
    
    def _extract_client_id_from_url(self, job_url: str) -> Optional[str]:
        """
        Extract client ID from job URL
        This might require some reverse engineering of Upwork's URL structure
        """
        # This is where you'd implement URL parsing logic
        # Upwork job URLs contain client identifiers that you can extract
        
        # Placeholder - you'll need to figure out the actual pattern
        match = re.search(r'client[/_]([a-f0-9]+)', job_url)
        if match:
            return match.group(1)
        
        return None
    
    async def _call_api(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated API call"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "JobHunterCommandCentre/1.0",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/{self.api_version}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        print("API Unauthorized - check your access token")
                        return None
                    else:
                        print(f"API call failed: {response.status}")
                        return None
        
        except Exception as e:
            print(f"API request error: {e}")
            return None
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse dollar amounts from API responses"""
        if not amount_str:
            return None
        
        # Remove currency symbols and commas
        clean_amount = re.sub(r'[^\d.]', '', str(amount_str))
        
        try:
            return float(clean_amount)
        except:
            return None
    
    def _calculate_priority_with_intel(self, job: Dict, intel: ClientIntelligence) -> str:
        """Recalculate job priority with client intelligence"""
        base_score = job.get('campaign_score', 5.0)
        
        # Start with base priority
        if base_score >= 7.0:
            priority = "HIGH"
        elif base_score >= 5.0:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        
        # Upgrade based on client quality
        if intel.feedback_score and intel.feedback_score >= 4.8:
            if priority == "MEDIUM":
                priority = "HIGH"
        
        if intel.total_spent and intel.total_spent >= 10000:  # $10k+ spent
            if priority == "LOW":
                priority = "MEDIUM"
            elif priority == "MEDIUM":
                priority = "HIGH"
        
        # Downgrade for red flags
        if intel.feedback_score and intel.feedback_score < 4.0:
            if priority == "HIGH":
                priority = "MEDIUM"
            elif priority == "MEDIUM":
                priority = "LOW"
        
        return priority
    
    def _boost_score_with_intel(self, base_score: float, intel: ClientIntelligence) -> float:
        """Boost campaign score with client intelligence"""
        boosted_score = base_score
        
        # High-spending clients get score boost
        if intel.total_spent:
            if intel.total_spent >= 50000:  # $50k+
                boosted_score += 1.0
            elif intel.total_spent >= 20000:  # $20k+
                boosted_score += 0.5
        
        # High-rating clients get boost
        if intel.feedback_score and intel.feedback_score >= 4.8:
            boosted_score += 0.5
        
        # Payment verified clients get small boost
        if intel.payment_verified:
            boosted_score += 0.2
        
        # Cap at 10.0
        return min(boosted_score, 10.0)

# Integration function for your Streamlit app
async def run_intelligence_enhanced_campaign(mode: str) -> List[Dict]:
    """
    Run campaign with both RSS discovery and API intelligence
    This is your complete solution
    """
    # Step 1: Get jobs via RSS
    from enhanced_upwork_rss import run_upwork_campaign
    jobs = await run_upwork_campaign(mode)
    
    print(f"RSS Discovery: {len(jobs)} jobs found")
    
    # Step 2: Enrich with API intelligence
    try:
        intel_api = UpworkAPIIntelligence()
        enriched_jobs = await intel_api.enrich_jobs_with_intelligence(jobs)
        
        print(f"Intelligence Enhancement: {len(enriched_jobs)} jobs enriched")
        return enriched_jobs
    
    except Exception as e:
        print(f"Intelligence enhancement failed: {e}")
        return jobs  # Return original jobs if API fails

# Test function
async def test_intelligence_system():
    """Test the complete intelligence system"""
    try:
        jobs = await run_intelligence_enhanced_campaign('executive')
        
        print(f"\nIntelligence-Enhanced Results: {len(jobs)} jobs")
        
        for job in jobs[:3]:
            print(f"\n- {job['title']}")
            print(f"  Score: {job['campaign_score']:.1f} | Priority: {job['priority']}")
            print(f"  Budget: {job['budget']}")
            
            if 'client_feedback_score' in job:
                print(f"  Client Rating: {job['client_feedback_score']}")
                print(f"  Client Spent: ${job.get('client_total_spent', 'Unknown')}")
            else:
                print("  Client Intelligence: Not available")
    
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_intelligence_system())
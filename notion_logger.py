# notion_logger.py - Enhanced Notion Logger with Deduplication
"""
🎖️ ANTONY DRAPER - NOTION LOGGER (ENHANCED WITH DEDUPLICATION)
Prevents duplicate job entries and manages proposal pipeline status
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional
import requests
import json

class NotionLoggerDedup:
    def __init__(self, notion_token: str = None, database_id: str = None):
        # Get credentials from environment variables or Streamlit secrets
        if notion_token and database_id:
            self.notion_token = notion_token
            self.database_id = database_id
        else:
            # Try to get from environment variables first (for local use)
            self.notion_token = os.getenv('NOTION_TOKEN')
            self.database_id = os.getenv('NOTION_DATABASE_ID')
            
            # If running in Streamlit, try to get from secrets
            if not self.notion_token or not self.database_id:
                try:
                    import streamlit as st
                    self.notion_token = st.secrets.get('notion_token')
                    self.database_id = st.secrets.get('notion_database_id')
                except:
                    pass
        
        # Validate we have required credentials
        if not self.notion_token or not self.database_id:
            raise ValueError("Notion token and database ID are required. Set via environment variables or pass directly.")
        
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Cache for existing jobs to avoid repeated API calls
        self._existing_jobs_cache = {}
        self._cache_refreshed = False
    
    async def log_job_opportunity(self, job, icp_score, campaign_name: str):
        """
        Log job opportunity with deduplication check
        """
        try:
            # Check if job already exists
            existing_job = await self._find_existing_job(job.url)
            
            if existing_job:
                # Update existing job instead of creating duplicate
                await self._update_existing_job(existing_job, job, icp_score, campaign_name)
                print(f"   📊 Updated existing job in Notion: {job.title[:50]}...")
                return existing_job['id']
            else:
                # Create new job entry
                new_job_id = await self._create_new_job(job, icp_score, campaign_name)
                print(f"   📊 New job logged to Notion: {job.title[:50]}...")
                return new_job_id
                
        except Exception as e:
            print(f"   ❌ Notion logging error: {e}")
            return None
    
    async def _find_existing_job(self, job_url: str) -> Optional[Dict]:
        """
        Find existing job by URL to prevent duplicates
        """
        try:
            # Refresh cache if needed
            if not self._cache_refreshed:
                await self._refresh_existing_jobs_cache()
            
            # Check cache first
            if job_url in self._existing_jobs_cache:
                return self._existing_jobs_cache[job_url]
            
            # If not in cache, do direct search
            query_data = {
                "filter": {
                    "property": "Job URL",
                    "url": {
                        "equals": job_url
                    }
                },
                "page_size": 1
            }
            
            response = requests.post(
                f"https://api.notion.com/v1/databases/{self.database_id}/query",
                headers=self.headers,
                json=query_data
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    existing_job = results[0]
                    # Add to cache
                    self._existing_jobs_cache[job_url] = existing_job
                    return existing_job
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ Error checking for existing job: {e}")
            return None
    
    async def _refresh_existing_jobs_cache(self):
        """
        Refresh cache of existing jobs for faster duplicate checking
        """
        try:
            # Get all jobs from last 30 days to build cache
            query_data = {
                "filter": {
                    "property": "Date Added",
                    "date": {
                        "after": (datetime.now().replace(day=1)).isoformat()
                    }
                },
                "page_size": 100
            }
            
            response = requests.post(
                f"https://api.notion.com/v1/databases/{self.database_id}/query",
                headers=self.headers,
                json=query_data
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                
                for job in results:
                    try:
                        job_url_prop = job.get('properties', {}).get('Job URL', {})
                        if job_url_prop.get('type') == 'url' and job_url_prop.get('url'):
                            job_url = job_url_prop['url']
                            self._existing_jobs_cache[job_url] = job
                    except:
                        continue
                
                self._cache_refreshed = True
                print(f"   📊 Cached {len(self._existing_jobs_cache)} existing jobs for deduplication")
            
        except Exception as e:
            print(f"   ⚠️ Error refreshing cache: {e}")
    
    async def _update_existing_job(self, existing_job: Dict, job, icp_score, campaign_name: str):
        """
        Update existing job with latest information
        """
        try:
            # Get current properties
            current_props = existing_job.get('properties', {})
            
            # Prepare update data
            update_data = {
                "properties": {
                    "Last Seen": {
                        "date": {
                            "start": datetime.now().isoformat()
                        }
                    },
                    "Campaign": {
                        "select": {
                            "name": campaign_name
                        }
                    }
                }
            }
            
            # Update ICP score if it's better
            if hasattr(icp_score, 'confidence'):
                current_confidence = self._extract_number_from_property(
                    current_props.get('Confidence', {})
                )
                if not current_confidence or icp_score.confidence > current_confidence:
                    update_data["properties"]["Confidence"] = {
                        "number": round(icp_score.confidence * 100, 1)
                    }
                    update_data["properties"]["Fit Level"] = {
                        "select": {
                            "name": icp_score.fit_level
                        }
                    }
            
            # Don't change status if already set to something other than "Prospecting"
            current_status = self._extract_select_from_property(
                current_props.get('Status', {})
            )
            if not current_status or current_status == "Prospecting":
                update_data["properties"]["Status"] = {
                    "select": {
                        "name": "Updated"
                    }
                }
            
            response = requests.patch(
                f"https://api.notion.com/v1/pages/{existing_job['id']}",
                headers=self.headers,
                json=update_data
            )
            
            if response.status_code != 200:
                print(f"   ⚠️ Failed to update existing job: {response.status_code}")
            
        except Exception as e:
            print(f"   ❌ Error updating existing job: {e}")
    
    async def _create_new_job(self, job, icp_score, campaign_name: str) -> Optional[str]:
        """
        Create new job entry in Notion
        """
        try:
            # Build properties based on what we know about typical Notion job databases
            properties = {
                "Job Title": {
                    "title": [
                        {
                            "text": {
                                "content": job.title[:100]  # Notion title limit
                            }
                        }
                    ]
                },
                "Job URL": {
                    "url": job.url
                },
                "Budget": {
                    "rich_text": [
                        {
                            "text": {
                                "content": job.budget or "Not specified"
                            }
                        }
                    ]
                },
                "Campaign": {
                    "select": {
                        "name": campaign_name
                    }
                },
                "Date Added": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                },
                "Status": {
                    "select": {
                        "name": "Prospecting"
                    }
                }
            }
            
            # Add ICP scoring data if available
            if hasattr(icp_score, 'confidence'):
                properties["Confidence"] = {
                    "number": round(icp_score.confidence * 100, 1)
                }
                properties["Fit Level"] = {
                    "select": {
                        "name": icp_score.fit_level
                    }
                }
            
            if hasattr(icp_score, 'industry_match'):
                properties["Industry Match"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": str(icp_score.industry_match)[:2000]
                            }
                        }
                    ]
                }
            
            # Create the page
            page_data = {
                "parent": {
                    "database_id": self.database_id
                },
                "properties": properties
            }
            
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers,
                json=page_data
            )
            
            if response.status_code == 200:
                new_page = response.json()
                # Add to cache
                self._existing_jobs_cache[job.url] = new_page
                return new_page['id']
            else:
                print(f"   ❌ Failed to create job: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error creating new job: {e}")
            return None
    
    async def log_proposal(self, job, proposal_data: Dict, icp_score):
        """
        Log proposal submission and update job status
        """
        try:
            # Find the job entry
            existing_job = await self._find_existing_job(job.url)
            
            if existing_job:
                # Update status to "Proposal Submitted"
                update_data = {
                    "properties": {
                        "Status": {
                            "select": {
                                "name": "Proposal Submitted"
                            }
                        },
                        "Proposal Date": {
                            "date": {
                                "start": datetime.now().isoformat()
                            }
                        },
                        "Proposal Word Count": {
                            "number": proposal_data.get('word_count', 0)
                        }
                    }
                }
                
                response = requests.patch(
                    f"https://api.notion.com/v1/pages/{existing_job['id']}",
                    headers=self.headers,
                    json=update_data
                )
                
                if response.status_code == 200:
                    print(f"   📊 Updated job status to 'Proposal Submitted'")
                else:
                    print(f"   ⚠️ Failed to update proposal status: {response.status_code}")
            else:
                print(f"   ⚠️ Could not find job to update proposal status")
                
        except Exception as e:
            print(f"   ❌ Error logging proposal: {e}")
    
    async def mark_job_status(self, job_url: str, status: str):
        """
        Update job status manually (for when you submit proposals outside the system)
        """
        try:
            existing_job = await self._find_existing_job(job_url)
            
            if existing_job:
                update_data = {
                    "properties": {
                        "Status": {
                            "select": {
                                "name": status
                            }
                        },
                        "Status Updated": {
                            "date": {
                                "start": datetime.now().isoformat()
                            }
                        }
                    }
                }
                
                response = requests.patch(
                    f"https://api.notion.com/v1/pages/{existing_job['id']}",
                    headers=self.headers,
                    json=update_data
                )
                
                if response.status_code == 200:
                    print(f"   ✅ Job status updated to '{status}'")
                    return True
                else:
                    print(f"   ❌ Failed to update status: {response.status_code}")
                    return False
            else:
                print(f"   ❌ Job not found: {job_url}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error updating job status: {e}")
            return False
    
    async def get_job_stats(self) -> Dict:
        """
        Get comprehensive job statistics
        """
        try:
            query_data = {
                "page_size": 100
            }
            
            response = requests.post(
                f"https://api.notion.com/v1/databases/{self.database_id}/query",
                headers=self.headers,
                json=query_data
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                
                stats = {
                    'total_jobs': len(results),
                    'prospecting': 0,
                    'proposals_submitted': 0,
                    'interviews': 0,
                    'won': 0,
                    'lost': 0,
                    'high_priority': 0
                }
                
                for job in results:
                    try:
                        # Status counting
                        status = self._extract_select_from_property(
                            job.get('properties', {}).get('Status', {})
                        )
                        if status == "Prospecting":
                            stats['prospecting'] += 1
                        elif status == "Proposal Submitted":
                            stats['proposals_submitted'] += 1
                        elif status == "Interview":
                            stats['interviews'] += 1
                        elif status == "Won":
                            stats['won'] += 1
                        elif status == "Lost":
                            stats['lost'] += 1
                        
                        # Fit level counting
                        fit_level = self._extract_select_from_property(
                            job.get('properties', {}).get('Fit Level', {})
                        )
                        if fit_level == "High":
                            stats['high_priority'] += 1
                            
                    except:
                        continue
                
                # Calculate conversion rates
                if stats['total_jobs'] > 0:
                    stats['proposal_rate'] = round(stats['proposals_submitted'] / stats['total_jobs'] * 100, 1)
                    stats['interview_rate'] = round(stats['interviews'] / max(stats['proposals_submitted'], 1) * 100, 1)
                    stats['win_rate'] = round(stats['won'] / max(stats['proposals_submitted'], 1) * 100, 1)
                
                return stats
            else:
                return {'error': f"Failed to fetch stats: {response.status_code}"}
                
        except Exception as e:
            return {'error': f"Error getting stats: {e}"}
    
    def _extract_select_from_property(self, prop: Dict) -> Optional[str]:
        """Extract select value from Notion property"""
        try:
            if prop.get('type') == 'select' and prop.get('select'):
                return prop['select'].get('name')
            return None
        except:
            return None
    
    def _extract_number_from_property(self, prop: Dict) -> Optional[float]:
        """Extract number value from Notion property"""
        try:
            if prop.get('type') == 'number':
                return prop.get('number')
            return None
        except:
            return None

# Status update utility function
async def update_job_status(job_url: str, status: str):
    """
    Utility function to manually update job status
    Usage: await update_job_status("https://upwork.com/jobs/...", "Proposal Submitted")
    """
    logger = NotionLoggerDedup()
    return await logger.mark_job_status(job_url, status)

# Quick stats utility
async def get_pipeline_stats():
    """
    Utility function to get quick pipeline stats
    """
    logger = NotionLoggerDedup()
    return await logger.get_job_stats()

# Export for use as drop-in replacement
NotionLogger = NotionLoggerDedup

if __name__ == "__main__":
    # Test functionality
    print("🎖️ NOTION LOGGER (DEDUPLICATION) - TEST MODE")
    print("Import this as: from notion_logger import NotionLoggerDedup")
    print("Or use as drop-in replacement: from notion_logger import NotionLogger")

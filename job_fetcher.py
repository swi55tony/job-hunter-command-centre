# job_fetcher.py
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urlencode, urlparse, parse_qs
@dataclass
class Job:
    """Structured job data"""
    id: str
    title: str
    description: str
    url: str
    client: str
    budget: str
    budget_type: str  # 'hourly' or 'fixed'
    hourly_range: Optional[tuple] = None
    posted_time: Optional[str] = None
    category: Optional[str] = None
    skills: List[str] = None
    proposals: Optional[int] = None
    client_rating: Optional[float] = None
    client_spent: Optional[str] = None
    duration: Optional[str] = None
    experience_level: Optional[str] = None
    raw_data: Optional[Dict] = None
    def post_init(self):
        if self.skills is None:
            self.skills = []
class JobFetcher:
    def init(self, config: Dict):
        self.config = config
        self.session = None
        self.last_check = None
        self.seen_job_ids = set()
        self.logger = logging.getLogger(name)

        # Search configuration
        self.search_queries = config.get('search_queries', [])
        self.filters = config.get('filters', {})

        # Rate limiting
        self.request_delay = 2  # seconds between requests
        self.last_request_time = 0

    async def aenter(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self

    async def aexit(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
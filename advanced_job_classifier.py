# advanced_job_classifier.py - ICP-based job classification
import json
import asyncio
import aiohttp
from dataclasses import dataclass
from typing import Dict, List, Optional
from job_fetcher import Job

@dataclass
class ICPScore:
    fit_level: str  # High/Medium/Low
    confidence: float
    industry_match: str
    pain_points: List[str]
    budget_fit: str
    reasoning: str
    hourly_rate_match: bool
    project_duration_fit: str

class AdvancedJobClassifier:
    def __init__(self, config: Dict):
        self.config = config
        
        # Your ICP profiles based on ex-military + business operations background
        self.icp_profiles = {
            'scaling_startup': {
                'description': '20-50 person companies transitioning from founder-led chaos',
                'keywords': ['startup', 'scale', 'growth', 'systems', 'processes', 'operations', 'founder'],
                'pain_points': ['scaling', 'operations', 'systems', 'processes', 'team building'],
                'company_size': ['20-50', 'small team', 'growing team'],
                'budget_range': (75, 150),
                'ideal_duration': ['months', 'ongoing', 'long-term']
            },
            'operations_overhaul': {
                'description': 'Companies needing operational structure and efficiency',
                'keywords': ['operations', 'efficiency', 'process improvement', 'workflow', 'automation'],
                'pain_points': ['inefficient', 'manual processes', 'chaos', 'disorganized'],
                'company_size': ['medium', 'growing', 'established'],
                'budget_range': (60, 120),
                'ideal_duration': ['weeks', 'months']
            },
            'team_leadership': {
                'description': 'Leadership roles leveraging military experience',
                'keywords': ['leadership', 'team lead', 'manager', 'director', 'military', 'veteran'],
                'pain_points': ['team management', 'leadership', 'structure', 'discipline'],
                'company_size': ['any'],
                'budget_range': (80, 200),
                'ideal_duration': ['months', 'ongoing', 'permanent']
            },
            'sales_operations': {
                'description': 'Revenue operations roles leveraging HP/Capita sales experience',
                'keywords': ['sales operations', 'revenue operations', 'crm', 'sales process', 'revenue', 'sales director', 'cmo', 'cro', 'cso'],
                'pain_points': ['sales efficiency', 'process', 'data', 'pipeline', 'forecasting', 'revenue growth'],
                'company_size': ['medium', 'large', 'enterprise', 'scaling'],
                'budget_range': (75, 200),
                'ideal_duration': ['months', 'ongoing']
            },
            'revenue_leadership': {
                'description': 'Fractional CMO/CRO/CSO roles combining military discipline with sales expertise',
                'keywords': ['fractional cmo', 'fractional cro', 'fractional cso', 'revenue operations', 'sales transformation', 'marketing operations'],
                'pain_points': ['revenue growth', 'sales performance', 'marketing efficiency', 'lead generation', 'conversion optimization'],
                'company_size': ['startup', 'scaling', 'medium'],
                'budget_range': (100, 250),
                'ideal_duration': ['months', 'ongoing', 'fractional']
            },
            'strategic_consulting': {
                'description': 'High-level strategic work - GTM, business plans, pitch decks',
                'keywords': ['go to market', 'gtm strategy', 'business plan', 'pitch deck', 'strategic planning', 'market entry', 'business strategy'],
                'pain_points': ['market entry', 'strategic direction', 'investor readiness', 'growth planning', 'competitive positioning'],
                'company_size': ['startup', 'scaling', 'established'],
                'budget_range': (100, 300),
                'ideal_duration': ['weeks', 'months', 'project-based']
            },
            'crisis_management': {
                'description': 'Companies in chaos needing military-style order',
                'keywords': ['crisis', 'urgent', 'chaos', 'fix', 'stabilize', 'emergency'],
                'pain_points': ['crisis', 'urgent fix', 'stabilization', 'rapid improvement'],
                'company_size': ['any'],
                'budget_range': (100, 250),
                'ideal_duration': ['weeks', 'urgent']
            }
        }
    
    async def score_job(self, job: Job) -> ICPScore:
        """Score job against your ICP profiles"""
        
        # Combine job text for analysis
        job_text = f"{job.title} {job.description}".lower()
        
        best_match = None
        best_score = 0
        
        # Score against each ICP profile
        for profile_name, profile in self.icp_profiles.items():
            score = self._calculate_profile_score(job, job_text, profile)
            
            if score > best_score:
                best_score = score
                best_match = (profile_name, profile)
        
        # Determine fit level
        if best_score >= 7:
            fit_level = "High"
        elif best_score >= 5:
            fit_level = "Medium"
        else:
            fit_level = "Low"
        
        # Analyze specific aspects
        budget_fit = self._analyze_budget_fit(job)
        pain_points = self._extract_pain_points(job_text)
        hourly_rate_match = self._check_hourly_rate(job)
        project_duration_fit = self._analyze_duration(job)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(job, best_match, best_score)
        
        return ICPScore(
            fit_level=fit_level,
            confidence=min(best_score / 10, 1.0),
            industry_match=best_match[0] if best_match else "No strong match",
            pain_points=pain_points,
            budget_fit=budget_fit,
            reasoning=reasoning,
            hourly_rate_match=hourly_rate_match,
            project_duration_fit=project_duration_fit
        )
    
    def _calculate_profile_score(self, job: Job, job_text: str, profile: Dict) -> float:
        """Calculate score for a specific ICP profile"""
        score = 0
        
        # Keyword matching
        keyword_matches = sum(1 for keyword in profile['keywords'] if keyword in job_text)
        score += keyword_matches * 1.5
        
        # Pain point matching
        pain_point_matches = sum(1 for pain in profile['pain_points'] if pain in job_text)
        score += pain_point_matches * 2
        
        # Company size indicators
        for size_indicator in profile['company_size']:
            if size_indicator in job_text:
                score += 1
        
        # Budget range matching
        if job.budget and self._extract_budget_number(job.budget):
            budget_num = self._extract_budget_number(job.budget)
            budget_range = profile['budget_range']
            if budget_range[0] <= budget_num <= budget_range[1]:
                score += 2
            elif budget_num >= budget_range[0]:  # Above minimum
                score += 1
        
        # Duration matching
        duration_keywords = profile['ideal_duration']
        if any(duration in job_text for duration in duration_keywords):
            score += 1
        
        # Military/veteran bonus
        if 'military' in job_text or 'veteran' in job_text:
            score += 3
        
        # Leadership role bonus
        leadership_terms = ['lead', 'manager', 'director', 'head of', 'senior']
        if any(term in job_text for term in leadership_terms):
            score += 1
        
        return score
    
    def _analyze_budget_fit(self, job: Job) -> str:
        """Analyze if budget fits your rates"""
        if not job.budget:
            return "Budget not specified"
        
        budget_text = job.budget.lower()
        
        # Extract budget numbers
        budget_num = self._extract_budget_number(job.budget)
        
        if not budget_num:
            return "Budget unclear"
        
        if budget_num >= 100:
            return "Excellent budget fit"
        elif budget_num >= 60:
            return "Good budget fit"
        elif budget_num >= 30:
            return "Acceptable budget"
        else:
            return "Budget too low"
    
    def _extract_budget_number(self, budget_text: str) -> Optional[float]:
        """Extract numeric budget from text"""
        import re
        
        # Look for hourly rates like $50/hr or $50-100/hr
        hourly_match = re.search(r'\$(\d+)', budget_text)
        if hourly_match and ('/hr' in budget_text or 'hour' in budget_text):
            return float(hourly_match.group(1))
        
        # Look for fixed price like $5000
        fixed_match = re.search(r'\$(\d+(?:,\d+)*)', budget_text)
        if fixed_match:
            return float(fixed_match.group(1).replace(',', ''))
        
        return None
    
    def _extract_pain_points(self, job_text: str) -> List[str]:
        """Extract pain points from job description"""
        pain_point_keywords = {
            'scaling issues': ['scale', 'scaling', 'growth', 'growing pains'],
            'process problems': ['inefficient', 'manual', 'chaos', 'disorganized', 'process'],
            'team issues': ['team', 'leadership', 'management', 'coordination'],
            'system problems': ['systems', 'automation', 'workflow', 'tools'],
            'operational chaos': ['chaos', 'crisis', 'urgent', 'fix', 'stabilize']
        }
        
        found_pain_points = []
        
        for pain_point, keywords in pain_point_keywords.items():
            if any(keyword in job_text for keyword in keywords):
                found_pain_points.append(pain_point)
        
        return found_pain_points
    
    def _check_hourly_rate(self, job: Job) -> bool:
        """Check if hourly rate meets your minimum"""
        if not job.budget:
            return False
        
        budget_num = self._extract_budget_number(job.budget)
        if budget_num and ('/hr' in job.budget.lower() or 'hour' in job.budget.lower()):
            return budget_num >= 50  # Your minimum rate
        
        return False
    
    def _analyze_duration(self, job: Job) -> str:
        """Analyze project duration fit"""
        if not job.description:
            return "Duration not specified"
        
        desc_lower = job.description.lower()
        
        if any(term in desc_lower for term in ['ongoing', 'long-term', 'permanent', 'months']):
            return "Ideal duration (long-term)"
        elif any(term in desc_lower for term in ['weeks', 'month', '3-6 months']):
            return "Good duration (medium-term)"
        elif any(term in desc_lower for term in ['urgent', 'asap', 'quick', 'days']):
            return "Short-term (consider for high rate)"
        else:
            return "Duration unclear"
    
    def _generate_reasoning(self, job: Job, best_match: tuple, score: float) -> str:
        """Generate human-readable reasoning for the score"""
        if not best_match:
            return "No strong ICP match found. Consider if fits general consulting skills."
        
        profile_name, profile = best_match
        
        reasoning = f"Best match: {profile_name} ({profile['description']}). "
        
        if score >= 7:
            reasoning += "Strong alignment with your expertise and ICP. High priority for application."
        elif score >= 5:
            reasoning += "Good fit with some relevant elements. Worth investigating further."
        else:
            reasoning += "Limited fit. Consider only if other factors are compelling."
        
        # Add specific observations
        job_text = f"{job.title} {job.description}".lower()
        
        if 'military' in job_text or 'veteran' in job_text:
            reasoning += " Military/veteran background explicitly valued."
        
        if any(term in job_text for term in ['scaling', 'growth', 'operations']):
            reasoning += " Clear operational challenges that match your experience."
        
        return reasoning
    
    def get_icp_summary(self) -> Dict:
        """Get summary of your ICP profiles for reference"""
        return {
            name: {
                'description': profile['description'],
                'budget_range': f"${profile['budget_range'][0]}-{profile['budget_range'][1]}/hr",
                'ideal_duration': profile['ideal_duration']
            }
            for name, profile in self.icp_profiles.items()
        }
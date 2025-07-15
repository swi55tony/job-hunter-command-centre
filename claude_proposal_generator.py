# claude_proposal_generator.py - AI-Powered Proposal Generation
import asyncio
import aiohttp
import json
import os
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import asdict

class ClaudeProposalGenerator:
    def __init__(self, api_key: str = None):
        # Get API key from environment variables or Streamlit secrets
        if api_key:
            self.api_key = api_key
        else:
            # Try to get from environment variables first (for local use)
            self.api_key = os.getenv('CLAUDE_API_KEY')
            
            # If running in Streamlit, try to get from secrets
            if not self.api_key:
                try:
                    import streamlit as st
                    self.api_key = st.secrets.get('claude_api_key')
                except:
                    pass
        
        self.base_url = "https://api.anthropic.com/v1/messages"
        
        # Your unique value proposition
        self.background_profile = """
        MY UNIQUE BACKGROUND:
        - Ex-Military Professional (1994-2005): 11 years service, jumped from planes/helicopters
        - Rapid Business Advancement: HP → Capita → Public Sector operations roles
        - Executive & Growth Coach: Helping leaders and companies scale systematically
        - Business Coach: Guiding founder-led companies through operational transformation
        - Growth Consultant: Specializing in 20-50 person companies at tipping points
        - Track Record: Cut dead weight, fired C-players, built scalable systems that work
        - Approach: Military precision + executive coaching + business pragmatism = sustainable results
        
        WHAT MAKES ME DIFFERENT:
        - I don't just consult - I coach leaders while implementing operational systems
        - Military training + executive coaching = unique combination for high-pressure scaling
        - Proven ability to coach founders through the transition from chaos to systematic growth
        - Experience coaching both individual executives and entire leadership teams
        - Business coaching expertise that addresses both personal and operational challenges
        """
        
        self.proposal_framework = """
        WINNING PROPOSAL STRUCTURE (No greeting - straight to value):
        1. HOOK: Immediate value proposition connecting to their specific challenge/opportunity
        2. CREDIBILITY: Brief relevant experience that builds trust  
        3. SOLUTION: 3-4 structured deliverables with clear outcomes
        4. PROOF: Specific results and relevant experience
        5. CTA: Professional call invitation with strategic framing
        
        TONE GUIDELINES:
        - Executive-level confidence without arrogance
        - Specific, measurable outcomes
        - Strategic perspective, not tactical
        - Military precision translated to business results
        - No generic consultant speak
        """
    
    async def create_proposal(self, job: Dict, icp_score) -> Dict:
        """Generate tailored proposal using Claude API"""
        
        try:
            # Build comprehensive prompt
            prompt = self._build_proposal_prompt(job, icp_score)
            
            # Call Claude API if key is available
            proposal_text = None
            if self.api_key:
                proposal_text = await self._call_claude_api(prompt)
            
            if not proposal_text:
                # Fallback to template-based proposal
                proposal_text = self._generate_fallback_proposal(job, icp_score)
            
            # Calculate metrics
            word_count = len(proposal_text.split())
            
            return {
                'proposal_text': proposal_text,
                'word_count': word_count,
                'generated_at': datetime.now().isoformat(),
                'model_used': 'claude-3-sonnet' if self.api_key else 'template',
                'job_id': getattr(job, 'id', 'unknown'),
                'icp_score': icp_score.fit_level,
                'industry_match': icp_score.industry_match,
                'confidence': icp_score.confidence
            }
            
        except Exception as e:
            print(f"⚠️ Proposal generation error: {e}")
            
            # Return fallback proposal
            fallback_text = self._generate_fallback_proposal(job, icp_score)
            return {
                'proposal_text': fallback_text,
                'word_count': len(fallback_text.split()),
                'generated_at': datetime.now().isoformat(),
                'model_used': 'fallback_template',
                'job_id': getattr(job, 'id', 'unknown'),
                'icp_score': icp_score.fit_level,
                'error': str(e)
            }
    
    def _build_proposal_prompt(self, job, icp_score) -> str:
        """Build comprehensive prompt for Claude"""
        
        job_title = getattr(job, 'title', 'Unknown Job')
        job_description = getattr(job, 'description', 'No description available')
        job_budget = getattr(job, 'budget', 'Not specified')
        
        prompt = f"""
        Create a winning Upwork proposal for this executive-level opportunity:
        
        JOB DETAILS:
        Title: {job_title}
        Description: {job_description[:500]}...
        Budget: {job_budget}
        
        ICP ANALYSIS:
        Industry Match: {icp_score.industry_match}
        Pain Points Identified: {', '.join(icp_score.pain_points)}
        Fit Level: {icp_score.fit_level} (Confidence: {icp_score.confidence:.0%})
        Reasoning: {icp_score.reasoning}
        
        {self.background_profile}
        
        {self.proposal_framework}
        
        SPECIFIC REQUIREMENTS FOR THIS PROPOSAL:
        - Length: 120-150 words maximum
        - Match their urgency/energy level from the job posting
        - Include ONE specific insight about their {icp_score.industry_match} challenge
        - Mention military background only if it adds credibility for their specific need
        - Focus on business results, not military stories
        - End with a clear call-to-action for next steps
        - Sound like a seasoned executive, not a salesperson
        
        AVOID:
        - Generic consultant speak
        - Long military stories
        - Overselling
        - Multiple CTAs
        - Buzzwords without substance
        
        Generate a proposal that makes them think: "This person gets it and can solve our problem."
        """
        
        return prompt
    
    async def _call_claude_api(self, prompt: str) -> Optional[str]:
        """Call Claude API to generate proposal"""
        
        if not self.api_key:
            return None  # Skip API call if no key provided
        
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['content'][0]['text']
                    else:
                        print(f"❌ Claude API error: {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Claude API call failed: {e}")
            return None
    
    def _generate_fallback_proposal(self, job, icp_score) -> str:
        """Generate template-based proposal when API isn't available"""
        
        job_title = getattr(job, 'title', 'this opportunity')
        
        # Choose template based on ICP match
        if icp_score.industry_match == 'scaling_startup':
            template = self._startup_template(job_title, icp_score)
        elif icp_score.industry_match == 'operations_overhaul':
            template = self._operations_template(job_title, icp_score)
        elif icp_score.industry_match == 'revenue_leadership':
            template = self._revenue_template(job_title, icp_score)
        elif icp_score.industry_match == 'strategic_consulting':
            template = self._strategic_template(job_title, icp_score)
        elif icp_score.industry_match == 'team_leadership':
            template = self._executive_coaching_template(job_title, icp_score)
        elif icp_score.industry_match == 'crisis_management':
            template = self._crisis_template(job_title, icp_score)
        else:
            template = self._general_template(job_title, icp_score)
        
        return template
    
    def _startup_template(self, job_title: str, icp_score) -> str:
        return f"""You're scaling past founder-led operations and need systematic growth without losing agility. That's where military-trained operational expertise combined with executive coaching makes the difference.

I'm a business coach and growth consultant who's helped 20-50 person companies transition from gut-feel decisions to data-driven operations—bringing discipline learned in high-pressure military environments to business scaling challenges.

Here's how I can accelerate your operational evolution:

Leadership & Team Development
• Executive coaching for founders navigating the transition from doer to leader
• Build accountability frameworks and decision-making hierarchies for faster execution
• Coach leadership teams through operational changes while maintaining team alignment

Operational Assessment & Structure
• Rapid diagnostic of current bottlenecks and growth constraints
• Build scalable systems that work without constant founder intervention
• Implement performance dashboards for strategic control vs. reactive management

Growth Infrastructure & Coaching
• Business coaching that addresses both personal leadership and operational challenges
• Create processes that maintain quality while scaling rapidly
• Coach teams through change management during operational transformation

Relevant Experience:
• Business coach and growth consultant specializing in operational transformation
• Ex-military professional with rapid advancement through operations roles at HP and Capita
• Executive coach with track record of helping founders scale beyond personal limitations
• Specialized in coaching leaders while implementing systems that support 2-3x growth

This is the right time to combine leadership development with operational excellence—and I bring both the coaching expertise and operational discipline to execute that transformation.

Would you like to set up a brief call to discuss your specific scaling challenges?

Best regards,
Antony"""

    def _operations_template(self, job_title: str, icp_score) -> str:
        return f"""Hello,

I noticed your {job_title} posting and it aligns perfectly with my expertise - stepping into operational chaos and creating systematic efficiency.

My background combines military operational training with proven business results. I've built and stabilized multi-layer teams across HP, Capita, and the Public Sector, specializing in cutting through inefficiencies and implementing processes that actually work.

What I bring:
• Rapid operational diagnosis and systematic improvement
• Experience moving teams from manual chaos to automated workflows
• Track record of identifying and eliminating operational dead weight

The military taught me how to impose order quickly. Business experience taught me how to make it sustainable and scalable.

Would you be open to a brief conversation about your specific operational challenges?

Best,
Tony"""

    def _revenue_template(self, job_title: str, icp_score) -> str:
        return f"""You've built solid revenue foundations and now need systematic optimization to unlock the next level of growth. That's where military-trained revenue operations expertise delivers measurable impact.

I've helped businesses scale revenue operations from manual processes to predictable, data-driven systems—applying the same systematic approach that drove my rapid advancement through sales operations at HP and Capita.

Here's how I can accelerate your revenue performance:

Revenue Operations Optimization
• Assess current pipeline efficiency and identify conversion bottlenecks
• Build automated systems for lead scoring, nurturing, and progression tracking
• Implement forecasting models that actually predict with accuracy

Sales Team Structure & Performance
• Design accountability frameworks that drive consistent results
• Create compensation structures and performance metrics that align with growth
• Establish clear sales processes that scale without constant management

Strategic Revenue Planning
• Develop data-driven pricing strategies and market positioning
• Build territory management and account segmentation frameworks
• Create revenue reporting systems for strategic decision-making

Relevant Experience:
• Revenue operations expertise from HP and Capita with proven scaling results
• Military background in high-pressure environments where performance was non-negotiable
• Track record of systematizing manual processes and eliminating revenue inefficiencies

This is the right time to evolve from gut-feel revenue management to predictable growth systems—and I bring the operational discipline to execute that transformation.

Would you like to set up a brief call to discuss your specific revenue optimization challenges?

Best regards,
Antony"""

    def _executive_coaching_template(self, job_title: str, icp_score) -> str:
        return f"""You need leadership development that drives business results—not generic coaching, but executive guidance that translates directly to operational performance. That's where military-trained leadership expertise meets proven business coaching.

I'm an executive coach and business consultant who's worked with scaling companies, bringing the same leadership principles that drove rapid advancement through high-pressure environments at HP and Capita.

Here's how I can accelerate your leadership effectiveness:

Executive Leadership Development
• One-on-one coaching for founders and senior leaders navigating scaling challenges
• Leadership assessment and development planning based on business growth objectives
• Decision-making frameworks for high-pressure situations and complex business challenges

Team Leadership & Performance
• Coach leadership teams through organizational change and growth transitions
• Build accountability structures and performance management systems that drive results
• Develop communication and delegation skills for leaders managing larger teams

Growth Leadership Coaching
• Business coaching that addresses both personal leadership and operational challenges
• Strategic thinking development for leaders transitioning from tactical to strategic roles
• Coach founders through the evolution from hands-on operators to organizational leaders

Relevant Experience:
• Executive coach and business coach specializing in growth-stage companies
• Military leadership background with experience in high-pressure, results-driven environments
• Business leadership experience from rapid advancement through operations roles at HP and Capita
• Track record of coaching leaders while implementing systems that support organizational scaling

This is the right time to invest in leadership development that drives measurable business outcomes—and I bring both the coaching expertise and operational credibility to deliver results.

Would you like to set up a brief call to discuss your specific leadership development needs?

Best regards,
Antony"""

    def _strategic_template(self, job_title: str, icp_score) -> str:
        return f"""You need strategic clarity to navigate market positioning and competitive advantage—not generic consulting, but executable frameworks that drive decisions. That's where military-trained strategic thinking meets proven business execution.

I've developed go-to-market strategies and business frameworks for scaling companies, bringing the same systematic approach that enabled rapid advancement through strategic roles at HP and Capita.

Here's how I can sharpen your strategic positioning:

Market Analysis & Positioning
• Conduct comprehensive competitive landscape analysis and opportunity mapping
• Develop clear value proposition frameworks that differentiate in crowded markets
• Create positioning strategies that translate to actionable marketing and sales messaging

Strategic Planning & Execution
• Build strategic roadmaps with clear milestones, resource requirements, and success metrics
• Develop scenario planning models for market entry, expansion, or pivot decisions
• Create decision-making frameworks that maintain strategic focus during rapid growth

Business Model & Revenue Strategy
• Analyze current business model efficiency and identify optimization opportunities
• Develop pricing strategies and revenue stream diversification options
• Create strategic partnership frameworks and channel development strategies

Relevant Experience:
• Strategic business development experience from corporate environments at HP and Capita
• Military background in complex situation analysis and strategic decision-making under pressure
• Track record of translating strategic thinking into executable business frameworks

This is the right time to move from tactical execution to strategic leadership—and I bring the analytical rigor to build strategies that actually get implemented.

Would you like to set up a brief call to discuss your specific strategic challenges?

Best regards,
Antony"""

    def _crisis_template(self, job_title: str, icp_score) -> str:
        return f"""Hello,

Your {job_title} situation sounds like exactly where my background delivers the most value - stepping into urgent operational challenges and stabilizing them quickly.

Military service taught me how to handle high-pressure situations and impose clarity when everything's chaotic. Business experience at HP and Capita taught me how to make those improvements sustainable.

My crisis management approach:
• Rapid assessment to identify critical failure points
• Immediate stabilization measures while building long-term solutions
• Clear communication and accountability structures

I've successfully turned around operational crises where time was critical and failure wasn't an option. That combination of urgency and systematic thinking is exactly what these situations require.

Can we discuss your specific situation this week?

Best,
Tony"""

    def _general_template(self, job_title: str, icp_score) -> str:
        return f"""Hi,

Your {job_title} posting aligns well with my background in operational excellence and business transformation.

I'm an ex-military professional who rapidly advanced through operations roles at HP, Capita, and the Public Sector. What makes me effective is combining military-trained operational discipline with proven business results.

Specific expertise:
• Building scalable operational systems from ground up
• Team leadership and performance optimization
• Strategic implementation that delivers measurable results

Military service taught me to handle complex, high-pressure situations. Business experience taught me how to translate that into sustainable commercial success.

Would you be interested in a brief conversation about how this applies to your specific needs?

Best regards,
Tony"""

    def generate_multiple_variants(self, job, icp_score, count: int = 3) -> List[Dict]:
        """Generate multiple proposal variants for A/B testing"""
        variants = []
        
        for i in range(count):
            # Vary the approach slightly for each variant
            variant_styles = ['direct', 'consultative', 'results_focused']
            style = variant_styles[i % len(variant_styles)]
            
            proposal = asyncio.run(self.create_proposal(job, icp_score))
            proposal['variant_style'] = style
            proposal['variant_number'] = i + 1
            
            variants.append(proposal)
        
        return variants

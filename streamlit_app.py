import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List
import time

# Set page config
st.set_page_config(
    page_title="Job Hunter Command Centre",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'jobs_data' not in st.session_state:
    st.session_state.jobs_data = []
if 'campaign_running' not in st.session_state:
    st.session_state.campaign_running = False
if 'approved_jobs' not in st.session_state:
    st.session_state.approved_jobs = []
if 'rejected_jobs' not in st.session_state:
    st.session_state.rejected_jobs = []

# Custom CSS for military-style interface
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin: 0.5rem 0;
    }
    .high-priority {
        border-left: 4px solid #ff6b6b;
        background: #fff5f5;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .medium-priority {
        border-left: 4px solid #ffa726;
        background: #fff8e1;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .approved-job {
        border-left: 4px solid #4caf50;
        background: #f1f8e9;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .command-header {
        background: linear-gradient(90deg, #2c3e50 0%, #34495e 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def role_selection():
    """Role selection interface"""
    st.markdown('<div class="command-header"><h1>🎖️ JOB HUNTER COMMAND CENTRE</h1><p>Select your operational role</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.write("### Choose Your Role")
        
        if st.button("👩‍💼 VA Operations", use_container_width=True, type="primary"):
            st.session_state.user_role = "va"
            st.rerun()
            
        if st.button("🎖️ Commander (Antony)", use_container_width=True, type="secondary"):
            st.session_state.user_role = "commander"
            st.rerun()

def va_dashboard():
    """VA Operations Dashboard"""
    st.markdown('<div class="command-header"><h1>👩‍💼 VA OPERATIONS DASHBOARD</h1><p>Search, analyse, and report - no client contact</p></div>', unsafe_allow_html=True)
    
    # Sidebar controls
    with st.sidebar:
        st.write("### Campaign Controls")
        
        campaign_modes = {
            "full": "Full Hunt (All Campaigns)",
            "executive": "Executive Only",
            "strategic": "Strategic Consulting",
            "coaching": "Coaching & Mentoring", 
            "quick": "Quick Hunt (Fast Results)"
        }
        
        selected_mode = st.selectbox("Campaign Mode", list(campaign_modes.keys()), 
                                   format_func=lambda x: campaign_modes[x])
        
        if st.button("🚀 Launch Campaign", type="primary", disabled=st.session_state.campaign_running):
            run_campaign_simulation(selected_mode)
        
        if st.session_state.campaign_running:
            if st.button("⏹️ Stop Campaign", type="secondary"):
                st.session_state.campaign_running = False
                st.rerun()
        
        st.write("---")
        st.write("### VA Guidelines")
        st.info("""
        **Your Mission:**
        - Run job searches and analysis
        - Score opportunities objectively  
        - NO client contact whatsoever
        - NO proposal submissions
        - Flag high-value targets for commander review
        """)
    
    # Main dashboard
    if st.session_state.campaign_running:
        show_campaign_progress()
    else:
        show_va_results()

def commander_dashboard():
    """Commander Dashboard - Strategic Control"""
    st.markdown('<div class="command-header"><h1>🎖️ COMMANDER DASHBOARD</h1><p>Strategic oversight and tactical execution</p></div>', unsafe_allow_html=True)
    
    # Sidebar intel
    with st.sidebar:
        st.write("### Mission Control")
        
        # Pipeline overview
        total_jobs = len(st.session_state.jobs_data)
        approved = len(st.session_state.approved_jobs)
        rejected = len(st.session_state.rejected_jobs)
        pending_review = total_jobs - approved - rejected
        
        st.metric("Total Intelligence", total_jobs)
        st.metric("Approved Targets", approved)
        st.metric("Pending Review", pending_review)
        
        if pending_review > 0:
            st.warning(f"⚠️ {pending_review} targets awaiting your review")
        
        st.write("---")
        st.write("### Quick Actions")
        
        if st.button("📊 Generate Battle Plan"):
            generate_battle_plan()
            
        if st.button("📄 Export Approved Jobs"):
            export_approved_jobs()
    
    # Main command interface
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Target Review", "📈 Campaign Intel", "💼 Approved Operations", "⚙️ System Status"])
    
    with tab1:
        show_target_review()
    
    with tab2:
        show_campaign_analytics()
    
    with tab3:
        show_approved_jobs()
    
    with tab4:
        show_system_status()

def run_campaign_simulation(mode: str):
    """Simulate running a campaign (replace with actual campaign logic)"""
    st.session_state.campaign_running = True
    
    # Generate some sample data for demonstration
    sample_jobs = generate_sample_jobs(mode)
    st.session_state.jobs_data.extend(sample_jobs)
    
    st.success(f"🚀 Campaign launched in {mode} mode")
    time.sleep(2)
    st.session_state.campaign_running = False
    st.rerun()

def generate_sample_jobs(mode: str) -> List[Dict]:
    """Generate sample job data for demonstration"""
    jobs = [
        {
            "id": f"job_{datetime.now().timestamp()}_{i}",
            "title": f"Fractional COO - Scale-up Operations",
            "budget": "$80/hr",
            "campaign_score": 8.5,
            "military_fit": 0.85,
            "campaign": "executive_suite",
            "priority": "HIGH",
            "url": "https://upwork.com/sample-job-1",
            "description": "Need experienced operations leader to scale 25-person team...",
            "timestamp": datetime.now().isoformat()
        },
        {
            "id": f"job_{datetime.now().timestamp()}_{i+1}",
            "title": "Business Strategy Consultant - Series A Startup",
            "budget": "$100-150/hr",
            "campaign_score": 7.8,
            "military_fit": 0.72,
            "campaign": "strategic_consulting", 
            "priority": "HIGH",
            "url": "https://upwork.com/sample-job-2",
            "description": "Looking for strategic advisor to help navigate growth phase...",
            "timestamp": datetime.now().isoformat()
        },
        {
            "id": f"job_{datetime.now().timestamp()}_{i+2}",
            "title": "Executive Coach for CEO",
            "budget": "$75/hr",
            "campaign_score": 6.9,
            "military_fit": 0.68,
            "campaign": "executive_coaching",
            "priority": "MEDIUM",
            "url": "https://upwork.com/sample-job-3",
            "description": "First-time CEO needs experienced mentor...",
            "timestamp": datetime.now().isoformat()
        }
    ]
    return jobs

def show_campaign_progress():
    """Show live campaign progress"""
    st.write("### 🚀 Campaign In Progress")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Simulate progress
    for i in range(100):
        progress_bar.progress(i + 1)
        status_text.text(f'Analysing targets... {i + 1}% complete')
        time.sleep(0.01)
    
    st.success("✅ Campaign complete! Processing results...")

def show_va_results():
    """Show VA results summary"""
    if not st.session_state.jobs_data:
        st.info("📡 No campaign data yet. Launch a campaign to begin operations.")
        return
    
    st.write("### 📊 Intelligence Gathered")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_jobs = len(st.session_state.jobs_data)
    high_value = len([j for j in st.session_state.jobs_data if j.get('campaign_score', 0) >= 7.0])
    avg_score = sum(j.get('campaign_score', 0) for j in st.session_state.jobs_data) / total_jobs if total_jobs > 0 else 0
    avg_military_fit = sum(j.get('military_fit', 0) for j in st.session_state.jobs_data) / total_jobs if total_jobs > 0 else 0
    
    with col1:
        st.metric("Total Targets", total_jobs)
    with col2:
        st.metric("High-Value", high_value)
    with col3:
        st.metric("Avg Score", f"{avg_score:.1f}/10")
    with col4:
        st.metric("Avg Military Fit", f"{avg_military_fit:.1%}")
    
    # Recent discoveries
    st.write("### 🎯 Latest Intelligence")
    
    for job in sorted(st.session_state.jobs_data, key=lambda x: x.get('campaign_score', 0), reverse=True)[:5]:
        priority_class = "high-priority" if job.get('priority') == 'HIGH' else "medium-priority"
        
        st.markdown(f'''
        <div class="{priority_class}">
            <strong>{job.get('title', 'Unknown Title')}</strong><br>
            💰 {job.get('budget', 'Not specified')} | 
            🎯 Score: {job.get('campaign_score', 0):.1f}/10 | 
            🎖️ Military Fit: {job.get('military_fit', 0):.1%}<br>
            📍 Campaign: {job.get('campaign', 'Unknown')}
        </div>
        ''', unsafe_allow_html=True)

def show_target_review():
    """Commander target review interface"""
    if not st.session_state.jobs_data:
        st.info("📡 No intelligence data. Deploy VA to gather targets.")
        return
    
    st.write("### 🎯 High-Value Targets Requiring Review")
    
    # Filter for pending review
    pending_jobs = [
        job for job in st.session_state.jobs_data 
        if job['id'] not in [j['id'] for j in st.session_state.approved_jobs] 
        and job['id'] not in [j['id'] for j in st.session_state.rejected_jobs]
        and job.get('campaign_score', 0) >= 6.0  # Only show decent scores
    ]
    
    if not pending_jobs:
        st.success("✅ All high-value targets reviewed")
        return
    
    for job in sorted(pending_jobs, key=lambda x: x.get('campaign_score', 0), reverse=True):
        with st.expander(f"🎯 {job.get('title', 'Unknown')} - Score: {job.get('campaign_score', 0):.1f}/10"):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Budget:** {job.get('budget', 'Not specified')}")
                st.write(f"**Campaign:** {job.get('campaign', 'Unknown')}")
                st.write(f"**Military Fit:** {job.get('military_fit', 0):.1%}")
                st.write(f"**Priority:** {job.get('priority', 'Unknown')}")
                
                if job.get('description'):
                    st.write("**Description:**")
                    st.write(job['description'][:300] + "..." if len(job.get('description', '')) > 300 else job.get('description', ''))
                
                if job.get('url'):
                    st.write(f"**URL:** {job['url']}")
            
            with col2:
                st.write("**Decision Required:**")
                
                col_approve, col_reject = st.columns(2)
                
                with col_approve:
                    if st.button("✅ Approve", key=f"approve_{job['id']}", type="primary"):
                        st.session_state.approved_jobs.append(job)
                        st.success("Target approved for engagement")
                        st.rerun()
                
                with col_reject:
                    if st.button("❌ Reject", key=f"reject_{job['id']}", type="secondary"):
                        st.session_state.rejected_jobs.append(job)
                        st.info("Target marked as unsuitable")
                        st.rerun()

def show_campaign_analytics():
    """Show campaign performance analytics"""
    if not st.session_state.jobs_data:
        st.info("📊 No data for analysis yet")
        return
    
    st.write("### 📈 Campaign Intelligence Analysis")
    
    # Create dataframe for analysis
    df = pd.DataFrame(st.session_state.jobs_data)
    
    # Campaign performance chart
    col1, col2 = st.columns(2)
    
    with col1:
        campaign_counts = df['campaign'].value_counts()
        fig = px.bar(
            x=campaign_counts.index, 
            y=campaign_counts.values,
            title="Targets by Campaign",
            labels={'x': 'Campaign', 'y': 'Count'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.histogram(
            df, 
            x='campaign_score', 
            title="Score Distribution",
            bins=20
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Performance metrics
    st.write("### 🎯 Performance Metrics")
    
    metrics_df = df.groupby('campaign').agg({
        'campaign_score': ['mean', 'max', 'count'],
        'military_fit': 'mean'
    }).round(2)
    
    st.dataframe(metrics_df, use_container_width=True)

def show_approved_jobs():
    """Show approved jobs ready for action"""
    st.write("### 💼 Approved Targets - Ready for Engagement")
    
    if not st.session_state.approved_jobs:
        st.info("🎯 No approved targets yet. Review pending intelligence first.")
        return
    
    for job in sorted(st.session_state.approved_jobs, key=lambda x: x.get('campaign_score', 0), reverse=True):
        with st.container():
            st.markdown(f'''
            <div class="approved-job">
                <strong>{job.get('title', 'Unknown Title')}</strong><br>
                💰 {job.get('budget', 'Not specified')} | 
                🎯 Score: {job.get('campaign_score', 0):.1f}/10 | 
                🎖️ Military Fit: {job.get('military_fit', 0):.1%}
            </div>
            ''', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("📝 Generate Proposal", key=f"proposal_{job['id']}"):
                    generate_proposal_placeholder(job)
            
            with col2:
                if st.button("🔗 Open Job", key=f"open_{job['id']}"):
                    st.write(f"Opening: {job.get('url', 'No URL')}")
            
            with col3:
                if st.button("✅ Mark Submitted", key=f"submit_{job['id']}"):
                    mark_job_submitted(job)

def show_system_status():
    """Show system status and connections"""
    st.write("### ⚙️ System Status")
    
    # Connection status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🌐 Browser Connection**
        
        Status: ⚠️ Not Connected
        
        *Chrome debugging required*
        """)
    
    with col2:
        st.markdown("""
        **🤖 Claude API**
        
        Status: ✅ Connected
        
        *Proposal generation ready*
        """)
    
    with col3:
        st.markdown("""
        **📊 Notion Database**
        
        Status: ✅ Connected
        
        *Pipeline tracking active*
        """)
    
    # System logs
    st.write("### 📋 Recent Activity")
    
    activity_log = [
        {"time": "14:32", "event": "VA launched executive campaign", "status": "✅"},
        {"time": "14:28", "event": "Commander approved 3 targets", "status": "✅"}, 
        {"time": "14:25", "event": "High-value target identified", "status": "🎯"},
        {"time": "14:20", "event": "Campaign analysis complete", "status": "✅"}
    ]
    
    for entry in activity_log:
        st.write(f"{entry['status']} **{entry['time']}** - {entry['event']}")

def generate_proposal_placeholder(job):
    """Placeholder for proposal generation"""
    st.success(f"📝 Proposal generated for: {job.get('title', 'Unknown')}")
    st.info("💡 In production: This would integrate with Claude API to generate a tailored proposal")

def mark_job_submitted(job):
    """Mark job as submitted"""
    st.success(f"✅ Marked as submitted: {job.get('title', 'Unknown')}")
    # In production: Update Notion database

def generate_battle_plan():
    """Generate strategic battle plan"""
    st.success("📊 Battle plan generated")
    st.info("💡 In production: This would create a comprehensive strategic document")

def export_approved_jobs():
    """Export approved jobs"""
    if st.session_state.approved_jobs:
        df = pd.DataFrame(st.session_state.approved_jobs)
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"approved_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No approved jobs to export")

# Role selector in sidebar
with st.sidebar:
    if st.session_state.user_role:
        role_display = "👩‍💼 VA" if st.session_state.user_role == "va" else "🎖️ Commander"
        st.write(f"**Current Role:** {role_display}")
        
        if st.button("🔄 Switch Role"):
            st.session_state.user_role = None
            st.rerun()

# Main app logic
if st.session_state.user_role is None:
    role_selection()
elif st.session_state.user_role == "va":
    va_dashboard()
elif st.session_state.user_role == "commander":
    commander_dashboard()

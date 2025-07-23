# Update your Streamlit app's run_actual_campaign function

async def run_actual_campaign(mode: str) -> List[Dict]:
    """Run actual campaign using enhanced RSS connector"""
    try:
        # Import the enhanced RSS connector
        from enhanced_upwork_rss import run_upwork_campaign
        
        # Run the campaign
        jobs_data = await run_upwork_campaign(mode)
        
        print(f"RSS Campaign completed: {len(jobs_data)} jobs found")
        return jobs_data
        
    except ImportError as e:
        raise Exception(f"Enhanced RSS module not available: {e}")
    except Exception as e:
        raise Exception(f"Campaign error: {e}")

# Also update your run_campaign_simulation function
def run_campaign_simulation(mode: str):
    """Run actual campaign using integrated modules"""
    st.session_state.campaign_running = True
    
    try:
        # Show immediate feedback
        with st.spinner('🎯 Scanning Upwork RSS feeds...'):
            # Run actual RSS campaign
            sample_jobs = asyncio.run(run_actual_campaign(mode))
            st.session_state.jobs_data.extend(sample_jobs)
        
        st.success(f"🚀 Campaign completed in {mode} mode - {len(sample_jobs)} jobs analysed")
        
    except Exception as e:
        # Show the actual error for debugging
        st.error(f"❌ Campaign failed: {str(e)}")
        
        # Only fall back to demo if specifically requested
        if st.button("Use demo data instead?"):
            with st.spinner('Generating demo data...'):
                sample_jobs = generate_demo_jobs(mode)
                st.session_state.jobs_data.extend(sample_jobs)
            st.info(f"📊 Demo campaign completed - {len(sample_jobs)} sample jobs")
    
    # Force completion
    st.session_state.campaign_running = False
    time.sleep(0.5)
    st.rerun()
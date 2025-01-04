import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os
import asyncio
from websearcher import WebSearcher
from datetime import datetime
from fpdf import FPDF, XPos, YPos
import textwrap
from organization_searcher import OrganizationSearcher
from database_manager import DatabaseManager
from data_processor import DataProcessor
import time

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Get API keys from environment variables
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Validate API keys
if not SERPAPI_KEY or not GROQ_API_KEY:
    st.error("Please set up your API keys in the .env file")
    st.stop()

# At the start of your app, add this check
if not os.getenv('SERPAPI_KEY'):
    st.error("⚠️ SERPAPI_KEY is not set. Please set it in your environment variables.")
    st.stop()

# Initialize clients
groq_client = Groq(api_key=GROQ_API_KEY)
web_searcher = WebSearcher()
db_manager = DatabaseManager()
data_processor = DataProcessor()
org_searcher = OrganizationSearcher()

# Initialize session state
if 'report' not in st.session_state:
    st.session_state.report = None
if 'sources' not in st.session_state:
    st.session_state.sources = None
if 'query' not in st.session_state:
    st.session_state.query = None

# Main title
st.title("Political Research Assistant")

# Report Generation Section
st.header("Report Generation")

# Input for report topic
query = st.text_input("Enter your research topic:", key="report_query")

if query:
    st.session_state.query = query

def generate_report(content, sources):
    """Generate report using Groq"""
    prompt = f"""Based on the following content, generate a comprehensive report:
    {content}
    
    Sources:
    {sources}
    
    Please structure the report with:
    1. Executive Summary
    2. Key Findings
    3. Detailed Analysis
    4. Conclusion
    
    Guidelines:
    - Include relevant citations from the sources
    - Be objective and factual
    - Highlight key insights and trends
    - Keep sections well-organized and clear
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        return None

def generate_report_clicked():
    """Handle report generation button click"""
    with st.spinner("🔎 Searching and analyzing content..."):
        try:
            result = asyncio.run(web_searcher.search_company_info(st.session_state.query))
            
            if not result or not result['articles']:
                st.error("Unable to fetch search results. Please try a different query.")
                return

            sources = "\n".join([f"- {article['source']}: {article['url']}" 
                               for article in result['articles']])
            
            report = generate_report(result['content'], sources)
            
            if report:
                st.session_state.report = report
                st.session_state.sources = sources
                st.session_state.articles = result['articles']
            else:
                st.error("Failed to generate report")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"Error in report generation: {str(e)}")

# Generate Report button
if st.button("Generate Report", key="generate_report"):
    generate_report_clicked()

# Display report if available
if st.session_state.report:
    st.markdown("### Generated Report")
    
    # Create formatted text for copying
    formatted_report = f"""Research Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{st.session_state.report}

Sources:
{st.session_state.sources}"""

    # Display report with copy button using custom HTML/CSS
    st.markdown("""
    <style>
    .report-container {
        position: relative;
        padding: 15px;
        background-color: rgba(49, 51, 63, 0.8);
        border-radius: 10px;
        margin: 10px 0;
    }
    .copy-icon {
        position: absolute;
        top: 10px;
        right: 10px;
        cursor: pointer;
        padding: 5px;
        border-radius: 5px;
        background-color: rgba(70, 70, 70, 0.8);
    }
    .copy-icon:hover {
        background-color: rgba(90, 90, 90, 0.8);
    }
    </style>
    """, unsafe_allow_html=True)

    st.code(formatted_report, language="text")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("📥 Download PDF"):
            try:
                # Create PDF with larger page size
                pdf = FPDF(format='A4')  # Standard A4 size
                pdf.add_page()
                
                # Use Helvetica instead of Arial and fix deprecated parameters
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, "Research Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
                pdf.ln(10)
                
                # Add timestamp
                pdf.set_font("Helvetica", "I", 10)
                pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(10)
                
                # Add content with proper text wrapping
                pdf.set_font("Helvetica", "", 12)
                
                # Calculate available width for text
                effective_width = pdf.w - 2 * pdf.l_margin
                
                # Add report content with proper wrapping
                lines = textwrap.wrap(st.session_state.report, width=70)  # Adjust width for better fit
                for line in lines:
                    pdf.multi_cell(effective_width, 10, line)
                    pdf.ln(2)  # Small spacing between lines
                
                # Add sources
                if st.session_state.sources:
                    pdf.ln(10)
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.cell(0, 10, "Sources:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(5)
                    
                    pdf.set_font("Helvetica", "", 12)
                    source_lines = st.session_state.sources.split('\n')
                    for line in source_lines:
                        wrapped_source = textwrap.wrap(line, width=70)
                        for wrapped_line in wrapped_source:
                            pdf.multi_cell(effective_width, 10, wrapped_line)
                        pdf.ln(2)
                
                # Save the PDF
                pdf_filename = f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf.output(pdf_filename)
                
                # Read PDF file and create download button
                with open(pdf_filename, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="📄 Save PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
                
                # Clean up the temporary file
                os.remove(pdf_filename)
                
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
                logging.error(f"PDF generation error: {str(e)}")

    # Display sources separately if needed
    if st.session_state.sources:
        st.markdown("### Sources")
        st.markdown(st.session_state.sources)

# Political Organization Research section
st.markdown("---")
st.header("Political Organization Research")

# Add tab selection for different views
tab1, tab2, tab3 = st.tabs(["Research Organization", "Search Database", "Browse Organizations"])

async def research_organization(org_name):
    """Async function to research organization"""
    raw_data = await org_searcher.fetch_organization_data(org_name)
    return raw_data

with tab1:
    st.markdown("""
    <style>
    /* General container styling */
    .research-container {
        padding: 20px;
        margin: 10px 0;
    }
    
    /* Results container styling */
    .results-box {
        background-color: rgba(49, 51, 63, 0.8) !important;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: #ffffff !important;
        border: 1px solid rgba(250, 250, 250, 0.2);
    }
    
    /* Section headers */
    .section-title {
        color: #ffffff !important;
        font-size: 1.2em;
        margin: 15px 0;
        padding-bottom: 5px;
        border-bottom: 1px solid rgba(250, 250, 250, 0.2);
    }
    
    /* Info labels */
    .info-tag {
        font-weight: bold;
        color: #ff9494 !important;
        min-width: 120px;
        display: inline-block;
    }
    
    /* Data rows */
    .data-row {
        margin: 10px 0;
        padding: 5px 0;
    }
    
    /* Links styling */
    .results-box a {
        color: #00ff95 !important;
        text-decoration: none;
    }
    
    .results-box a:hover {
        text-decoration: underline;
        opacity: 0.8;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: rgba(49, 51, 63, 0.8);
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        background-color: rgba(59, 61, 73, 0.8);
    }
    
    /* Status messages */
    .success-message {
        color: #00ff95 !important;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Cards for different sections */
    .info-card {
        background-color: rgba(59, 61, 73, 0.8) !important;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #ffffff !important;
        border: 1px solid rgba(250, 250, 250, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("Research Organizations")
    
    # Create two columns for search
    search_col1, search_col2 = st.columns([3, 1])
    
    with search_col1:
        search_query = st.text_input("Enter organization name:", key="org_search")
    
    with search_col2:
        search_button = st.button("🔍 Search", use_container_width=True)

    if search_button and search_query:
        try:
            with st.spinner("🔄 Searching and processing..."):
                # Get organization data
                org_data = asyncio.run(org_searcher.fetch_organization_data(search_query))
                
                if org_data:
                    # Structure the data
                    structured_data = data_processor.structure_organization_data(org_data)
                    
                    if structured_data:
                        # Automatically save to database
                        try:
                            result = db_manager.save_organization_data(structured_data)
                            if result:
                                st.success("✅ Information found and saved successfully!")
                            else:
                                st.error("⚠️ Information found but could not be saved.")
                        except Exception as e:
                            st.error(f"❌ Database error: {str(e)}")
                            logging.error(f"Database save error: {str(e)}")
                        
                        # Display organization info
                        with st.expander("📋 Organization Information", expanded=True):
                            # Display organization details
                            org_info = structured_data.get("organization", {})
                            st.markdown(f"### {org_info.get('name', 'Organization Name')}")
                            st.write(f"**Description:** {org_info.get('description', 'N/A')}")
                            st.write(f"**Ideology:** {org_info.get('ideology', 'N/A')}")
                            st.write(f"**Founded:** {org_info.get('founding_date', 'N/A')}")
                            st.write(f"**Headquarters:** {org_info.get('headquarters', 'N/A')}")
                            if org_info.get('website'):
                                st.write(f"**Website:** {org_info['website']}")
                            
                            # Display leaders if available
                            if structured_data.get("leaders"):
                                st.markdown("### Leadership")
                                for leader in structured_data["leaders"]:
                                    st.markdown(f"""
                                    **{leader.get('name', 'N/A')}** - {leader.get('position', 'N/A')}
                                    - Background: {leader.get('background', 'N/A')}
                                    - Education: {leader.get('education', 'N/A')}
                                    """)
                    else:
                        st.error("❌ Failed to structure the organization data")
                else:
                    st.warning("⚠️ No information found for this organization. Please try a different search term.")
                    
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            logging.error(f"Error in organization search: {str(e)}")

with tab2:
    search_term = st.text_input("Search organizations or members:", 
                               help="Enter name, location, or other keywords",
                               key="search_db")
    
    if st.button("Search", key="search_button"):
        if search_term:
            # Search in database
            org_results = db_manager.search_organizations(search_term)
            member_results = db_manager.search_members(search_term)
            
            if org_results:
                st.subheader("Organizations Found")
                for org in org_results:
                    st.markdown("---")
                    st.write(f"🏢 **{org['name']}**")
                    st.write(f"**Description:** {org['description']}")
                    st.write(f"**Ideology:** {org['ideology']}")
                    st.write(f"**Founded:** {org['founding_date']}")
                    st.write(f"**Headquarters:** {org['headquarters']}")
                    if org.get('website'):
                        st.write(f"**Website:** {org['website']}")
            
            if member_results:
                st.subheader("Members/Leaders Found")
                for member in member_results:
                    st.markdown("---")
                    st.write(f"👤 **{member['name']}** - {member['position']}")
                    st.write(f"**Organization:** {member['organization_name']}")
                    if member.get('background'):
                        st.write(f"**Background:** {member['background']}")
                    if member.get('education'):
                        st.write(f"**Education:** {member['education']}")
                    if member.get('political_history'):
                        st.write(f"**Political History:** {member['political_history']}")
            
            if not org_results and not member_results:
                st.info("No results found for your search term.")

with tab3:
    st.subheader("Browse Organizations")
    
    # Get all organizations
    orgs = db_manager.get_all_organizations()
    
    if orgs:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_org = st.selectbox(
                "Select an organization to view:", 
                [org['name'] for org in orgs],
                key="org_selector"
            )
        
        with col2:
            # Initialize session state for delete confirmation
            if 'delete_confirmation' not in st.session_state:
                st.session_state.delete_confirmation = False
                st.session_state.org_to_delete = None

            if st.button("🗑️ Delete Organization", type="secondary", use_container_width=True):
                st.session_state.delete_confirmation = True
                st.session_state.org_to_delete = selected_org
        # Handle delete confirmation
        if st.session_state.delete_confirmation:
            st.warning(f"⚠️ Are you sure you want to delete {st.session_state.org_to_delete}? This action cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Delete", type="primary", key="confirm_delete"):
                    if db_manager.delete_organization(st.session_state.org_to_delete):
                        st.success(f"Organization '{st.session_state.org_to_delete}' has been deleted!")
                        # Reset session state
                        st.session_state.delete_confirmation = False
                        st.session_state.org_to_delete = None
                        # Rerun to refresh the page
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to delete organization. Please try again.")
            with col2:
                if st.button("❌ Cancel", key="cancel_delete"):
                    st.session_state.delete_confirmation = False
                    st.session_state.org_to_delete = None
                    st.rerun()

        # Display organization information only if not in delete confirmation mode
        if selected_org and not st.session_state.delete_confirmation:
            org = next((org for org in orgs if org['name'] == selected_org), None)
            if org:
                # Organization Overview
                st.markdown(f"""
                <div class="org-box">
                    <h2>{org['name']}</h2>
                    <p><span class="info-label">Description:</span> {org['description']}</p>
                    <p><span class="info-label">Ideology:</span> {org['ideology']}</p>
                    <p><span class="info-label">Founded:</span> {org['founding_date']}</p>
                    <p><span class="info-label">Headquarters:</span> {org['headquarters']}</p>
                    {f'<p><span class="info-label">Website:</span> <a href="{org["website"]}" target="_blank">{org["website"]}</a></p>' if org.get('website') else ''}
                </div>
                """, unsafe_allow_html=True)
                
                # Leadership Section
                st.markdown('<h3 class="section-header">👥 Leadership and Key Members</h3>', unsafe_allow_html=True)
                members = db_manager.get_organization_members(org['name'])
                
                if members:
                    for member in members:
                        st.markdown(f"""
                        <div class="leader-card">
                            <h4>{member['name']}</h4>
                            <p><span class="info-label">Position:</span> {member['position']}</p>
                            {f'<p><span class="info-label">Background:</span> {member["background"]}</p>' if member.get('background') else ''}
                            {f'<p><span class="info-label">Education:</span> {member["education"]}</p>' if member.get('education') else ''}
                            {f'<p><span class="info-label">Political History:</span> {member["political_history"]}</p>' if member.get('political_history') else ''}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No leadership information available for this organization.")
                # News Section
                st.markdown('<h3 class="section-header">📰 Recent News</h3>', unsafe_allow_html=True)
                news = db_manager.get_organization_news(org['name'])
                
                if news:
                    for article in news:
                        st.markdown(f"""
                        <div class="news-card">
                            <h4>{article['title']}</h4>
                            <p>{article['content']}</p>
                            {f'<p><a href="{article["source_url"]}" target="_blank">Read more →</a></p>' if article.get('source_url') else ''}
                            {f'<p class="small-text">Published: {article["publication_date"]}</p>' if article.get('publication_date') else ''}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No recent news available for this organization.")
    else:
        st.info("No organizations found in the database. Use the Research tab to add organizations.")
# Add after initializing db_manager
try:
    # Test database connection without adding/deleting data
    db_manager = DatabaseManager()
    # Just check if we can query the database
    test_query = db_manager.supabase.table('organizations').select("*").limit(1).execute()
    if test_query:
        st.success("✅ Database connected successfully!")
except Exception as e:
    st.error(f"❌ Database setup failed: {str(e)}")
    st.info("Please check your database configuration and refresh the page")
    st.stop() 
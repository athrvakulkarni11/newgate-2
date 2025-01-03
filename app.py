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
from urllib.parse import urlparse
from database_manager import DatabaseManager
from data_processor import DataProcessor

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

# Initialize clients
groq_client = Groq(api_key=GROQ_API_KEY)
web_searcher = WebSearcher()

# Initialize session state for report storage
if 'report' not in st.session_state:
    st.session_state.report = None
if 'sources' not in st.session_state:
    st.session_state.sources = None
if 'query' not in st.session_state:
    st.session_state.query = None

# Initialize database manager
db_manager = DatabaseManager()

# Initialize DataProcessor
data_processor = DataProcessor()

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
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for more focused output
            max_tokens=4000   # Adjust based on your needs
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
                # Store in session state
                st.session_state.report = report
                st.session_state.sources = sources
                st.session_state.articles = result['articles']
            else:
                st.error("Failed to generate report")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"Error in report generation: {str(e)}")

def create_download_content(report, sources, query):
    """Create a well-formatted text report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create a formatted text report with proper spacing and dividers
    content = f"""
{'='*80}
RESEARCH REPORT
{'='*80}

TOPIC: {query}
Generated on: {timestamp}

{'-'*80}
CONTENTS
{'-'*80}

{report}

{'-'*80}
SOURCES
{'-'*80}

The following sources were used in this research:
"""
    # Add sources with proper formatting
    for source in sources.split('\n'):
        if source.strip():
            content += f"{source}\n"
    
    content += f"""
{'-'*80}
METADATA
{'-'*80}
- Generated using AI-powered analysis
- Search performed on: {timestamp}
- Tool: Research Report Generator
- Powered by: Groq LLM and SerpAPI

{'='*80}
"""
    return content.strip()

def format_report_for_display(report):
    """Format report for Streamlit display with proper markdown"""
    return report.replace('```', '').replace('#', '##')

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'Research Report', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('Helvetica', '', 11)
        # Split text into paragraphs
        paragraphs = text.split('\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                # Word wrap for each paragraph
                lines = textwrap.wrap(paragraph, width=85)
                for line in lines:
                    self.cell(0, 5, line, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

def create_pdf_report(report, sources, query):
    """Create a well-formatted PDF report"""
    try:
        pdf = PDF()
        pdf.add_page()
        
        # Add metadata
        pdf.set_title(f"Research Report: {query}")
        pdf.set_author("Research Report Generator")
        
        # Add timestamp and query
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 5, f'Generated on: {timestamp}', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 5, f'Topic: {query}', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)

        # Split the report into sections
        sections = report.split('\n\n')
        current_section = None

        for section in sections:
            if section.strip():
                # Check if this is a section header
                if section.strip().startswith(('Executive Summary', 'Key Findings', 'Detailed Analysis', 'Conclusion')):
                    current_section = section.strip().split('\n')[0]
                    pdf.chapter_title(current_section)
                    # Get the content after the title
                    content = '\n'.join(section.strip().split('\n')[1:])
                    if content.strip():
                        pdf.chapter_body(content)
                else:
                    pdf.chapter_body(section)

        # Add sources section
        pdf.add_page()
        pdf.chapter_title('Sources')
        pdf.set_font('Helvetica', '', 10)
        for source in sources.split('\n'):
            if source.strip():
                pdf.cell(0, 5, source, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        return bytes(pdf.output())
    
    except Exception as e:
        st.error(f"Error in PDF generation: {str(e)}")
        return None

# Streamlit UI
st.set_page_config(page_title="Research Report Generator", layout="wide")

st.title("Research Report Generator")
st.markdown("""
This tool generates comprehensive research reports based on web searches.
Enter a topic or question below to get started.
""")

# Input prompt
user_query = st.text_input("Enter your research topic:", 
                          key="query",
                          help="Be specific with your query for better results")

if st.button("Generate Report", type="primary"):
    generate_report_clicked()

# Display report if available
if st.session_state.report:
    col1, col2 = st.columns([7,3])
    
    with col1:
        st.markdown("## Generated Report")
        st.markdown(st.session_state.report)
        
        # Download buttons container
        download_container = st.container()
        with download_container:
            col_pdf, col_txt = st.columns(2)
            
            with col_pdf:
                pdf_content = create_pdf_report(
                    st.session_state.report, 
                    st.session_state.sources, 
                    st.session_state.query
                )
                if pdf_content:
                    st.download_button(
                        label="📥 Download as PDF",
                        data=pdf_content,
                        file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        help="Download the report as a PDF file"
                    )
            
            with col_txt:
                download_content = create_download_content(
                    st.session_state.report, 
                    st.session_state.sources, 
                    st.session_state.query
                )
                st.download_button(
                    label="📥 Download as TXT",
                    data=download_content,
                    file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    help="Download the report as a text file"
                )
    
    with col2:
        st.markdown("## Sources")
        for article in st.session_state.articles:
            st.markdown(f"- [{article['source']}]({article['url']})")
        
        st.markdown("---")
        st.markdown("### About this Report")
        st.markdown("""
        - Generated using AI analysis
        - Based on multiple web sources
        - Updated as of current search
        - Available in PDF and TXT formats
        """)

# Footer
st.markdown("---")
st.markdown("*Powered by Groq LLM and SerpAPI*")

st.markdown("---")
st.header("Political Organization Research")

org_name = st.text_input("Enter organization name:", 
                        help="Enter the name of a political organization")

async def run_org_search(org_name):
    async with OrganizationSearcher() as org_searcher:
        try:
            raw_data = await org_searcher.fetch_organization_data(org_name)
            if raw_data:
                # Process the raw data through LLM
                structured_data = data_processor.structure_organization_data(raw_data)
                if structured_data:
                    # Clean the data before saving
                    for key in structured_data["organization"]:
                        structured_data["organization"][key] = data_processor.clean_text(
                            structured_data["organization"][key]
                        )
                    
                    for leader in structured_data.get("leaders", []):
                        for key in leader:
                            leader[key] = data_processor.clean_text(leader[key])
                    
                    for news in structured_data.get("news", []):
                        for key in news:
                            news[key] = data_processor.clean_text(news[key])
                    
                    # Save to database
                    db_manager.save_organization_data(structured_data)
                    return structured_data
                else:
                    st.error("Failed to structure the organization data")
            return None
        except Exception as e:
            st.error(f"Error processing organization data: {str(e)}")
            return None

if st.button("Research Organization"):
    with st.spinner("Researching organization..."):
        try:
            result = asyncio.run(run_org_search(org_name))
            
            if result:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Organization Info
                    st.subheader("Organization Information")
                    org_info = result["organization"]
                    st.write(f"**Description:** {org_info['description']}")
                    st.write(f"**Ideology:** {org_info['ideology']}")
                    st.write(f"**Founded:** {org_info['founding_date']}")
                    st.write(f"**Headquarters:** {org_info['headquarters']}")
                    
                    # Leaders
                    if result["leaders"]:
                        st.subheader("Leaders and Key Members")
                        for leader in result["leaders"]:
                            with st.expander(f"📋 {leader['name']} - {leader['position']}"):
                                st.write(f"**Background:** {leader['background']}")
                                st.write(f"**Education:** {leader['education']}")
                                st.write(f"**Political History:** {leader['political_history']}")
                                st.write(f"**Achievements:** {leader['achievements']}")
                                st.write(f"**Source:** {leader['source_url']}")
                    
                    # News
                    if result["news"]:
                        st.subheader("Recent News")
                        for news in result["news"]:
                            with st.expander(f"📰 {news['title']}"):
                                st.write(news['content'])
                                st.write(f"Published: {news['publication_date']}")
                                st.write(f"Source: {news['source_url']}")
            else:
                st.warning("No information found for this organization. Please try a different search term.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"Error in organization search: {str(e)}") 
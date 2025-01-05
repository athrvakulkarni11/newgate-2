```markdown
# Political Research Assistant

A Streamlit-based web application for conducting political research and organization analysis using AI and web data.

Application Currently Available at :[link](https://newgate.streamlit.app/)

IF want to Execute LO

## Setup & Installation

### Prerequisites
- Python 3.8+ (3.12 recommended)
- Supabase account
- Required API keys:
  - Groq API key
  - SerpAPI key
  - NewsAPI key 

### Installation Steps

1. Clone the repository and install dependencies:
```bash
git clone https://github.com/athrvakulkarni11/newgate-2.git
cd newgate-2
pip install -r requirements.txt
```

2. Create `.streamlit/secrets.toml` with your API credentials(In our case already provided for ease of use but recommended for new database you'll have to do below setup):
```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
GROQ_API_KEY = "your-groq-key"
SERPAPI_KEY = "your-serpapi-key"
NEWSAPI_KEY = "your-newsapi-key"
USER_AGENT = "Mozilla/5.0..."
```

3. Configure Streamlit theme (optional) in `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#262730"
textColor = "#FAFAFA"

[server]
maxUploadSize = 200
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

4. Set up Supabase database tables(these steps are already done for new database execute below in sql editor):
```sql
-- Run these SQL commands in your Supabase SQL editor
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    ideology VARCHAR(255),
    founding_date VARCHAR(255),
    headquarters VARCHAR(255),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leaders (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    position VARCHAR(255),
    organization VARCHAR(255) REFERENCES organizations(name),
    background TEXT,
    education TEXT,
    political_history TEXT,
    achievements TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Running the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

## Project Structure
```
political-research-assistant/
├── app.py                    # Main Streamlit application
├── data_processor.py         # Data processing logic
├── database_manager.py       # Supabase database operations
├── organization_searcher.py  # Organization research functionality
├── websearcher.py           # Web scraping utilities
├── requirements.txt         # Python dependencies
├── .streamlit/
│   ├── config.toml        # Streamlit configuration
│   └── secrets.toml       # API keys and credentials
└── supabase/
    └── migrations/        # Database migrations
```

## Key Dependencies
```
streamlit>=1.24.0
supabase>=1.0.3
groq>=0.3.0
beautifulsoup4
google-search-results
langchain
python-dotenv
```

## Features

- Organization research and profiling
- Leadership analysis
- News tracking and aggregation
- AI-powered report generation
- PDF export functionality
- Database storage and management
- Custom styling and theming

## Development Notes

- The application uses Groq for AI processing
- Web scraping is handled through SerpAPI and BeautifulSoup4
- Data is stored in Supabase PostgreSQL database
- Streamlit is used for the web interface
- Async operations for improved performance


import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging
from groq import Groq
import os
from datetime import datetime
import re

class OrganizationSearcher:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.logger = logging.getLogger(__name__)

    async def fetch_organization_data(self, org_name: str) -> Dict:
        """Fetch organization data including leaders and news"""
        try:
            self.logger.info(f"Searching for: {org_name}")
            
            # More specific prompt to get structured data
            org_prompt = f"""Research the organization "{org_name}" and provide information in this exact format:

            ORGANIZATION PROFILE
            Name: [Organization name]
            Description: [2-3 sentence description]
            Ideology: [Political/ideological stance]
            Founded: [Year founded]
            Headquarters: [City, Country]
            Website: [URL]

            LEADERSHIP
            [For each leader use exactly this format:]
            Leader: [Full Name]
            Position: [Current role]
            Background: [Brief background]

            RECENT NEWS
            [For each news item use exactly this format:]
            Title: [News headline]
            Date: [Publication date]
            Summary: [Brief summary]
            Source: [Source URL if available]

            Please provide actual information, not the placeholder text in brackets.
            """

            response = self.groq_client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {"role": "system", "content": "You are a research analyst providing factual information about organizations."},
                    {"role": "user", "content": org_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            self.logger.info("Received response from LLM")

            # Parse organization profile
            org_section = self._extract_section(content, "ORGANIZATION PROFILE", "LEADERSHIP")
            org_info = self._parse_organization_section(org_section)

            # Parse leadership
            leadership_section = self._extract_section(content, "LEADERSHIP", "RECENT NEWS")
            leaders = self._parse_leadership_section(leadership_section)

            # Parse news
            news_section = self._extract_section(content, "RECENT NEWS", None)
            news = self._parse_news_section(news_section)

            result = {
                "organization": org_info,
                "leaders": leaders,
                "news": news
            }

            self.logger.info(f"Parsed data - Org: {bool(org_info)}, Leaders: {len(leaders)}, News: {len(news)}")
            return result

        except Exception as e:
            self.logger.error(f"Error in fetch_organization_data: {str(e)}")
            return None

    async def _gather_web_data(self, org_name: str) -> str:
        """Gather data from multiple sources with better error handling"""
        try:
            async with aiohttp.ClientSession() as session:
                results = []
                
                # First try direct company search
                company_data = await self._search_company_info(session, org_name)
                if company_data:
                    results.extend(company_data)
                    
                # If no results, try broader search
                if not results:
                    self.logger.info(f"No direct company results for {org_name}, trying broader search...")
                    broader_data = await self._search_broader_info(session, org_name)
                    results.extend(broader_data)

                # Always try to get news
                news_data = await self._search_news(session, org_name)
                if news_data:
                    results.extend(news_data)

                # Add debug logging
                self.logger.info(f"Number of results gathered: {len(results)}")

                if not results:
                    self.logger.warning(f"No results found for {org_name} from any source")
                    return ""

                return "\n\n".join(results)

        except Exception as e:
            self.logger.error(f"Error in _gather_web_data: {str(e)}")
            return ""

    async def _search_company_info(self, session: aiohttp.ClientSession, org_name: str) -> List[str]:
        """Search specifically for company information"""
        results = []
        try:
            # Basic company search
            params = {
                "api_key": self.serpapi_key,
                "q": f'"{org_name}" company OR business OR organization',
                "num": 10,
                "gl": "us",
                "hl": "en"
            }
            
            async with session.get("https://serpapi.com/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "organic_results" in data:
                        for result in data["organic_results"]:
                            snippet = result.get("snippet", "")
                            title = result.get("title", "")
                            link = result.get("link", "")
                            
                            # Less strict matching to ensure we get results
                            if any(term.lower() in title.lower() or term.lower() in snippet.lower() 
                                  for term in org_name.lower().split()):
                                results.append(f"""
COMPANY INFORMATION:
Title: {title}
Description: {snippet}
Source: {link}
""")
                                
            # Try LinkedIn search as well
            linkedin_params = {
                "api_key": self.serpapi_key,
                "q": f'site:linkedin.com/company {org_name}',
                "num": 3
            }
            
            async with session.get("https://serpapi.com/search", params=linkedin_params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "organic_results" in data:
                        for result in data["organic_results"]:
                            results.append(f"""
LINKEDIN PROFILE:
{result.get('title', '')}
{result.get('snippet', '')}
URL: {result.get('link', '')}
""")
                                
        except Exception as e:
            self.logger.error(f"Error in company search: {str(e)}")
        
        return results

    async def _search_broader_info(self, session: aiohttp.ClientSession, org_name: str) -> List[str]:
        """Perform a broader search for information"""
        results = []
        try:
            search_queries = [
                f'{org_name} about',
                f'{org_name} overview',
                f'{org_name} description'
            ]
            
            for query in search_queries:
                params = {
                    "api_key": self.serpapi_key,
                    "q": query,
                    "num": 5
                }
                
                async with session.get("https://serpapi.com/search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "organic_results" in data:
                            for result in data["organic_results"]:
                                snippet = result.get("snippet", "")
                                if snippet:
                                    results.append(f"""
GENERAL INFORMATION:
Source: {result.get('title', '')}
Content: {snippet}
URL: {result.get('link', '')}
""")
                                
            await asyncio.sleep(0.2)  # Small delay between requests
            
        except Exception as e:
            self.logger.error(f"Error in broader search: {str(e)}")
        
        return results

    async def _search_news(self, session: aiohttp.ClientSession, org_name: str) -> List[str]:
        """Search for news articles"""
        results = []
        try:
            params = {
                "api_key": self.serpapi_key,
                "q": org_name,
                "tbm": "nws",
                "num": 5,
                "tbs": "qdr:m"  # Last month
            }
            
            async with session.get("https://serpapi.com/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "news_results" in data:
                        for item in data["news_results"]:
                            results.append(f"""
NEWS:
Title: {item['title']}
Summary: {item['snippet']}
Date: {item.get('date', 'N/A')}
Source: {item['source']}
URL: {item['link']}
""")
                                
        except Exception as e:
            self.logger.error(f"Error in news search: {str(e)}")
        
        return results

    def _structure_analysis(self, analysis: str, raw_data: str) -> Dict:
        """Structure the analysis into the required format"""
        try:
            # Extract organization info
            org_info = {
                'name': self._extract_field(analysis, 'Full Name:'),
                'type': self._extract_field(analysis, 'Type:'),
                'description': self._extract_field(analysis, 'Description:'),
                'ideology': self._extract_field(analysis, 'Ideology:'),
                'founding_date': self._extract_field(analysis, 'Founding Date:'),
                'headquarters': self._extract_field(analysis, 'Headquarters:'),
                'website': self._extract_field(analysis, 'Website:')
            }

            # Add debug logging
            self.logger.info(f"Extracted organization info: {bool(org_info['name'])}")

            # Ensure required fields are present
            if not org_info['name'] or not org_info['description']:
                self.logger.warning("Missing required organization fields")
                return {}

            return org_info

        except Exception as e:
            self.logger.error(f"Error in _structure_analysis: {e}")
            return {}

    def _extract_field(self, text: str, field: str) -> str:
        """Extract a field value from text"""
        pattern = f"{field}(.*?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_section(self, text: str, start_marker: str, end_marker: str = None) -> str:
        """Extract a section from text between markers"""
        try:
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return ""
            
            start_idx += len(start_marker)
            
            if end_marker:
                end_idx = text.find(end_marker, start_idx)
                if end_idx == -1:
                    return text[start_idx:].strip()
                return text[start_idx:end_idx].strip()
            return text[start_idx:].strip()
        except Exception as e:
            self.logger.error(f"Error extracting section: {str(e)}")
            return ""

    def _parse_organization_section(self, section: str) -> Dict:
        """Parse organization profile section"""
        org_info = {}
        for line in section.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if value and not value.startswith('['):  # Skip template placeholders
                    org_info[key] = value
        return org_info

    def _parse_leadership_section(self, section: str) -> List[Dict]:
        """Parse leadership section"""
        leaders = []
        current_leader = {}
        
        for line in section.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('Leader:'):
                if current_leader:
                    leaders.append(current_leader)
                current_leader = {'name': line.replace('Leader:', '').strip()}
            elif line.startswith('Position:'):
                current_leader['position'] = line.replace('Position:', '').strip()
            elif line.startswith('Background:'):
                current_leader['background'] = line.replace('Background:', '').strip()
        
        if current_leader:  # Add the last leader
            leaders.append(current_leader)
        
        return leaders

    def _parse_news_section(self, section: str) -> List[Dict]:
        """Parse news section"""
        news_items = []
        current_news = {}
        
        for line in section.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('Title:'):
                if current_news:
                    news_items.append(current_news)
                current_news = {'title': line.replace('Title:', '').strip()}
            elif line.startswith('Date:'):
                current_news['publication_date'] = line.replace('Date:', '').strip()
            elif line.startswith('Summary:'):
                current_news['content'] = line.replace('Summary:', '').strip()
            elif line.startswith('Source:'):
                current_news['source_url'] = line.replace('Source:', '').strip()
        
        if current_news:  # Add the last news item
            news_items.append(current_news)
        
        return news_items 
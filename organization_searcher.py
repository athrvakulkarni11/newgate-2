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

    async def fetch_organization_data(self, org_name: str) -> Optional[Dict]:
        """Fetch organization data from multiple sources"""
        try:
            self.logger.info(f"Searching for: {org_name}")
            
            # Gather data from web sources
            web_data = await self._gather_web_data(org_name)
            
            if not web_data:
                self.logger.warning("No data found from web sources")
                return None

            # Analyze gathered data
            analysis_prompt = f"""Analyze this information about {org_name}:

{web_data}

Provide a structured analysis in the following format:

ORGANIZATION PROFILE
-------------------
Full Name: [Organization name]
Type: [Organization type]
Description: [Brief description]
Ideology: [If applicable]
Founding Date: [When established]
Headquarters: [Location]
Website: [Official website]

LEADERSHIP STRUCTURE
-------------------
[Current leaders and their roles]

RECENT DEVELOPMENTS
------------------
[Recent news and developments]

Focus on providing factual, verifiable information."""

            # Get analysis from LLM
            response = self.groq_client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {"role": "system", "content": "You are a research analyst. Provide factual information based on the given data."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3
            )

            return self._structure_analysis(response.choices[0].message.content, web_data)

        except Exception as e:
            self.logger.error(f"Error in fetch_organization_data: {e}")
            return None

    async def _gather_web_data(self, org_name: str) -> str:
        """Gather data from multiple web sources"""
        try:
            async with aiohttp.ClientSession() as session:
                results = []
                
                # Search using SerpAPI
                params = {
                    "api_key": self.serpapi_key,
                    "q": f"{org_name}",
                    "num": 10
                }
                
                async with session.get("https://serpapi.com/search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "organic_results" in data:
                            for result in data["organic_results"][:5]:
                                snippet = result.get("snippet", "")
                                title = result.get("title", "")
                                results.append(f"Title: {title}\nContent: {snippet}")
                
                # Get news results
                news_params = {
                    "api_key": self.serpapi_key,
                    "q": f"{org_name} news",
                    "tbm": "nws",
                    "num": 5
                }
                
                async with session.get("https://serpapi.com/search", params=news_params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "news_results" in data:
                            for item in data["news_results"]:
                                results.append(f"News: {item['title']}\nSummary: {item['snippet']}")

                return "\n\n".join(results) if results else ""

        except Exception as e:
            self.logger.error(f"Error gathering web data: {e}")
            return ""

    def _structure_analysis(self, analysis: str, raw_data: str) -> Optional[Dict]:
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

            # Extract leadership info
            leadership_section = self._extract_section(analysis, 'LEADERSHIP STRUCTURE', 'RECENT DEVELOPMENTS')
            leaders = self._parse_leaders(leadership_section)

            # Extract news
            news_section = self._extract_section(analysis, 'RECENT DEVELOPMENTS', None)
            news = self._parse_news(news_section, raw_data)

            return {
                'organization': org_info,
                'leaders': leaders,
                'news': news
            }

        except Exception as e:
            self.logger.error(f"Error in _structure_analysis: {e}")
            return None

    def _extract_field(self, text: str, field: str) -> str:
        """Extract a field value from text"""
        pattern = f"{field}(.*?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        """Extract a section from text"""
        start_idx = text.find(start_marker)
        if start_idx == -1:
            return ""
        
        if end_marker:
            end_idx = text.find(end_marker, start_idx)
            if end_idx == -1:
                return text[start_idx:].strip()
            return text[start_idx:end_idx].strip()
        return text[start_idx:].strip()

    def _parse_leaders(self, leadership_text: str) -> List[Dict]:
        """Parse leadership information"""
        leaders = []
        # Split by newlines and process each line
        lines = leadership_text.split('\n')
        current_leader = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if ':' in line:
                name, role = line.split(':', 1)
                current_leader = {
                    'name': name.strip(),
                    'position': role.strip(),
                    'background': '',
                    'education': '',
                    'political_history': ''
                }
                leaders.append(current_leader)
            elif current_leader:
                # Add additional info to current leader
                current_leader['background'] = line

        return leaders

    def _parse_news(self, news_text: str, raw_data: str) -> List[Dict]:
        """Parse news information"""
        news_items = []
        lines = news_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('---'):
                news_items.append({
                    'title': line,
                    'content': self._find_news_content(line, raw_data),
                    'source_url': '',
                    'publication_date': ''
                })

        return news_items[:5]  # Return up to 5 news items

    def _find_news_content(self, title: str, raw_data: str) -> str:
        """Find news content in raw data"""
        for line in raw_data.split('\n'):
            if title.lower() in line.lower():
                return line
        return "" 
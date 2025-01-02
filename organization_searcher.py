from aiohttp import ClientSession, ClientTimeout
import asyncio
import logging
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
import os

class OrganizationSearcher:
    def __init__(self):
        self.session = None
        self.timeout = ClientTimeout(total=30)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        if not self.session:
            self.session = ClientSession(
                headers=self.headers,
                timeout=self.timeout
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    def get_search_urls(self, query: str, num_results: int = 5):
        """Get URLs from Google Search using SerpAPI"""
        try:
            params = {
                "api_key": os.getenv("SERPAPI_KEY"),
                "engine": "google",
                "q": query,
                "num": num_results,
                "hl": "en",
                "gl": "us"
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            urls = []
            if "organic_results" in results:
                for result in results["organic_results"]:
                    if "link" in result and "snippet" in result:
                        urls.append({
                            'link': result["link"],
                            'snippet': result["snippet"],
                            'title': result.get("title", "")
                        })
            
            return urls[:num_results]
            
        except Exception as e:
            self.logger.error(f"Error in get_search_urls: {str(e)}")
            return []

    async def fetch_organization_data(self, org_name):
        if not org_name or len(org_name.strip()) < 2:
            return None

        try:
            results = {
                "organization": {},
                "leaders": [],
                "news": []
            }

            # Get organization info
            org_results = self.get_search_urls(f"{org_name} organization information")
            if org_results:
                results["organization"] = {
                    "name": org_name,
                    "description": org_results[0].get('snippet', ''),
                    "sources": [result['link'] for result in org_results[:3]]
                }

            # Get leadership info
            leader_results = self.get_search_urls(f"{org_name} leadership team executives")
            if leader_results:
                results["leaders"] = [
                    {
                        "title": result['title'],
                        "description": result['snippet'],
                        "source": result['link']
                    }
                    for result in leader_results[:3]
                ]

            # Get recent news
            news_results = self.get_search_urls(f"{org_name} recent news")
            if news_results:
                results["news"] = [
                    {
                        "title": result['title'],
                        "summary": result['snippet'],
                        "source": result['link']
                    }
                    for result in news_results[:5]
                ]

            return results

        except Exception as e:
            self.logger.error(f"Error in fetch_organization_data: {str(e)}")
            return None 
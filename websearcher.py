from langchain_community.document_loaders import AsyncHtmlLoader, WebBaseLoader
from langchain_community.document_transformers import Html2TextTransformer
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
import requests
import logging
import os
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urlparse

class WebSearcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.html2text = Html2TextTransformer()

    async def search_company_info(self, query: str) -> Optional[Dict]:
        try:
            # Step 1: Get search URLs
            urls = self.get_search_urls(query)
            if not urls:
                self.logger.error(f"No URLs found for query: {query}")
                return None

            # Step 2: Load HTML content asynchronously
            loader = AsyncHtmlLoader(urls)
            docs = await loader.aload()
            
            if not docs:
                self.logger.error(f"No documents loaded for query: {query}")
                return None

            # Step 3: Transform HTML to text
            processed_docs = []
            for doc in docs:
                if doc and hasattr(doc, 'page_content'):
                    # Transform one document at a time
                    transformed = self.html2text.transform_documents([doc])
                    if transformed:
                        processed_docs.extend(transformed)

            # Step 4: Process and structure the results
            result = {
                'content': '',
                'articles': []
            }

            for i, doc in enumerate(processed_docs):
                if doc and hasattr(doc, 'page_content'):
                    text_content = doc.page_content.strip()
                    if text_content:
                        article = {
                            'url': urls[i],
                            'text': text_content[:2000],  # Limit text length
                            'source': urlparse(urls[i]).netloc
                        }
                        result['articles'].append(article)

            if result['articles']:
                # Combine all article texts for content
                result['content'] = ' '.join([article['text'] for article in result['articles']])
                return result

            self.logger.error(f"No valid content found for query: {query}")
            return None

        except Exception as e:
            self.logger.error(f"Error in search_company_info: {str(e)}")
            return None

    def get_search_urls(self, query: str, num_results: int = 5) -> List[str]:
        """Get URLs from Google Search using SerpAPI"""
        try:
            params = {
                "api_key": os.getenv("SERPAPI_KEY"),
                "engine": "google",
                "q": query,
                "num": num_results,
                "hl": "en",  # Language
                "gl": "us"   # Country
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            urls = []
            if "organic_results" in results:
                for result in results["organic_results"]:
                    if "link" in result:
                        urls.append(result["link"])
            
            if not urls:
                self.logger.warning(f"No search results found for query: {query}")
                
            return urls[:num_results]
            
        except Exception as e:
            self.logger.error(f"Error in get_search_urls: {str(e)}")
            return []

    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and parse content from a single URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
                element.decompose()
            
            # Get text content
            text = soup.get_text(separator='\n', strip=True)
            
            # Basic text cleaning
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            return text[:5000]  # Limit length
            
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def clean_text(self, text: str) -> str:
        """Clean and format extracted text"""
        if not text:
            return ""
            
        # Remove extra whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = ' '.join(lines)
        
        # Remove very short lines (likely noise)
        text = ' '.join([line for line in text.split('.') if len(line.strip()) > 30])
        
        return text.strip()
from langchain_community.document_transformers import Html2TextTransformer
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
import requests
import logging
import os
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urlparse

class WebSearcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.html2text = Html2TextTransformer()

    async def search_company_info(self, query: str) -> Optional[Dict]:
        try:
            # Step 1: Get search URLs
            urls = self.get_search_urls(query)
            if not urls:
                self.logger.error(f"No URLs found for query: {query}")
                return None

            # Step 2: Load HTML content asynchronously
            loader = AsyncHtmlLoader(urls)
            docs = await loader.aload()
            
            if not docs:
                self.logger.error(f"No documents loaded for query: {query}")
                return None

            # Step 3: Transform HTML to text
            processed_docs = []
            for doc in docs:
                if doc and hasattr(doc, 'page_content'):
                    # Transform one document at a time
                    transformed = self.html2text.transform_documents([doc])
                    if transformed:
                        processed_docs.extend(transformed)

            # Step 4: Process and structure the results
            result = {
                'content': '',
                'articles': []
            }

            for i, doc in enumerate(processed_docs):
                if doc and hasattr(doc, 'page_content'):
                    text_content = doc.page_content.strip()
                    if text_content:
                        article = {
                            'url': urls[i],
                            'text': text_content[:2000],  # Limit text length
                            'source': urlparse(urls[i]).netloc
                        }
                        result['articles'].append(article)

            if result['articles']:
                # Combine all article texts for content
                result['content'] = ' '.join([article['text'] for article in result['articles']])
                return result

            self.logger.error(f"No valid content found for query: {query}")
            return None

        except Exception as e:
            self.logger.error(f"Error in search_company_info: {str(e)}")
            return None

    def get_search_urls(self, query: str, num_results: int = 5) -> List[str]:
        """Get URLs from Google Search using SerpAPI"""
        try:
            params = {
                "api_key": os.getenv("SERPAPI_KEY"),
                "engine": "google",
                "q": query,
                "num": num_results,
                "hl": "en",  # Language
                "gl": "us"   # Country
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            urls = []
            if "organic_results" in results:
                for result in results["organic_results"]:
                    if "link" in result:
                        urls.append(result["link"])
            
            if not urls:
                self.logger.warning(f"No search results found for query: {query}")
                
            return urls[:num_results]
            
        except Exception as e:
            self.logger.error(f"Error in get_search_urls: {str(e)}")
            return []

    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and parse content from a single URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
                element.decompose()
            
            # Get text content
            text = soup.get_text(separator='\n', strip=True)
            
            # Basic text cleaning
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            return text[:5000]  # Limit length
            
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def clean_text(self, text: str) -> str:
        """Clean and format extracted text"""
        if not text:
            return ""
            
        # Remove extra whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = ' '.join(lines)
        
        # Remove very short lines (likely noise)
        text = ' '.join([line for line in text.split('.') if len(line.strip()) > 30])
        
        return text.strip()
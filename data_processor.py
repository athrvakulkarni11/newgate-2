from groq import Groq
import os
from typing import Dict, Optional
import json
import logging
import re

class DataProcessor:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.logger = logging.getLogger(__name__)

    def structure_organization_data(self, data):
        """Structure raw organization data including news articles"""
        org_data = {
            "name": data["organization"].get("name"),
            "description": data["organization"].get("description"),
            "ideology": data["organization"].get("ideology"),
            "founding_date": data["organization"].get("founding_date"),
            "headquarters": data["organization"].get("headquarters"),
            "website": data["organization"].get("website")
        }
        
        # Structure leaders data
        leaders = []
        if "leaders" in data:
            for leader in data["leaders"]:
                leader_data = {
                    "name": leader.get("name"),
                    "position": leader.get("position"),
                    "background": leader.get("background"),
                    "education": leader.get("education"),
                    "political_history": leader.get("political_history"),
                    "organization_name": org_data["name"]
                }
                leaders.append(leader_data)
        
        # Structure news data
        news_articles = []
        if "news" in data:
            for article in data["news"]:
                article_data = {
                    "title": article.get("title"),
                    "content": article.get("content"),
                    "source_url": article.get("source_url"),
                    "publication_date": article.get("publication_date"),
                    "organization": org_data["name"]
                }
                news_articles.append(article_data)

        return {
            "organization": org_data,
            "leaders": leaders,
            "news": news_articles
        }

    def clean_text(self, text: str) -> str:
        """Clean and format text data"""
        if not text:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Remove extra whitespace and newlines
        text = ' '.join(text.split())
        
        # Remove special characters but keep basic punctuation
        text = ''.join(char for char in text if char.isprintable())
        
        # Limit length while keeping whole words
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text.strip() 
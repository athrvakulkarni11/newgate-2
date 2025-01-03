from groq import Groq
import os
from typing import Dict, Optional
import json
import logging

class DataProcessor:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.logger = logging.getLogger(__name__)

    def structure_organization_data(self, raw_data: Dict) -> Optional[Dict]:
        prompt = """
        Analyze the following raw data about a political organization and structure it into a clean format.
        Raw data: {raw_data}

        Return ONLY a valid JSON object with this exact structure:
        {{
            "organization": {{
                "name": "string",
                "description": "string",
                "ideology": "string",
                "founding_date": "string",
                "headquarters": "string",
                "website": "string"
            }},
            "leaders": [
                {{
                    "name": "string",
                    "position": "string",
                    "background": "string",
                    "education": "string",
                    "political_history": "string",
                    "achievements": "string",
                    "source_url": "string"
                }}
            ],
            "news": [
                {{
                    "title": "string",
                    "content": "string",
                    "source_url": "string",
                    "publication_date": "string"
                }}
            ]
        }}
        """

        try:
            response = self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{
                    "role": "user",
                    "content": prompt.format(raw_data=raw_data)
                }],
                temperature=0.1,
                max_tokens=4000
            )
            
            # Get the response content
            content = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                structured_data = json.loads(content)
                return structured_data
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing error: {str(e)}")
                # Try to extract JSON from the response if it contains other text
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        structured_data = json.loads(json_match.group())
                        return structured_data
                    except json.JSONDecodeError:
                        self.logger.error("Failed to parse extracted JSON")
                        return None
                return None
                
        except Exception as e:
            self.logger.error(f"Error in structuring data: {str(e)}")
            return None

    def clean_text(self, text: str) -> str:
        """Clean and format text data"""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = ' '.join(text.split())
        
        # Remove special characters but keep basic punctuation
        text = ''.join(char for char in text if char.isprintable())
        
        # Limit length while keeping whole words
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text.strip() 
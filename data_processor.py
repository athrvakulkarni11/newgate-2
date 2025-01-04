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

    def structure_organization_data(self, raw_data: Dict) -> Optional[Dict]:
        """Structure raw organization data into a clean format"""
        try:
            # Format the raw data into a string for the prompt
            raw_data_str = json.dumps(raw_data, indent=2)
            
            prompt = f"""You are a data structuring assistant for political organizations. Analyze this raw data and structure it precisely.

Raw data:
{raw_data_str}

Instructions:
1. Extract key information about the organization
2. Identify leadership details
3. Include recent news coverage
4. Ensure accuracy and completeness
5. Return ONLY a valid JSON object

Required JSON structure:
{{
    "organization": {{
        "name": "full official name",
        "description": "comprehensive description",
        "ideology": "clear political ideology/orientation",
        "founding_date": "verified founding date",
        "headquarters": "main headquarters location",
        "website": "official website URL"
    }},
    "leaders": [
        {{
            "name": "full name",
            "position": "current role/title",
            "background": "professional background",
            "education": "educational background",
            "political_history": "political career highlights"
        }}
    ],
    "news": [
        {{
            "title": "article headline",
            "content": "article summary",
            "source_url": "source URL",
            "publication_date": "publication date"
        }}
    ]
}}

Return ONLY the JSON structure, no additional text."""

            # Get response from LLM with stricter parameters
            response = self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": "You are a precise data structuring assistant that only returns valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Lower temperature for more consistent output
                max_tokens=4000,
                top_p=0.1,  # More focused sampling
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            # Extract the response text
            result = response.choices[0].message.content.strip()
            
            # Log the raw response for debugging
            self.logger.debug(f"Raw LLM response: {result[:200]}...")

            # Clean up the response
            # Remove any markdown code blocks
            result = re.sub(r'```json\s*', '', result)
            result = re.sub(r'```\s*', '', result)
            
            # Try to find JSON object in the response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                result = json_match.group()
            
            # Log the cleaned JSON
            self.logger.debug(f"Cleaned JSON string: {result[:200]}...")

            try:
                # Parse the JSON
                structured_data = json.loads(result)
                
                # Validate the structure
                required_keys = {"organization", "leaders", "news"}
                if not all(key in structured_data for key in required_keys):
                    self.logger.error(f"Missing required keys. Found keys: {structured_data.keys()}")
                    return None
                
                # Validate organization fields
                org_required_fields = {"name", "description", "ideology", "founding_date", "headquarters", "website"}
                if not all(field in structured_data["organization"] for field in org_required_fields):
                    self.logger.error(f"Missing organization fields. Found: {structured_data['organization'].keys()}")
                    return None
                
                return structured_data
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing error: {str(e)}")
                self.logger.error(f"Problematic JSON string: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in structuring data: {str(e)}")
            self.logger.error(f"Raw data: {raw_data_str[:200]}...")
            return None

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
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List
import logging

class DatabaseManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get database credentials from environment variables
        self.db_params = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432')
        }
        
        # Initialize connection and cursor as None
        self.conn = None
        self.cursor = None
        
        # Establish connection
        self.connect()

    def connect(self):
        """Establish database connection and create cursor"""
        try:
            self.conn = psycopg2.connect(**self.db_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            self.create_tables()  # Ensure tables exist
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Create organizations table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    ideology VARCHAR(255),
                    founding_date VARCHAR(255),
                    headquarters VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create leaders table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS leaders (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    position VARCHAR(255),
                    organization VARCHAR(255),
                    background TEXT,
                    education TEXT,
                    political_history TEXT,
                    achievements TEXT,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.conn.commit()
        except Exception as e:
            print(f"Error creating tables: {e}")
            self.conn.rollback()
            raise

    def save_organization_data(self, data: Dict):
        """Save organization data including leaders and news"""
        try:
            # Save organization
            self.cursor.execute("""
                INSERT INTO organizations 
                (name, description, ideology, founding_date, headquarters, website)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                self.clean_text(data['organization']['name']),
                self.clean_text(data['organization'].get('description', '')),
                self.clean_text(data['organization'].get('ideology', '')),
                self.clean_text(data['organization'].get('founding_date', '')),
                self.clean_text(data['organization'].get('headquarters', '')),
                self.clean_text(data['organization'].get('website', ''))
            ))
            
            org_id = self.cursor.fetchone()['id']
            
            # Save leaders
            for leader in data.get('leaders', []):
                self.cursor.execute("""
                    INSERT INTO leaders 
                    (organization_id, name, position, background, education, political_history)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    org_id,
                    self.clean_text(leader.get('name', '')),
                    self.clean_text(leader.get('position', '')),
                    self.clean_text(leader.get('background', '')),
                    self.clean_text(leader.get('education', '')),
                    self.clean_text(leader.get('political_history', ''))
                ))
            
            # Save news
            for news in data.get('news', []):
                self.cursor.execute("""
                    INSERT INTO news 
                    (organization_id, title, content, source_url, publication_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    org_id,
                    self.clean_text(news.get('title', '')),
                    self.clean_text(news.get('content', '')),
                    self.clean_text(news.get('source_url', '')),
                    self.clean_text(news.get('publication_date', ''))
                ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving organization data: {e}")
            self.conn.rollback()
            return False

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

    def search_organizations(self, search_term):
        """Search organizations by name, description, or location"""
        try:
            query = """
                SELECT * FROM organizations 
                WHERE name ILIKE %s 
                OR description ILIKE %s 
                OR headquarters ILIKE %s
            """
            search_pattern = f"%{search_term}%"
            self.cursor.execute(query, (search_pattern, search_pattern, search_pattern))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error searching organizations: {e}")
            return []

    def search_members(self, search_term):
        """Search members/leaders by name, position, or background"""
        try:
            query = """
                SELECT l.*, o.name as organization_name 
                FROM leaders l
                JOIN organizations o ON l.organization_id = o.id
                WHERE l.name ILIKE %s 
                OR l.position ILIKE %s 
                OR l.background ILIKE %s
            """
            search_pattern = f"%{search_term}%"
            self.cursor.execute(query, (search_pattern, search_pattern, search_pattern))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error searching members: {e}")
            return []

    def get_all_organizations(self):
        """Retrieve all organizations from database"""
        try:
            query = "SELECT * FROM organizations ORDER BY name"
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving organizations: {e}")
            return []

    def get_organization_members(self, org_name: str) -> List[Dict]:
        """Retrieve all members/leaders for a specific organization"""
        try:
            query = """
                SELECT l.name, l.position, l.background, l.education, l.political_history
                FROM leaders l
                JOIN organizations o ON l.organization_id = o.id
                WHERE o.name = %s
                ORDER BY l.name
            """
            self.cursor.execute(query, (org_name,))
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error retrieving members: {e}")
            self.conn.rollback()
            return []

    def get_organization_news(self, org_name: str) -> List[Dict]:
        """Retrieve news articles for a specific organization"""
        try:
            query = """
                SELECT n.title, n.content, n.source_url, n.publication_date
                FROM news n
                JOIN organizations o ON n.organization_id = o.id
                WHERE o.name = %s
                ORDER BY n.publication_date DESC
            """
            self.cursor.execute(query, (org_name,))
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error retrieving news: {e}")
            self.conn.rollback()
            return []

    def __del__(self):
        """Cleanup database connections"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close() 
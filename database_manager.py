import sqlite3
from datetime import datetime
from typing import Dict, List

class DatabaseManager:
    def __init__(self, db_name='organizations.db'):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Drop existing tables
            cursor.execute("DROP TABLE IF EXISTS leader_details")
            cursor.execute("DROP TABLE IF EXISTS news")
            cursor.execute("DROP TABLE IF EXISTS leaders")
            cursor.execute("DROP TABLE IF EXISTS organizations")
            
            # Political Organizations table
            cursor.execute('''
                CREATE TABLE organizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    ideology TEXT,
                    founding_date TEXT,
                    headquarters TEXT,
                    website TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Leaders table
            cursor.execute('''
                CREATE TABLE leaders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_id INTEGER,
                    name TEXT NOT NULL,
                    position TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (organization_id) REFERENCES organizations (id)
                )
            ''')
            
            # Leader Details table
            cursor.execute('''
                CREATE TABLE leader_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    leader_id INTEGER,
                    background TEXT,
                    education TEXT,
                    political_history TEXT,
                    achievements TEXT,
                    source_url TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (leader_id) REFERENCES leaders (id)
                )
            ''')
            
            # News/Posts table
            cursor.execute('''
                CREATE TABLE news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_id INTEGER,
                    title TEXT,
                    content TEXT,
                    source_url TEXT,
                    publication_date TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (organization_id) REFERENCES organizations (id)
                )
            ''')
            
            conn.commit()

    def save_organization_data(self, data: Dict):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now()
            
            # Save organization
            cursor.execute('''
                INSERT OR REPLACE INTO organizations 
                (name, description, ideology, founding_date, headquarters, website)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['organization']['name'],
                data['organization'].get('description', ''),
                data['organization'].get('ideology', ''),
                data['organization'].get('founding_date', ''),
                data['organization'].get('headquarters', ''),
                data['organization'].get('website', '')
            ))
            
            org_id = cursor.lastrowid
            
            # Save leaders and their details
            for leader in data.get('leaders', []):
                cursor.execute('''
                    INSERT INTO leaders (organization_id, name, position)
                    VALUES (?, ?, ?)
                ''', (
                    org_id,
                    leader.get('name', ''),
                    leader.get('position', '')
                ))
            
            # Save news
            for news in data.get('news', []):
                cursor.execute('''
                    INSERT INTO news 
                    (organization_id, title, content, source_url, publication_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    org_id,
                    news.get('title', ''),
                    news.get('content', ''),
                    news.get('source_url', ''),
                    news.get('publication_date', '')
                ))
            
            conn.commit()

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
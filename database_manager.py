from supabase import create_client
import streamlit as st
import logging
from typing import List, Dict, Optional
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        try:
            self.supabase = create_client(
                "https://vitoohbkhesyhwjkejyj.supabase.co",
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpdG9vaGJraGVzeWh3amtlanlqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYwMDYxNzIsImV4cCI6MjA1MTU4MjE3Mn0.v8_Y9AlTBYJhxDfvHiyF2EoZAsdHUXWLQqfSDC0Tjvk"
            )
            self.logger = logging.getLogger(__name__)
            self._check_tables()
            self._initialize_database()
        except Exception as e:
            st.error(f"Failed to initialize database: {str(e)}")
            raise e

    def _initialize_database(self):
        """Initialize database tables if they don't exist"""
        try:
            # Check if tables exist by attempting to select from them
            try:
                self.supabase.table('organizations').select("*").limit(1).execute()
                self.supabase.table('leaders').select("*").limit(1).execute()
                self.logger.info("Database tables already exist")
                return
            except Exception:
                # Tables don't exist, create them using rpc
                sql = """
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
                """
                # Use rpc to execute raw SQL
                self.supabase.rpc('exec_sql', {'query': sql}).execute()
                self.logger.info("Database tables created successfully")
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise e

    def save_organization_data(self, data: Dict) -> bool:
        """Save organization data including leaders and news"""
        try:
            self.logger.info("Starting to save organization data")
            
            # Extract data
            org_data = data.get("organization", {})
            leaders_data = data.get("leaders", [])
            news_data = data.get("news", [])

            # Validate organization data
            if not org_data:
                self.logger.error("No organization data to save")
                return False

            # Ensure required fields exist
            org_name = org_data.get("name", "").strip()
            if not org_name:
                self.logger.error("Organization name is required")
                return False

            # Prepare organization data
            org_record = {
                "name": org_name,
                "description": org_data.get("description", ""),
                "ideology": org_data.get("ideology", ""),
                "founding_date": org_data.get("founded", ""),
                "headquarters": org_data.get("headquarters", ""),
                "website": org_data.get("website", "")
            }

            # Save organization
            try:
                # Check if organization exists
                existing = self.supabase.table('organizations').select("*").eq('name', org_name).execute()
                
                if not existing.data:
                    self.logger.info(f"Creating new organization: {org_name}")
                    self.supabase.table('organizations').insert(org_record).execute()
                else:
                    self.logger.info(f"Updating existing organization: {org_name}")
                    self.supabase.table('organizations').update(org_record).eq('name', org_name).execute()
            except Exception as e:
                self.logger.error(f"Error saving organization: {str(e)}")
                raise

            # Save leaders
            if leaders_data:
                try:
                    # Delete existing leaders
                    self.supabase.table('leaders').delete().eq('organization', org_name).execute()
                    
                    # Prepare and insert new leaders
                    for leader in leaders_data:
                        leader_record = {
                            "name": leader.get("name", ""),
                            "position": leader.get("position", ""),
                            "background": leader.get("background", ""),
                            "organization": org_name
                        }
                        self.supabase.table('leaders').insert(leader_record).execute()
                    self.logger.info(f"Saved {len(leaders_data)} leaders")
                except Exception as e:
                    self.logger.error(f"Error saving leaders: {str(e)}")
                    # Continue execution even if leaders fail

            # Save news
            if news_data:
                try:
                    # Delete existing news
                    self.supabase.table('news_articles').delete().eq('organization', org_name).execute()
                    
                    # Prepare and insert new news
                    for article in news_data:
                        news_record = {
                            "title": article.get("title", ""),
                            "content": article.get("content", ""),
                            "source_url": article.get("source_url", ""),
                            "publication_date": article.get("publication_date", datetime.now().isoformat()),
                            "organization": org_name
                        }
                        self.supabase.table('news_articles').insert(news_record).execute()
                    self.logger.info(f"Saved {len(news_data)} news articles")
                except Exception as e:
                    self.logger.error(f"Error saving news: {str(e)}")
                    # Continue execution even if news fails

            self.logger.info("Successfully saved all organization data")
            return True

        except Exception as e:
            self.logger.error(f"Error in save_organization_data: {str(e)}")
            return False

    def get_organization_data(self, org_name: str) -> Dict:
        """Get complete organization data including leaders and news"""
        try:
            # Get organization
            org = self.supabase.table('organizations').select("*").eq('name', org_name).execute()
            
            if not org.data:
                return {}

            # Get leaders
            leaders = self.supabase.table('leaders').select("*").eq('organization', org_name).execute()
            
            # Get news
            news = self.supabase.table('news_articles').select("*").eq('organization', org_name).execute()

            return {
                "organization": org.data[0] if org.data else {},
                "leaders": leaders.data if leaders.data else [],
                "news": news.data if news.data else []
            }

        except Exception as e:
            self.logger.error(f"Error retrieving organization data: {str(e)}")
            return {}

    def get_all_organizations(self) -> List[Dict]:
        """Fetch all organizations from the database"""
        try:
            response = self.supabase.table('organizations').select("*").execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching organizations: {e}")
            return []

    def get_organization_by_name(self, name: str) -> Optional[Dict]:
        """Fetch organization by name"""
        try:
            response = self.supabase.table('organizations').select("*").eq('name', name).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error fetching organization by name: {e}")
            return None

    def add_organization(self, org_data: Dict) -> Optional[Dict]:
        """Add a new organization to the database"""
        try:
            response = self.supabase.table('organizations').insert(org_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error adding organization: {e}")
            return None

    def add_leader(self, leader_data: Dict) -> Optional[Dict]:
        """Add a new leader to the database"""
        try:
            response = self.supabase.table('leaders').insert(leader_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error adding leader: {e}")
            return None

    def get_leaders_by_organization(self, organization_name: str) -> List[Dict]:
        """Fetch all leaders for a specific organization"""
        try:
            response = self.supabase.table('leaders').select("*").eq('organization', organization_name).execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching leaders for organization: {e}")
            return []

    def update_organization(self, name: str, update_data: Dict) -> Optional[Dict]:
        """Update an existing organization"""
        try:
            response = self.supabase.table('organizations').update(update_data).eq('name', name).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error updating organization: {e}")
            return None

    def delete_organization(self, name: str) -> bool:
        """Delete an organization and its associated leaders"""
        try:
            response = self.supabase.table('organizations').delete().eq('name', name).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Error deleting organization: {e}")
            return False 

    def search_organizations(self, search_term: str) -> List[Dict]:
        """Search organizations by name, description, or ideology"""
        try:
            query = f"%{search_term}%"
            response = self.supabase.table('organizations').select("*").or_(
                f"name.ilike.{query},description.ilike.{query},ideology.ilike.{query}"
            ).execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error searching organizations: {e}")
            return []

    def search_members(self, search_term: str) -> List[Dict]:
        """Search leaders/members by name or position"""
        try:
            query = f"%{search_term}%"
            response = self.supabase.table('leaders').select("*").or_(
                f"name.ilike.{query},position.ilike.{query}"
            ).execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error searching members: {e}")
            return []

    def get_organization_members(self, organization_name: str) -> List[Dict]:
        """Get all members/leaders for a specific organization"""
        try:
            response = self.supabase.table('leaders').select("*").eq(
                'organization', organization_name
            ).execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching organization members: {e}")
            return []

    def get_organization_news(self, org_name):
        """Get news articles for an organization"""
        try:
            response = self.supabase.table('news_articles') \
                .select("*") \
                .eq('organization', org_name) \
                .order('publication_date', desc=True) \
                .execute()
            
            logging.info(f"Retrieved {len(response.data)} news articles for {org_name}")
            return response.data
        except Exception as e:
            logging.error(f"Error fetching organization news: {str(e)}")
            return []

    def _check_tables(self):
        """Debug method to check table structure"""
        try:
            # Check organizations table
            org_response = self.supabase.table('organizations').select("*").limit(1).execute()
            st.write("Organizations table exists")
            
            # Check leaders table
            leader_response = self.supabase.table('leaders').select("*").limit(1).execute()
            st.write("Leaders table exists")
            
            return True
        except Exception as e:
            st.error(f"Table check failed: {str(e)}")
            return False 
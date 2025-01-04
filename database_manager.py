from supabase import create_client
import streamlit as st
import logging
from typing import List, Dict, Optional
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        try:
            self.supabase = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_KEY"]
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

    def save_organization_data(self, org_data: Dict) -> Optional[Dict]:
        """Save organization data and its leaders to the database"""
        try:
            # Log the incoming data structure
            self.logger.info("Received data structure for saving")
            
            # Extract organization data
            org_info = {
                "name": org_data.get("organization", {}).get("name", "").strip(),
                "description": org_data.get("organization", {}).get("description", "").strip(),
                "ideology": org_data.get("organization", {}).get("ideology", "").strip(),
                "founding_date": org_data.get("organization", {}).get("founding_date", "").strip(),
                "headquarters": org_data.get("organization", {}).get("headquarters", "").strip(),
                "website": org_data.get("organization", {}).get("website", "").strip()
            }

            # Validate required fields
            if not org_info["name"]:
                self.logger.error("Organization name is missing")
                return None

            try:
                # Check if organization exists
                existing_org = self.get_organization_by_name(org_info["name"])
                
                if existing_org:
                    self.logger.info(f"Updating existing organization: {org_info['name']}")
                    response = self.supabase.table('organizations').update(org_info).eq('name', org_info["name"]).execute()
                else:
                    self.logger.info(f"Creating new organization: {org_info['name']}")
                    response = self.supabase.table('organizations').insert(org_info).execute()

                if not response.data:
                    self.logger.error("No data returned from database operation")
                    return None

                # Process leaders
                if "leaders" in org_data and isinstance(org_data["leaders"], list):
                    # Remove existing leaders
                    self.supabase.table('leaders').delete().eq('organization', org_info["name"]).execute()
                    
                    # Add new leaders
                    for leader in org_data["leaders"]:
                        leader_data = {
                            "name": leader.get("name", "").strip(),
                            "position": leader.get("position", "").strip(),
                            "organization": org_info["name"],
                            "background": leader.get("background", "").strip(),
                            "education": leader.get("education", "").strip(),
                            "political_history": leader.get("political_history", "").strip(),
                            "achievements": leader.get("achievements", "").strip(),
                            "source_url": leader.get("source_url", "").strip()
                        }
                        
                        if leader_data["name"]:  # Only save if name exists
                            try:
                                self.supabase.table('leaders').insert(leader_data).execute()
                            except Exception as e:
                                self.logger.error(f"Error saving leader {leader_data['name']}: {str(e)}")

                self.logger.info(f"Successfully saved organization: {org_info['name']}")
                return response.data[0]

            except Exception as e:
                self.logger.error(f"Database operation failed: {str(e)}")
                return None

        except Exception as e:
            self.logger.error(f"Error in save_organization_data: {str(e)}")
            return None

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

    def get_organization_news(self, organization_name: str) -> List[Dict]:
        """Get news for a specific organization"""
        # Since we don't have a news table, return empty list
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
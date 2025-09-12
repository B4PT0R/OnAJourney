from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from tinydb import TinyDB, Query
import os

class DatabaseInterface(ABC):
    """Abstract interface for user data storage"""
    
    @abstractmethod
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by username"""
        pass
    
    @abstractmethod
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user and return the created user"""
        pass
    
    @abstractmethod
    def update_user(self, user_data: Dict[str, Any]) -> None:
        """Update existing user"""
        pass

class TinyDBDatabase(DatabaseInterface):
    """TinyDB implementation"""
    
    def __init__(self, db_path: str = "on_a_journey_db.json"):
        self.db = TinyDB(db_path)
        self.users_table = self.db.table("users")
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        return self.users_table.get(Query().username == username)
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        self.users_table.insert(user_data)
        return user_data
    
    def update_user(self, user_data: Dict[str, Any]) -> None:
        self.users_table.update(user_data, Query().username == user_data["username"])

class MongoDatabase(DatabaseInterface):
    """MongoDB implementation"""
    
    def __init__(self, connection_string: str, database_name: str = "on_a_journey"):
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pymongo is required for MongoDB support. Install with: pip install pymongo")
        
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        self.users_collection = self.db.users
        
        # Test connection and create index
        try:
            # Test the connection
            self.client.admin.command('ping')
            
            # Create index on username for performance (idempotent operation)
            self.users_collection.create_index("username", unique=True)
            print("✅ MongoDB connected successfully")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            raise
    
    def _normalize_for_mongo(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert integer keys to strings for MongoDB compatibility"""
        if not isinstance(data, dict):
            return data
        
        normalized = {}
        for key, value in data.items():
            # Convert integer keys to strings
            str_key = str(key)
            
            # Recursively normalize nested dictionaries
            if isinstance(value, dict):
                normalized[str_key] = self._normalize_for_mongo(value)
            elif isinstance(value, list):
                normalized[str_key] = [
                    self._normalize_for_mongo(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                normalized[str_key] = value
        
        return normalized
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized_data = self._normalize_for_mongo(user_data)
        self.users_collection.insert_one(normalized_data)
        return user_data  # Return original structure
    
    def update_user(self, user_data: Dict[str, Any]) -> None:
        username = user_data["username"]
        normalized_data = self._normalize_for_mongo(user_data)
        # Remove _id if present
        normalized_data.pop('_id', None)
        
        self.users_collection.replace_one(
            {"username": username}, 
            normalized_data,
            upsert=False
        )

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        user = self.users_collection.find_one({"username": username})
        if user:
            # Remove MongoDB's _id field
            user.pop('_id', None)
        return user

# Factory function to create database instance
def create_database(local=False) -> DatabaseInterface:
    """Create database instance based on environment or config"""
    import streamlit as st
    # Check for MongoDB connection string in environment
    mongo_uri = st.secrets.get('MONGODB_URI') or os.getenv('MONGODB_URI')
    if mongo_uri and not local:
        return MongoDatabase(mongo_uri)
    
    # Default to TinyDB
    return TinyDBDatabase()

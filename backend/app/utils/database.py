from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
from flask import current_app  # noqa: F401 (imported for potential future use)
import certifi
import os

logger = logging.getLogger(__name__)

class Database:
    """MongoDB database connection manager"""
    
    def __init__(self):
        self.client = None
        self.db = None
    
    def connect(self, app):
        """Connect to MongoDB"""
        try:
            # Get MongoDB URI from config
            mongo_uri = app.config.get('MONGODB_URI')
            db_name = app.config.get('MONGODB_DB', 'streamlineer')
            
            if not mongo_uri:
                raise ValueError("MONGODB_URI not configured")
            
            # Optional insecure TLS for development/troubleshooting (DO NOT USE IN PROD)
            allow_insecure_tls = os.environ.get('ALLOW_INSECURE_TLS', '').lower() == 'true'

            # Create MongoDB client with improved connection settings for Atlas
            self.client = MongoClient(
                mongo_uri,
                maxPoolSize=50,  # Maximum number of connections in the pool
                minPoolSize=5,   # Minimum number of connections in the pool
                maxIdleTimeMS=30000,  # Close connections after 30 seconds of inactivity
                serverSelectionTimeoutMS=10000,  # 10 second timeout for server selection
                connectTimeoutMS=60000,  # 20 second timeout for connection
                socketTimeoutMS=60000,  # 10 second timeout for socket operations
                retryWrites=True,  # Retry write operations
                retryReads=True,   # Retry read operations
                # SSL/TLS configuration for Atlas
                tls=True,
                tlsAllowInvalidCertificates=allow_insecure_tls,
                tlsAllowInvalidHostnames=allow_insecure_tls,
                tlsCAFile=certifi.where(),
                # Heartbeat settings
                heartbeatFrequencyMS=10000,
            )
            
            # Test the connection with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.client.admin.command('ping')
                    logger.info("Successfully connected to MongoDB")
                    print("✅ MongoDB connected")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"MongoDB connection attempt {attempt + 1} failed, retrying...")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            # Get database
            self.db = self.client[db_name]
            
            # Create indexes for better performance
            self._create_indexes()
            
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            print("❌ MongoDB connection failed – check URI / network")
            print("💡 If you're behind a corporate proxy/SSL interception, try setting ALLOW_INSECURE_TLS=true for local dev only.")
            print("💡 Ensure your current IP is whitelisted in MongoDB Atlas Network Access.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            print(f"❌ MongoDB error: {e}")
            return False
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Users collection indexes
            users_collection = self.db.users
            
            # Create unique index on email
            users_collection.create_index("email", unique=True)
            
            # Create index on organization for faster queries
            users_collection.create_index("organization")
            
            # Create index on role for role-based queries
            users_collection.create_index("role")
            
            # Create index on created_at for time-based queries
            users_collection.create_index("created_at")

            # Tasks collection indexes
            tasks_collection = self.db.tasks
            tasks_collection.create_index("assigned_to_id")
            tasks_collection.create_index("assigned_by_id")
            tasks_collection.create_index("status")
            tasks_collection.create_index("is_completed")
            tasks_collection.create_index("inspection_id")
            tasks_collection.create_index("created_at")

            # Inspection responses indexes
            responses_coll = self.db.inspection_responses
            responses_coll.create_index("manager_id")
            responses_coll.create_index("inspector_id")
            responses_coll.create_index("template_id")

            # Templates collection indexes
            templates_collection = self.db.templates
            templates_collection.create_index("creator_id")
            templates_collection.create_index("manager_id")
            templates_collection.create_index("status")
            templates_collection.create_index("updated_at")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def get_collection(self, collection_name):
        """Get a collection from the database"""
        # A `pymongo.database.Database` instance does *not* support truth-value
        # testing (i.e. `bool(self.db)` raises the error the user saw).  We
        # therefore check explicitly for *None* instead.
        if self.db is None:
            raise Exception("Database not connected")
        return self.db[collection_name]
    
    def close(self):
        """Close the database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Global database instance
db = Database()

def init_db(app):
    """Initialize database connection"""
    return db.connect(app)

def get_db():
    """Get database instance"""
    return db 
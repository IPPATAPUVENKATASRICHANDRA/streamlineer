import os
from datetime import timedelta
# Robust .env loading: handle different encodings (utf-8, utf-8-sig, utf-16)
from dotenv import load_dotenv, find_dotenv

# Attempt to load a .env file even if it was saved with a BOM or UTF-16
def _safe_load_dotenv():
    """Load a .env file trying multiple encodings so that a file saved with
    Windows Notepad (often UTF-16-LE with BOM) does not crash the app.
    """

    dotenv_path = find_dotenv(usecwd=True)
    if not dotenv_path:
        return

    for enc in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            load_dotenv(dotenv_path, encoding=enc, override=False)
            return  # success
        except UnicodeDecodeError:
            # try next encoding
            continue

    # If we get here all attempts failed → let the caller know.
    raise UnicodeDecodeError("Unable to decode .env file – please save it in UTF-8.")


# Safely load environment variables on import
try:
    _safe_load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    print("Using default configuration values")


class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # MongoDB Configuration
    MONGODB_URI = os.environ.get('MONGODB_URI')
    MONGODB_DB = 'streamlineer'
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 604800)))
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Security Configuration
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    ACCOUNT_LOCKOUT_DURATION = int(os.environ.get('ACCOUNT_LOCKOUT_DURATION', 900))  # 15 minutes
    
    # Rate Limiting
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '200 per day')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    MONGODB_DB = 'streamlineer_test'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 
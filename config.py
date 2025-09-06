"""
Configuration file for EvideciaFlow
Contains all environment variables and settings
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('APP_SECRET_KEY', 'research_platform_prototype_key_2024')
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
    PORT = int(os.environ.get('PORT', 5000))
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///databases/')
    
    # AI Configuration
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads/temp/')
    FIGURES_FOLDER = os.environ.get('FIGURES_FOLDER', 'uploads/figures/')
    
    # CORS Configuration
    ALLOWED_ORIGINS = os.environ.get(
        'ALLOWED_ORIGINS',
        'http://localhost:3000,http://localhost:9002'
    ).split(',')
    
    # Rate Limiting
    RATE_LIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    
    # Session Configuration
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', 24))
    SESSION_TIMEOUT = timedelta(hours=SESSION_TIMEOUT_HOURS)  # Added for direct comparison
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif', 'tiff', 'svg'}
    
    # MIME types for file validation
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'image/png',
        'image/jpeg',
        'image/gif',
        'image/tiff',
        'image/svg+xml'
    }

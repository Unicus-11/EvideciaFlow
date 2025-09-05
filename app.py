# app.py - Main Flask application
"""
EvideciaFlow Research Platform - Flask server
Improved version with better configuration, security, and code organization.
Provides endpoints for:
  - Dashboard and feature pages
  - Citation analysis
  - Explain / Rewrite
 - Generic AI processing
  - Paper Analyzer (upload, run tool, status, download)
"""

import os
import sys
import uuid
import traceback
import logging
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from flask import Flask, request, jsonify, render_template, session, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Optional imports with fallbacks
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available - MIME type validation disabled")

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    print("Warning: flask-limiter not available - rate limiting disabled")

# Add project root to path so backend imports resolve when running from project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# -------------------------
# Configuration
# -------------------------
class Config:
    """Centralized configuration management"""
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads/temp/'
    FIGURES_FOLDER = 'uploads/figures/'
    SECRET_KEY = os.environ.get('APP_SECRET_KEY', 'research_platform_prototype_key_2024')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif', 'tiff', 'svg'}
    SESSION_TIMEOUT = timedelta(hours=24)
    RATE_LIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    
    # File validation settings
    MAX_TEXT_SIZE = 1024 * 1024  # 1MB for text content
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

# -------------------------
# Imports with graceful fallbacks
# -------------------------
def safe_import(module_name, class_name=None, fallback=None):
    """Safely import modules with logging"""
    try:
        module = __import__(module_name, fromlist=[class_name] if class_name else [])
        if class_name:
            return getattr(module, class_name)
        return module
    except ImportError as e:
        print(f"Warning: {module_name}.{class_name or ''} not found - {str(e)}")
        return fallback

# Import optional components
CitationContextAnalyzer = safe_import('backend.citation_context', 'CitationContextAnalyzer')
AIManager = safe_import('ai.ai_manager', 'AIManager')
FileProcessor = safe_import('backend.utils.file_processor', 'FileProcessor')
PaperAnalyzer = safe_import('backend.paper_analyzer', 'PaperAnalyzer')

# Database helper with fallback
try:
    from backend.utils.database_helper import DatabaseHelper
except ImportError:
    print("Warning: DatabaseHelper not found, using dummy class")
    class DatabaseHelper:
        def create_anonymous_session(self, user_id):
            pass
        def get_all_journals(self):
            return []
        def get_user_activity(self, user_id):
            return []
        def update_session_activity(self, session_id):
            pass
        def get_journal_requirements(self, journal_name):
            return {
                'name': journal_name, 
                'citation_style': 'APA', 
                'special_requirements': [], 
                'word_limits': {}, 
                'formatting_rules': {}, 
                'language_variant': 'American English'
            }
        def log_activity(self, session_id, feature, event, payload):
            pass
        def save_citation_analysis(self, session_id, analyzed_text, citation_results, metadata):
            pass

# -------------------------
# Flask app setup
# -------------------------
app = Flask(__name__, template_folder='frontend', static_folder='frontend')
app.config.from_object(Config)
CORS(app)

# Rate limiting
# Rate limiting (optional)
if LIMITER_AVAILABLE:
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["1000 per hour", "100 per minute"],
        storage_uri=Config.RATE_LIMIT_STORAGE_URL
    )
else:
    # Create a dummy limiter that does nothing
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -------------------------
# Initialize components
# -------------------------
def initialize_components():
    """Initialize all application components with error handling"""
    components = {}
    
    # Database helper
    components['db_helper'] = DatabaseHelper()
    
    # File processor
    if FileProcessor:
        try:
            components['file_processor'] = FileProcessor()
            logger.info("✓ File Processor initialized successfully")
        except Exception as e:
            components['file_processor'] = None
            logger.warning(f"✗ FileProcessor init failed: {str(e)}")
    else:
        components['file_processor'] = None
    
    # AI manager
    if AIManager:
        try:
            components['ai_manager'] = AIManager()
            logger.info("✓ AI Manager initialized successfully")
        except Exception as e:
            components['ai_manager'] = None
            logger.warning(f"✗ AIManager init failed: {str(e)}")
    else:
        components['ai_manager'] = None
    
    # Citation analyzer
    if CitationContextAnalyzer:
        try:
            components['citation_analyzer'] = CitationContextAnalyzer()
            logger.info("✓ Citation Analyzer initialized successfully")
        except Exception as e:
            components['citation_analyzer'] = None
            logger.warning(f"✗ CitationContextAnalyzer init failed: {str(e)}")
    else:
        components['citation_analyzer'] = None
    
    # Paper analyzer
    if PaperAnalyzer:
        try:
            components['paper_analyzer'] = PaperAnalyzer(ai_manager=components['ai_manager'])
            logger.info("✓ Paper Analyzer initialized successfully")
        except Exception as e:
            components['paper_analyzer'] = None
            logger.warning(f"✗ Paper Analyzer init failed: {str(e)}")
    else:
        components['paper_analyzer'] = None
    
    return components

# Initialize all components
app_components = initialize_components()

# -------------------------
# Utility functions
# -------------------------
def error_response(message: str, details: str = None, status: int = 400):
    """Standardized error response format"""
    response = {
        'success': False,
        'error': message,
        'timestamp': datetime.now().isoformat()
    }
    if details:
        response['details'] = details
    return jsonify(response), status

def success_response(data: dict = None, message: str = None):
    """Standardized success response format"""
    response = {
        'success': True,
        'timestamp': datetime.now().isoformat()
    }
    if message:
        response['message'] = message
    if data:
        response.update(data)
    return jsonify(response)

def validate_file_security(file):
    """Enhanced file validation with optional MIME type checking"""
    if not file or not file.filename:
        return False, "No file provided"
    
    # Secure filename
    filename = secure_filename(file.filename)
    if not filename:
        return False, "Invalid filename"
    
    # Extension check
    if not allowed_file(filename):
        return False, f"Invalid file type. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"
    
    # MIME type validation (if python-magic is available)
    if MAGIC_AVAILABLE:
        try:
            file_content = file.read()
            file.seek(0)  # Reset file pointer
            
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type not in Config.ALLOWED_MIME_TYPES:
                return False, f"File type not allowed: {mime_type}"
        except Exception as e:
            logger.warning(f"MIME type check failed: {str(e)}")
            # Continue without MIME check if magic fails
    else:
        logger.debug("MIME type validation skipped - python-magic not available")
    
    return True, "File validation passed"

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def get_user_session() -> str:
    """Get or create anonymous user session with timeout handling"""
    current_time = datetime.now()
    
    # Check if session exists and is valid
    if 'user_id' in session and 'created_at' in session:
        try:
            created_at = datetime.fromisoformat(session['created_at'])
            if current_time - created_at < Config.SESSION_TIMEOUT:
                return session['user_id']
        except (ValueError, TypeError):
            pass
    
    # Create new session
    session['user_id'] = str(uuid.uuid4())
    session['created_at'] = current_time.isoformat()
    session['last_activity'] = current_time.isoformat()
    
    try:
        app_components['db_helper'].create_anonymous_session(session['user_id'])
    except Exception as e:
        logger.warning(f"Failed to create database session: {str(e)}")
    
    return session['user_id']

def require_component(component_name):
    """Decorator to ensure required component is available"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not app_components.get(component_name):
                return error_response(
                    f"{component_name.replace('_', ' ').title()} not available",
                    f"The {component_name} service is currently unavailable",
                    503
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json_request(required_fields=None):
    """Decorator to validate JSON request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json(force=True)
                if not data:
                    return error_response("Invalid JSON data", "Request body must contain valid JSON")
                
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        return error_response(
                            "Missing required fields",
                            f"Required fields: {', '.join(missing_fields)}"
                        )
                
                return f(data, *args, **kwargs)
            except Exception as e:
                return error_response("Invalid request format", str(e))
        return decorated_function
    return decorator

# -------------------------
# Routes - UI pages
# -------------------------
@app.route('/')
def dashboard():
    """Main dashboard showing all features"""
    user_id = get_user_session()
    return render_template('home.html', user_id=user_id)

@app.route('/citation-context')
def citation_context_page():
    """Citation Context feature page"""
    return render_template('citation_context.html')

@app.route('/explain-rewrite')
def explain_rewrite_page():
    """Explain/Rewrite feature page"""
    return render_template('explain_rewrite.html')

@app.route('/paper-analyzer')
def paper_analyzer_page():
    """Render the paper analyzer page"""
    return render_template('paper_analyzer.html')

# -------------------------
# Routes - Citation analysis
# -------------------------
@app.route('/analyze_citations', methods=['POST'])
@limiter.limit("20 per minute")
@require_component('citation_analyzer')
def analyze_citations():
    """Citation Context analysis endpoint"""
    try:
        user_id = get_user_session()
        
        # Validate request has required data
        if not request.files.get('paper_file') and not request.form.get('paper_text'):
            return error_response(
                'No paper content provided',
                'Please upload a file or paste text.'
            )

        # Handle file upload
        if 'paper_file' in request.files and request.files['paper_file'].filename:
            file = request.files['paper_file']
            
            # Enhanced file validation
            is_valid, validation_message = validate_file_security(file)
            if not is_valid:
                return error_response('File validation failed', validation_message)

            if not app_components['file_processor']:
                return error_response('File processing not available', status=503)

            # Process file with secure handling
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            try:
                file.save(filepath)
                extraction_success, text_content, extraction_metadata = \
                    app_components['file_processor'].extract_text_from_file(filepath)
            finally:
                # Always clean up temp file
                try:
                    os.remove(filepath)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {filepath}: {str(e)}")

            if not extraction_success:
                return error_response('Text extraction failed', text_content)

            if not text_content.strip():
                return error_response(
                    'Empty file content',
                    'The uploaded file appears to be empty or contains no readable text.'
                )

            content_type = 'file'
            paper_content = text_content

        else:
            paper_content = request.form.get('paper_text', '').strip()
            if not paper_content:
                return error_response('Missing paper text', 'Please provide paper text for analysis.')
            
            if len(paper_content) > Config.MAX_TEXT_SIZE:
                return error_response(
                    'Text too long',
                    f'Maximum text size is {Config.MAX_TEXT_SIZE} characters.'
                )
            
            content_type = 'text'

        target_journal = request.form.get('target_journal', 'nature')
        analysis_type = request.form.get('analysis_type', 'comprehensive')
        custom_requirements = request.form.get('custom_requirements', '')

        # Run citation analysis
        result = app_components['citation_analyzer'].process_citation_analysis(
            session_id=user_id,
            paper_content=paper_content,
            target_journal=target_journal,
            analysis_type=analysis_type,
            custom_requirements=custom_requirements if custom_requirements else None,
            content_type=content_type
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Citation analysis error: {str(e)}\n{traceback.format_exc()}")
        return error_response('Analysis failed', str(e), 500)

# -------------------------
# Routes - Generic AI processing
# -------------------------
@app.route('/api/ai-process', methods=['POST'])
@limiter.limit("30 per minute")
@require_component('ai_manager')
@validate_json_request(['feature'])
def api_ai_process(data):
    """Generic AI processing endpoint"""
    try:
        user_id = get_user_session()
        feature = data.get('feature')
        request_data = data.get('data', {})

        result = app_components['ai_manager'].process_request(feature, request_data, user_id)
        return jsonify(result)

    except Exception as e:
        logger.error(f"AI processing error: {str(e)}\n{traceback.format_exc()}")
        return error_response('AI processing failed', str(e), 500)

# -------------------------
# Routes - Explain/Rewrite
# -------------------------
@app.route('/api/explain-rewrite', methods=['POST'])
@limiter.limit("15 per minute")
@require_component('ai_manager')
def api_explain_rewrite():
    """API endpoint for paper rewriting using AI manager"""
    try:
        user_id = get_user_session()
        paper_content = None

        # Handle file upload
        if 'paper_file' in request.files and request.files['paper_file'].filename:
            file = request.files['paper_file']
            
            is_valid, validation_message = validate_file_security(file)
            if not is_valid:
                return error_response('File validation failed', validation_message)

            if not app_components['file_processor']:
                return error_response('File processing not available', status=503)

            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            try:
                file.save(filepath)
                success, text_content, _ = app_components['file_processor'].extract_text_from_file(filepath)
            finally:
                try:
                    os.remove(filepath)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file: {str(e)}")

            if not success:
                return error_response('Text extraction failed', text_content)

            paper_content = text_content

        elif request.form.get('paper_text'):
            paper_content = request.form.get('paper_text')
            if len(paper_content) > Config.MAX_TEXT_SIZE:
                return error_response(
                    'Text too long',
                    f'Maximum text size is {Config.MAX_TEXT_SIZE} characters.'
                )
        else:
            return error_response('No content provided', 'Please upload a file or provide text.')

        data = {
            'text': paper_content,
            'target_journal': request.form.get('target_journal', 'Nature'),
            'language': 'American English'
        }

        result = app_components['ai_manager'].process_request('explain_rewrite', data, user_id)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Explain/Rewrite error: {str(e)}\n{traceback.format_exc()}")
        return error_response('Processing failed', str(e), 500)

# -------------------------
# Routes - Paper Analyzer
# -------------------------
@app.route('/api/analyze-paper', methods=['POST'])
@limiter.limit("10 per minute")
@require_component('paper_analyzer')
def api_analyze_paper():
    """API endpoint for initial paper analysis"""
    try:
        if 'paper_file' not in request.files:
            return error_response('No file uploaded', 'Please select a PDF file to analyze')

        paper_file = request.files['paper_file']

        if paper_file.filename == '':
            return error_response('No file selected', 'Please choose a file to upload')

        is_valid, validation_message = validate_file_security(paper_file)
        if not is_valid:
            return error_response('File validation failed', validation_message)

        user_id = get_user_session()
        result = app_components['paper_analyzer'].analyze_paper(paper_file, user_id)

        return jsonify(result), (200 if result.get('success') else 500)

    except Exception as e:
        logger.error(f"Paper analysis error: {str(e)}\n{traceback.format_exc()}")
        return error_response('Analysis failed', str(e), 500)

@app.route('/api/download-result/<analysis_id>/<tool_name>', methods=['GET'])
@require_component('paper_analyzer')
def api_download_result(analysis_id, tool_name):
    """API endpoint for downloading tool results"""
    try:
        # Input validation
        if not analysis_id or not tool_name:
            return error_response('Missing parameters', 'Analysis ID and tool name are required')
        
        # Sanitize inputs
        analysis_id = secure_filename(analysis_id)
        tool_name = secure_filename(tool_name)

        analysis_data = app_components['paper_analyzer']._get_analysis_data(analysis_id)
        if not analysis_data:
            return error_response('Analysis not found', status=404)

        return success_response({
            'download_url': f'/downloads/{analysis_id}_{tool_name}_result.pdf',
            'filename': f'{tool_name}_analysis_result.pdf',
        }, 'Download link generated successfully')

    except Exception as e:
        logger.error(f"Download error: {str(e)}\n{traceback.format_exc()}")
        return error_response('Download failed', str(e), 500)

@app.route('/api/analysis-status/<analysis_id>', methods=['GET'])
@require_component('paper_analyzer')
def api_analysis_status(analysis_id):
    """Get the status of a paper analysis"""
    try:
        analysis_id = secure_filename(analysis_id)
        analysis_data = app_components['paper_analyzer']._get_analysis_data(analysis_id)
        
        if not analysis_data:
            return error_response('Analysis not found', status=404)

        return success_response({
            'analysis_id': analysis_id,
            'status': analysis_data.get('status', 'unknown'),
            'filename': analysis_data.get('filename', 'unknown'),
            'created_at': analysis_data.get('created_at'),
            'word_count': analysis_data.get('word_count', 0),
            'available_tools': list(app_components['paper_analyzer'].available_tools.keys()) 
                             if hasattr(app_components['paper_analyzer'], 'available_tools') else []
        })

    except Exception as e:
        logger.error(f"Status check error: {str(e)}\n{traceback.format_exc()}")
        return error_response('Status check failed', str(e), 500)

@app.route('/api/run-tool/<tool_name>', methods=['POST'])
@limiter.limit("20 per minute")
@require_component('paper_analyzer')
@validate_json_request(['analysis_id'])
def api_run_tool(data, tool_name):
    """API endpoint for running specific analysis tools"""
    try:
        # Validate tool name
        valid_tools = ['polish', 'figure', 'citation', 'claim', 'protocol']
        if tool_name not in valid_tools:
            return error_response(
                'Invalid tool',
                f'Tool "{tool_name}" is not available. Valid tools: {", ".join(valid_tools)}'
            )

        analysis_id = data.get('analysis_id')
        tool_config = data.get('tool_config', {})

        result = app_components['paper_analyzer'].run_analysis_tool(
            analysis_id, tool_name, tool_config
        )
        return jsonify(result), (200 if result.get('success') else 500)

    except Exception as e:
        logger.error(f"Tool execution error for {tool_name}: {str(e)}\n{traceback.format_exc()}")
        return error_response('Tool execution failed', str(e), 500)

# -------------------------
# Utility endpoints
# -------------------------
@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0',
        'features': {
            'ai_manager': app_components['ai_manager'] is not None,
            'citation_analyzer': app_components['citation_analyzer'] is not None,
            'file_processor': app_components['file_processor'] is not None,
            'paper_analyzer': app_components['paper_analyzer'] is not None,
            'database': True
        }
    }

    if app_components['ai_manager']:
        try:
            ai_health = app_components['ai_manager'].health_check()
            health_status['ai_status'] = ai_health
        except Exception as e:
            health_status['ai_status'] = {'status': 'unhealthy', 'error': str(e)}

    return jsonify(health_status)

@app.route('/api/journals')
def api_get_journals():
    """Get list of available journals"""
    try:
        journals = app_components['db_helper'].get_all_journals()
        return success_response({'journals': journals})
    except Exception as e:
        logger.error(f"Failed to fetch journals: {str(e)}")
        return error_response('Failed to fetch journals', str(e), 500)

# -------------------------
# Error handlers
# -------------------------
@app.errorhandler(404)
def not_found_error(error):
    return error_response('Not found', 'The requested resource was not found', 404)

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return error_response('Internal server error', 'An unexpected error occurred', 500)

@app.errorhandler(413)
def too_large(e):
    return error_response(
        'File too large', 
        f'Maximum file size is {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB',
        413
    )

@app.errorhandler(429)
def ratelimit_handler(e):
    return error_response(
        'Rate limit exceeded',
        'Too many requests. Please try again later.',
        429
    )

# -------------------------
# Main
# -------------------------
def create_directories():
    """Create necessary directories"""
    directories = [Config.UPLOAD_FOLDER, Config.FIGURES_FOLDER]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def print_startup_info():
    """Print application startup information"""
    print("\n" + "="*60)
    print("EvideciaFlow Research Platform v2.0 Starting...")
    print("="*60)
    
    components_status = [
        ("AI Manager", app_components['ai_manager']),
        ("Citation Analyzer", app_components['citation_analyzer']),
        ("File Processor", app_components['file_processor']),
        ("Paper Analyzer", app_components['paper_analyzer']),
    ]
    
    for name, component in components_status:
        status = "✓ Available" if component else "✗ Unavailable"
        print(f"{name:<20}: {status}")
    
    print("="*60)
    
    unavailable = [name for name, component in components_status if not component]
    if unavailable:
        print("⚠️  Warning: Limited functionality due to missing components:")
        for component in unavailable:
            print(f"   - {component}")
        print()
    
    print("🚀 Starting Flask server on http://localhost:5000")
    print("\n📋 Available endpoints:")
    endpoints = [
        ("GET  /", "Dashboard"),
        ("GET  /paper-analyzer", "Paper Analysis Tools"),
        ("GET  /citation-context", "Citation Analysis"),
        ("GET  /explain-rewrite", "Text Rewriting"),
        ("POST /api/analyze-paper", "Upload & analyze paper"),
        ("POST /api/run-tool/<tool>", "Run analysis tool"),
        ("GET  /api/health", "Health check"),
    ]
    
    for method_path, description in endpoints:
        print(f"   {method_path:<25} → {description}")
    
    print("="*60 + "\n")

if __name__ == '__main__':
    create_directories()
    print_startup_info()
    
    # Production considerations
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
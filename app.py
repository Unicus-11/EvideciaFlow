# app.py - Main Flask application
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import os
import sys
import uuid
from datetime import datetime
import json
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your actual feature modules (not handlers)
try:
    from backend.citation_context import CitationContextAnalyzer
except ImportError:
    CitationContextAnalyzer = None
    print("Warning: CitationContextAnalyzer not found")

try:
    from ai.ai_manager import AIManager
except ImportError:
    AIManager = None
    print("Warning: AIManager not found")

# Import utilities
try:
    from backend.utils.database_helper import DatabaseHelper
except ImportError:
    print("Warning: DatabaseHelper not found, using dummy class")
    class DatabaseHelper:
        def create_anonymous_session(self, user_id): pass
        def get_all_journals(self): return []
        def get_user_activity(self, user_id): return []

try:
    from backend.utils.file_processor import FileProcessor
except ImportError:
    FileProcessor = None
    print("Warning: FileProcessor not found")

app = Flask(__name__, template_folder='frontend', static_folder='frontend')
app.secret_key = 'research_platform_prototype_key_2024'  # Change in production
CORS(app)

# Initialize components
db_helper = DatabaseHelper()
if FileProcessor:
    file_processor = FileProcessor()
else:
    file_processor = None

if AIManager:
    try:
        ai_manager = AIManager()
    except Exception as e:
        print(f"Warning: Could not initialize AIManager: {e}")
        ai_manager = None
else:
    ai_manager = None

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif', 'tiff', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_session():
    """Get or create anonymous user session"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['created_at'] = datetime.now().isoformat()
        # Store anonymous session in database
        db_helper.create_anonymous_session(session['user_id'])
    return session['user_id']

@app.route('/')
def dashboard():
    """Main dashboard showing all features"""
    user_id = get_user_session()
    return render_template('home.html', user_id=user_id)

# ================ CITATION CONTEXT FEATURE ================
@app.route('/citation-context')
def citation_context_page():
    """Citation Context feature page"""
    return render_template('citation_context.html')

@app.route('/analyze_citations', methods=['POST'])
def analyze_citations():
    """Citation Context analysis endpoint"""
    try:
        user_id = get_user_session()
        
        # Check if CitationContextAnalyzer is available
        if not CitationContextAnalyzer:
            return jsonify({
                'success': False,
                'error': 'Citation analysis feature not available'
            }), 500
        
        # Validate request has required data
        if not request.files.get('paper_file') and not request.form.get('paper_text'):
            return jsonify({
                'success': False,
                'error': 'No paper content provided. Please upload a file or paste text.'
            }), 400
        
        # Handle file upload
        if 'paper_file' in request.files and request.files['paper_file'].filename:
            file = request.files['paper_file']
            
            # Validate file type
            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
                }), 400
            
            if not file_processor:
                return jsonify({
                    'success': False,
                    'error': 'File processing not available'
                }), 500
            
            # Save file temporarily for processing
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join('uploads/temp/', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            # Extract text using FileProcessor
            extraction_success, text_content, extraction_metadata = file_processor.extract_text_from_file(filepath)
            
            # Clean up temp file immediately after extraction
            try:
                os.remove(filepath)
            except:
                pass  # Don't fail if cleanup fails
            
            if not extraction_success:
                return jsonify({
                    'success': False,
                    'error': f'Failed to extract text from file: {text_content}'
                }), 400
            
            if not text_content.strip():
                return jsonify({
                    'success': False,
                    'error': 'The uploaded file appears to be empty or contains no readable text.'
                }), 400
            
            content_type = 'file'
            paper_content = text_content
            
        else:
            # Handle text input
            paper_content = request.form.get('paper_text', '').strip()
            if not paper_content:
                return jsonify({
                    'success': False,
                    'error': 'Please provide paper text for analysis.'
                }), 400
            content_type = 'text'
        
        # Get form parameters
        target_journal = request.form.get('target_journal', 'nature')
        analysis_type = request.form.get('analysis_type', 'comprehensive')
        custom_requirements = request.form.get('custom_requirements', '')
        
        # Initialize and run citation analysis
        citation_analyzer = CitationContextAnalyzer()
        
        result = citation_analyzer.analyze_citations(
            paper_content=paper_content,
            target_journal=target_journal,
            analysis_type=analysis_type,
            custom_requirements=custom_requirements if custom_requirements else None
        )
        
        # Format the result
        formatted_result = {
            'success': True,
            'analysis': result,
            'content_type': content_type,
            'target_journal': target_journal,
            'analysis_type': analysis_type
        }
        
        return jsonify(formatted_result)
        
    except Exception as e:
        # Log the full error for debugging
        app.logger.error(f"Citation analysis error: {str(e)}\n{traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

# ================ AI-POWERED FEATURES ================
@app.route('/api/ai-process', methods=['POST'])
def api_ai_process():
    """Generic AI processing endpoint"""
    try:
        if not ai_manager:
            return jsonify({
                'success': False,
                'error': 'AI processing not available'
            }), 500
        
        user_id = get_user_session()
        
        # Get request data
        feature = request.json.get('feature')
        data = request.json.get('data', {})
        
        if not feature:
            return jsonify({
                'success': False,
                'error': 'Feature not specified'
            }), 400
        
        # Process through AI manager
        result = ai_manager.process_request(feature, data, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ================ EXPLAIN/REWRITE FEATURE ================
@app.route('/explain-rewrite')
def explain_rewrite_page():
    """Explain/Rewrite feature page"""
    return render_template('explain_rewrite.html')

@app.route('/api/explain-rewrite', methods=['POST'])
def api_explain_rewrite():
    """API endpoint for paper rewriting using AI manager"""
    try:
        if not ai_manager:
            return jsonify({
                'success': False,
                'error': 'AI processing not available'
            }), 500
        
        user_id = get_user_session()
        
        # Handle file upload or text input
        paper_content = None
        if 'paper_file' in request.files and request.files['paper_file'].filename:
            file = request.files['paper_file']
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            
            if not file_processor:
                return jsonify({'success': False, 'error': 'File processing not available'}), 500
            
            # Save file temporarily
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join('uploads/temp/', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            # Extract text
            success, text_content, _ = file_processor.extract_text_from_file(filepath)
            os.remove(filepath)  # Clean up
            
            if not success:
                return jsonify({'success': False, 'error': f'Failed to extract text: {text_content}'}), 400
            
            paper_content = text_content
            
        elif request.form.get('paper_text'):
            paper_content = request.form.get('paper_text')
        else:
            return jsonify({'success': False, 'error': 'No paper content provided'}), 400
        
        # Prepare data for AI manager
        data = {
            'text': paper_content,
            'target_journal': request.form.get('target_journal', 'Nature'),
            'language': 'American English'
        }
        
        # Process through AI manager
        result = ai_manager.process_request('explain_rewrite', data, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ UTILITY ENDPOINTS ================
@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    health_status = {
        'status': 'healthy',
        'features': {
            'ai_manager': ai_manager is not None,
            'citation_analyzer': CitationContextAnalyzer is not None,
            'file_processor': file_processor is not None,
            'database': True  # Always available (dummy or real)
        }
    }
    
    # Test AI if available
    if ai_manager:
        try:
            ai_health = ai_manager.health_check()
            health_status['ai_status'] = ai_health
        except:
            health_status['ai_status'] = {'status': 'unhealthy'}
    
    return jsonify(health_status)

@app.route('/api/journals')
def api_get_journals():
    """Get list of available journals"""
    try:
        journals = db_helper.get_all_journals()
        return jsonify({'success': True, 'journals': journals})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ ERROR HANDLERS ================
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large. Maximum size is 16MB.'}), 413

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads/temp/', exist_ok=True)
    os.makedirs('uploads/figures/', exist_ok=True)
    
    # Run the application
    print("Starting Research Platform...")
    print(f"AI Manager: {'Available' if ai_manager else 'Not available'}")
    print(f"Citation Analyzer: {'Available' if CitationContextAnalyzer else 'Not available'}")
    print(f"File Processor: {'Available' if file_processor else 'Not available'}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
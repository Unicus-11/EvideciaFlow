# backend/app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
import os
import sys
import uuid
from datetime import datetime
import json
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import feature handlers - UPDATED PATHS
from backend.explain_rewrite_handler import ExplainRewriteHandler
from backend.figure_fixer_handler import FigureFixerHandler
from backend.protocol_optimizer_handler import ProtocolOptimizerHandler
from backend.idea_recombinator_handler import IdeaRecombinatorHandler
from backend.contradiction_detector_handler import ContradictionDetectorHandler
# Note: CitationContextHandler not needed since we're using CitationContextAnalyzer directly

# Import utilities - UPDATED PATH
try:
    from backend.utils.database_helper import DatabaseHelper
except ImportError:
    print("Warning: DatabaseHelper not found, using dummy class")
    class DatabaseHelper:
        def create_anonymous_session(self, user_id): pass
        def get_all_journals(self): return []
        def get_user_activity(self, user_id): return []

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.secret_key = 'research_platform_prototype_key_2024'  # Change in production
CORS(app)

# Initialize handlers
explain_rewrite = ExplainRewriteHandler()
figure_fixer = FigureFixerHandler()
protocol_optimizer = ProtocolOptimizerHandler()
idea_recombinator = IdeaRecombinatorHandler()
contradiction_detector = ContradictionDetectorHandler()

db_helper = DatabaseHelper()

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
    return render_template('dashboard.html', user_id=user_id)

# ================ EXPLAIN/REWRITE FEATURE ================
@app.route('/explain-rewrite')
def explain_rewrite_page():
    """Explain/Rewrite feature page"""
    return render_template('explain_rewrite.html')

@app.route('/api/explain-rewrite', methods=['POST'])
def api_explain_rewrite():
    """API endpoint for paper rewriting"""
    try:
        user_id = get_user_session()
        
        # Handle file upload or text input
        if 'paper_file' in request.files and request.files['paper_file'].filename:
            file = request.files['paper_file']
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            
            # Save file temporarily
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join('uploads/temp/', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            result = explain_rewrite.process_rewrite_request(
                user_id=user_id,
                paper_content=filepath,
                target_journal=request.form.get('target_journal'),
                content_type='file'
            )
            
            # Clean up temp file
            os.remove(filepath)
            
        elif request.form.get('paper_text'):
            result = explain_rewrite.process_rewrite_request(
                user_id=user_id,
                paper_content=request.form.get('paper_text'),
                target_journal=request.form.get('target_journal'),
                content_type='text'
            )
        else:
            return jsonify({'success': False, 'error': 'No paper content provided'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ FIGURE FIXER FEATURE ================
@app.route('/figure-fixer')
def figure_fixer_page():
    """Figure Fixer feature page"""
    return render_template('figure_fixer.html')

@app.route('/api/figure-fixer', methods=['POST'])
def api_figure_fixer():
    """API endpoint for figure fixing"""
    try:
        user_id = get_user_session()
        
        if 'figure_file' not in request.files:
            return jsonify({'success': False, 'error': 'No figure file provided'}), 400
        
        file = request.files['figure_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        result = figure_fixer.process_figure_request(
            user_id=user_id,
            figure_file=file,
            target_publication=request.form.get('target_publication'),
            figure_type=request.form.get('figure_type', 'graph')
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ PROTOCOL OPTIMIZER FEATURE ================
@app.route('/protocol-optimizer')
def protocol_optimizer_page():
    """Protocol Optimizer feature page"""
    return render_template('protocol_optimizer.html')

@app.route('/api/protocol-optimizer', methods=['POST'])
def api_protocol_optimizer():
    """API endpoint for protocol optimization"""
    try:
        user_id = get_user_session()
        
        # Handle file upload or text input
        if 'protocol_file' in request.files and request.files['protocol_file'].filename:
            file = request.files['protocol_file']
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            
            # Save file temporarily
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join('uploads/temp/', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            result = protocol_optimizer.process_protocol_optimization(
                user_id=user_id,
                protocol_content=filepath,
                research_field=request.form.get('research_field'),
                content_type='file'
            )
            
            # Clean up temp file
            os.remove(filepath)
            
        elif request.form.get('protocol_text'):
            result = protocol_optimizer.process_protocol_optimization(
                user_id=user_id,
                protocol_content=request.form.get('protocol_text'),
                research_field=request.form.get('research_field'),
                content_type='text'
            )
        else:
            return jsonify({'success': False, 'error': 'No protocol content provided'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ CITATION CONTEXT FEATURE ================
# NEW INTEGRATED CITATION CONTEXT ROUTES
@app.route('/citation-context')
def citation_context_page():
    """Citation Context feature page - serves your HTML"""
    return render_template('citation_context.html')

@app.route('/analyze_citations', methods=['POST'])
def analyze_citations():
    """
    Unified route for Citation Context analysis
    Matches the endpoint called by your HTML form
    """
    try:
        # Get user session (your existing pattern)
        user_id = get_user_session()
        
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
            
            # Save file temporarily for processing
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join('uploads/temp/', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            # Extract text using FileProcessor
            from backend.utils.file_processor import FileProcessor
            file_processor = FileProcessor()
            
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
        
        # Get form parameters with defaults matching your HTML
        target_journal = request.form.get('target_journal', 'nature')
        analysis_type = request.form.get('analysis_type', 'comprehensive')
        custom_requirements = request.form.get('custom_requirements', '')
        
        # Import and initialize CitationContextAnalyzer
        from backend.citation_context import CitationContextAnalyzer
        citation_analyzer = CitationContextAnalyzer()
        
        # Process the citation analysis
        result = citation_analyzer.process_citation_analysis(
            session_id=user_id,  # Using user_id as session_id for your anonymous system
            paper_content=paper_content,
            target_journal=target_journal,
            analysis_type=analysis_type,
            custom_requirements=custom_requirements if custom_requirements else None,
            content_type=content_type
        )
        
        # The result is already formatted correctly for your HTML
        return jsonify(result)
        
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': f'Module import failed: {str(e)}. Please check your file structure.'
        }), 500
    
    except Exception as e:
        # Log the full error for debugging
        app.logger.error(f"Citation analysis error: {str(e)}\n{traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

# Remove the old citation context route to avoid conflicts
# @app.route('/api/citation-context', methods=['POST'])  # REMOVED

# ================ IDEA RECOMBINATOR FEATURE ================
@app.route('/idea-recombinator')
def idea_recombinator_page():
    """Idea Recombinator feature page"""
    return render_template('idea_recombinator.html')

@app.route('/api/idea-recombinator', methods=['POST'])
def api_idea_recombinator():
    """API endpoint for idea recombination"""
    try:
        user_id = get_user_session()
        
        # Get form data
        research_interests = request.form.get('research_interests', '').split('\n')
        research_interests = [interest.strip() for interest in research_interests if interest.strip()]
        
        current_projects = request.form.get('current_projects', '')
        inspiration_sources = request.form.get('inspiration_sources', '')
        
        if not research_interests:
            return jsonify({'success': False, 'error': 'Please provide research interests'}), 400
        
        result = idea_recombinator.process_idea_recombination(
            user_id=user_id,
            research_interests=research_interests,
            current_projects=current_projects,
            inspiration_sources=inspiration_sources if inspiration_sources else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ CONTRADICTION DETECTOR FEATURE ================
@app.route('/contradiction-detector')
def contradiction_detector_page():
    """Contradiction Detector feature page"""
    return render_template('contradiction_detector.html')

@app.route('/api/contradiction-detector', methods=['POST'])
def api_contradiction_detector():
    """API endpoint for contradiction detection"""
    try:
        user_id = get_user_session()
        
        # Handle file upload or text input
        if 'paper_file' in request.files and request.files['paper_file'].filename:
            file = request.files['paper_file']
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            
            # Save file temporarily
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join('uploads/temp/', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            result = contradiction_detector.process_contradiction_detection(
                user_id=user_id,
                paper_content=filepath,
                analysis_depth=request.form.get('analysis_depth', 'standard'),
                content_type='file'
            )
            
            # Clean up temp file
            os.remove(filepath)
            
        elif request.form.get('paper_text'):
            result = contradiction_detector.process_contradiction_detection(
                user_id=user_id,
                paper_content=request.form.get('paper_text'),
                analysis_depth=request.form.get('analysis_depth', 'standard'),
                content_type='text'
            )
        else:
            return jsonify({'success': False, 'error': 'No paper content provided'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ UTILITY ENDPOINTS ================
@app.route('/api/journals')
def api_get_journals():
    """Get list of available journals"""
    try:
        journals = db_helper.get_all_journals()
        return jsonify({'success': True, 'journals': journals})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user-activity')
def api_user_activity():
    """Get user activity history"""
    try:
        user_id = get_user_session()
        activity = db_helper.get_user_activity(user_id)
        return jsonify({'success': True, 'activity': activity})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================ ERROR HANDLERS ================
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large. Maximum size is 16MB.'}), 413

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads/temp/', exist_ok=True)
    os.makedirs('uploads/figures/', exist_ok=True)
    os.makedirs('uploads/fixed_figures/', exist_ok=True)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)

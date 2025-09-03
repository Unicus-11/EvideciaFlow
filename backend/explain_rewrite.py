# backend/features/explain_rewrite_handler.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_manager import AIManager
from utils.database_helper import DatabaseHelper
from utils.file_processor import FileProcessor
import hashlib
from datetime import datetime

class ExplainRewriteHandler:
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        
    def process_rewrite_request(self, user_id, paper_content, target_journal, content_type='text'):
        """
        Process paper rewriting request
        Args:
            user_id: User session ID
            paper_content: Text content or file path
            target_journal: Target journal name
            content_type: 'text' or 'file'
        Returns:
            dict: Processing result with rewritten content
        """
        try:
            # Extract text from file if needed
            if content_type == 'file':
                extracted_text = self.file_processor.extract_text_from_file(paper_content)
                if not extracted_text['success']:
                    return {'success': False, 'error': 'Failed to extract text from file'}
                paper_text = extracted_text['content']
            else:
                paper_text = paper_content
            
            # Get journal requirements
            journal_info = self.db_helper.get_journal_requirements(target_journal)
            if not journal_info:
                return {'success': False, 'error': f'Journal "{target_journal}" not found'}
            
            # Process with AI
            rewrite_result = self.ai_manager.process_explain_rewrite(
                paper_text=paper_text,
                target_journal=target_journal,
                journal_requirements=journal_info
            )
            
            if not rewrite_result['success']:
                return {'success': False, 'error': 'AI processing failed'}
            
            # Generate unique ID for this rewrite
            rewrite_id = hashlib.md5(f"{user_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Store result for user
            self.db_helper.store_user_activity(
                user_id=user_id,
                feature='explain_rewrite',
                input_data={'target_journal': target_journal, 'content_length': len(paper_text)},
                result_id=rewrite_id
            )
            
            return {
                'success': True,
                'rewrite_id': rewrite_id,
                'original_text': paper_text,
                'rewritten_text': rewrite_result['rewritten_text'],
                'changes_summary': rewrite_result['changes_summary'],
                'journal_compliance': rewrite_result['compliance_check'],
                'target_journal': target_journal,
                'processing_time': rewrite_result.get('processing_time', 0)
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Processing error: {str(e)}'}


# backend/features/figure_fixer_handler.py
import os
import shutil
from PIL import Image
import uuid

class FigureFixerHandler:
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        self.upload_dir = 'uploads/figures/'
        self.fixed_dir = 'uploads/fixed_figures/'
        
        # Create directories if they don't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.fixed_dir, exist_ok=True)
        
    def process_figure_request(self, user_id, figure_file, target_publication, figure_type='graph'):
        """
        Process figure fixing request
        Args:
            user_id: User session ID
            figure_file: Uploaded figure file
            target_publication: Target publication name
            figure_type: Type of figure (graph, diagram, photo, etc.)
        Returns:
            dict: Processing result with fixed figure info
        """
        try:
            # Generate unique filename
            file_extension = os.path.splitext(figure_file.filename)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Save uploaded file
            figure_file.save(file_path)
            
            # Analyze figure
            analysis_result = self.file_processor.analyze_figure(file_path)
            if not analysis_result['success']:
                return {'success': False, 'error': 'Figure analysis failed'}
            
            # Get publication requirements
            pub_requirements = self.db_helper.get_figure_requirements(target_publication)
            if not pub_requirements:
                return {'success': False, 'error': f'Publication "{target_publication}" not found'}
            
            # Store original figure info in database
            figure_id = self.db_helper.store_user_figure(
                user_id=user_id,
                filename=unique_filename,
                original_path=file_path,
                figure_type=figure_type,
                target_publication=target_publication,
                analysis_results=analysis_result
            )
            
            # Check compliance and get AI recommendations
            compliance_check = self.ai_manager.process_figure_analysis(
                figure_analysis=analysis_result,
                publication_requirements=pub_requirements,
                figure_type=figure_type
            )
            
            # Fix figure if needed
            fixed_figure_path = None
            if not compliance_check.get('fully_compliant', False):
                fixed_result = self.file_processor.fix_figure(
                    file_path, 
                    pub_requirements, 
                    analysis_result,
                    output_dir=self.fixed_dir
                )
                if fixed_result['success']:
                    fixed_figure_path = fixed_result['fixed_path']
                    
                    # Update database with fixed figure info
                    self.db_helper.update_figure_processing(
                        figure_id=figure_id,
                        fixed_path=fixed_figure_path,
                        processing_status='completed'
                    )
            
            return {
                'success': True,
                'figure_id': figure_id,
                'original_path': file_path,
                'fixed_path': fixed_figure_path,
                'analysis': analysis_result,
                'compliance': compliance_check,
                'requirements': pub_requirements,
                'recommendations': compliance_check.get('recommendations', [])
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Processing error: {str(e)}'}


# backend/features/protocol_optimizer_handler.py
class ProtocolOptimizerHandler:
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        
    def process_protocol_optimization(self, user_id, protocol_content, research_field, content_type='text'):
        """
        Process protocol optimization request
        Args:
            user_id: User session ID
            protocol_content: Protocol text or file
            research_field: Research domain (biology, chemistry, psychology, etc.)
            content_type: 'text' or 'file'
        Returns:
            dict: Processing result with optimized protocol
        """
        try:
            # Extract text from file if needed
            if content_type == 'file':
                extracted_text = self.file_processor.extract_text_from_file(protocol_content)
                if not extracted_text['success']:
                    return {'success': False, 'error': 'Failed to extract text from file'}
                protocol_text = extracted_text['content']
            else:
                protocol_text = protocol_content
            
            # Process with AI
            optimization_result = self.ai_manager.process_protocol_optimizer(
                protocol_text=protocol_text,
                research_field=research_field
            )
            
            if not optimization_result['success']:
                return {'success': False, 'error': 'AI processing failed'}
            
            # Generate result ID
            result_id = hashlib.md5(f"{user_id}protocol{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Store activity
            self.db_helper.store_user_activity(
                user_id=user_id,
                feature='protocol_optimizer',
                input_data={'research_field': research_field, 'content_length': len(protocol_text)},
                result_id=result_id
            )
            
            return {
                'success': True,
                'result_id': result_id,
                'original_protocol': protocol_text,
                'optimized_protocol': optimization_result['optimized_protocol'],
                'improvements': optimization_result['improvements'],
                'risk_assessment': optimization_result['risk_assessment'],
                'efficiency_suggestions': optimization_result['efficiency_suggestions'],
                'research_field': research_field
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Processing error: {str(e)}'}


# backend/features/citation_context_handler.py
class CitationContextHandler:
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        
    def process_citation_analysis(self, user_id, paper_content, citation_style='APA', content_type='text'):
        """
        Process citation context analysis
        Args:
            user_id: User session ID
            paper_content: Paper text or file with citations
            citation_style: Citation format (APA, IEEE, Nature, etc.)
            content_type: 'text' or 'file'
        Returns:
            dict: Processing result with citation analysis
        """
        try:
            # Extract text from file if needed
            if content_type == 'file':
                extracted_text = self.file_processor.extract_text_from_file(paper_content)
                if not extracted_text['success']:
                    return {'success': False, 'error': 'Failed to extract text from file'}
                paper_text = extracted_text['content']
            else:
                paper_text = paper_content
            
            # Process with AI
            citation_analysis = self.ai_manager.process_citation_context(
                paper_text=paper_text,
                citation_style=citation_style
            )
            
            if not citation_analysis['success']:
                return {'success': False, 'error': 'AI processing failed'}
            
            # Generate result ID
            result_id = hashlib.md5(f"{user_id}citation{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Store activity
            self.db_helper.store_user_activity(
                user_id=user_id,
                feature='citation_context',
                input_data={'citation_style': citation_style, 'content_length': len(paper_text)},
                result_id=result_id
            )
            
            return {
                'success': True,
                'result_id': result_id,
                'original_text': paper_text,
                'citation_analysis': citation_analysis['analysis'],
                'context_improvements': citation_analysis['context_improvements'],
                'formatting_corrections': citation_analysis['formatting_corrections'],
                'missing_citations': citation_analysis['missing_citations'],
                'over_citations': citation_analysis['over_citations'],
                'citation_style': citation_style
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Processing error: {str(e)}'}


# backend/features/idea_recombinator_handler.py
class IdeaRecombinatorHandler:
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        
    def process_idea_recombination(self, user_id, research_interests, current_projects, inspiration_sources=None):
        """
        Process idea recombination request
        Args:
            user_id: User session ID
            research_interests: List of research areas/interests
            current_projects: Description of ongoing projects
            inspiration_sources: Optional external sources for inspiration
        Returns:
            dict: Processing result with novel research ideas
        """
        try:
            # Process with AI
            recombination_result = self.ai_manager.process_idea_recombinator(
                research_interests=research_interests,
                current_projects=current_projects,
                inspiration_sources=inspiration_sources
            )
            
            if not recombination_result['success']:
                return {'success': False, 'error': 'AI processing failed'}
            
            # Generate result ID
            result_id = hashlib.md5(f"{user_id}ideas{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Store activity
            self.db_helper.store_user_activity(
                user_id=user_id,
                feature='idea_recombinator',
                input_data={'interests_count': len(research_interests), 'has_inspiration': bool(inspiration_sources)},
                result_id=result_id
            )
            
            return {
                'success': True,
                'result_id': result_id,
                'novel_ideas': recombination_result['novel_ideas'],
                'cross_domain_connections': recombination_result['cross_domain_connections'],
                'research_gaps': recombination_result['research_gaps'],
                'implementation_paths': recombination_result['implementation_paths'],
                'collaboration_opportunities': recombination_result['collaboration_opportunities']
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Processing error: {str(e)}'}


# backend/features/contradiction_detector_handler.py
class ContradictionDetectorHandler:
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        
    def process_contradiction_detection(self, user_id, paper_content, analysis_depth='standard', content_type='text'):
        """
        Process contradiction detection in research paper
        Args:
            user_id: User session ID
            paper_content: Research paper text or file
            analysis_depth: 'quick', 'standard', or 'thorough'
            content_type: 'text' or 'file'
        Returns:
            dict: Processing result with contradictions found
        """
        try:
            # Extract text from file if needed
            if content_type == 'file':
                extracted_text = self.file_processor.extract_text_from_file(paper_content)
                if not extracted_text['success']:
                    return {'success': False, 'error': 'Failed to extract text from file'}
                paper_text = extracted_text['content']
            else:
                paper_text = paper_content
            
            # Process with AI
            contradiction_analysis = self.ai_manager.process_contradiction_detector(
                paper_text=paper_text,
                analysis_depth=analysis_depth
            )
            
            if not contradiction_analysis['success']:
                return {'success': False, 'error': 'AI processing failed'}
            
            # Generate result ID
            result_id = hashlib.md5(f"{user_id}contradictions{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            # Store activity
            self.db_helper.store_user_activity(
                user_id=user_id,
                feature='contradiction_detector',
                input_data={'analysis_depth': analysis_depth, 'content_length': len(paper_text)},
                result_id=result_id
            )
            
            return {
                'success': True,
                'result_id': result_id,
                'original_text': paper_text,
                'contradictions': contradiction_analysis['contradictions'],
                'logical_inconsistencies': contradiction_analysis['logical_inconsistencies'],
                'methodology_conflicts': contradiction_analysis['methodology_conflicts'],
                'data_inconsistencies': contradiction_analysis['data_inconsistencies'],
                'severity_levels': contradiction_analysis['severity_levels'],
                'suggestions_for_resolution': contradiction_analysis['suggestions'],
                'analysis_depth': analysis_depth
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Processing error: {str(e)}'}


# backend/features/__init__.py
"""
Research Platform Feature Handlers
Connects AI processing with user inputs and database storage
"""

from .explain_rewrite_handler import ExplainRewriteHandler
from .figure_fixer_handler import FigureFixerHandler
from .protocol_optimizer_handler import ProtocolOptimizerHandler
from .citation_context_handler import CitationContextHandler
from .idea_recombinator_handler import IdeaRecombinatorHandler
from .contradiction_detector_handler import ContradictionDetectorHandler

__all__ = [
    'ExplainRewriteHandler',
    'FigureFixerHandler', 
    'ProtocolOptimizerHandler',
    'CitationContextHandler',
    'IdeaRecombinatorHandler',
    'ContradictionDetectorHandler'
]

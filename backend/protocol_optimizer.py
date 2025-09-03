"""
Protocol Optimizer Handler
Integrates with existing EvideciaFlow architecture for protocol optimization
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Import existing utilities (matching your app.py structure)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.database_helper import DatabaseHelper
from utils.file_processor import FileProcessor
from ai.ai_manager import AIManager
from ai.prompt_templates import PromptTemplates

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProtocolOptimizerHandler:
    """
    Protocol Optimizer Handler - matches your existing handler pattern
    """
    
    def __init__(self):
        """Initialize handler with existing utilities"""
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        self.ai_manager = AIManager()
        self.prompt_templates = PromptTemplates()
        self.database_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'protocols.db')
        
    def process_protocol_optimization(self, user_id: str, protocol_content: str, 
                                    research_field: str, content_type: str = 'text',
                                    **kwargs) -> Dict[str, Any]:
        """
        Main method matching your app.py call pattern
        
        Args:
            user_id: User session ID
            protocol_content: File path or text content  
            research_field: Research field from form
            content_type: 'file' or 'text'
            **kwargs: Additional form data
            
        Returns:
            Dictionary with success status and results
        """
        try:
            # Step 1: Extract protocol text
            if content_type == 'file':
                protocol_text = self._extract_text_from_file(protocol_content)
                filename = os.path.basename(protocol_content)
                file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            else:
                protocol_text = protocol_content
                filename = None
                file_type = 'manual'
            
            if not protocol_text or len(protocol_text.strip()) < 50:
                return {
                    'success': False,
                    'error': 'Protocol content is too short or empty. Please provide more detailed protocol information.'
                }
            
            # Step 2: Extract form data
            form_data = self._parse_form_data(kwargs)
            
            # Step 3: Store protocol in database
            protocol_id = self._store_protocol(
                user_id=user_id,
                protocol_text=protocol_text,
                filename=filename,
                file_type=file_type,
                research_field=research_field,
                form_data=form_data
            )
            
            # Step 4: Process with AI
            ai_results = self._analyze_with_ai(protocol_text, research_field, form_data)
            
            if not ai_results['success']:
                self._update_protocol_status(protocol_id, 'error', ai_results.get('error'))
                return ai_results
            
            # Step 5: Store AI results in database
            self._store_analysis_results(protocol_id, ai_results['results'])
            
            # Step 6: Update protocol status
            self._update_protocol_status(protocol_id, 'completed')
            
            # Step 7: Format response for frontend
            formatted_results = self._format_results_for_frontend(ai_results['results'])
            
            return {
                'success': True,
                'protocol_id': protocol_id,
                'analysis_complete': True,
                'results': formatted_results,
                'metadata': {
                    'protocol_length': len(protocol_text),
                    'research_field': research_field,
                    'analysis_categories': list(form_data.get('focus_areas', [])),
                    'processing_time': ai_results.get('processing_time_ms', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Protocol optimization error: {str(e)}")
            return {
                'success': False,
                'error': f'Protocol optimization failed: {str(e)}',
                'error_type': 'processing_error'
            }
    
    def _extract_text_from_file(self, filepath: str) -> str:
        """Extract text from uploaded file using existing file processor"""
        try:
            return self.file_processor.extract_text(filepath)
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            raise Exception(f"Could not extract text from file: {str(e)}")
    
    def _parse_form_data(self, kwargs: Dict) -> Dict[str, Any]:
        """Parse form data from HTML form submission"""
        form_data = {}
        
        # Parse study details
        form_data['study_type'] = kwargs.get('study_type', '')
        form_data['sample_size'] = self._safe_int_convert(kwargs.get('sample_size'))
        form_data['duration'] = kwargs.get('duration', '')
        
        # Parse focus areas (JSON string from frontend)
        focus_areas_raw = kwargs.get('focus_areas', '[]')
        try:
            if isinstance(focus_areas_raw, str):
                form_data['focus_areas'] = json.loads(focus_areas_raw)
            else:
                form_data['focus_areas'] = focus_areas_raw
        except json.JSONDecodeError:
            form_data['focus_areas'] = []
        
        return form_data
    
    def _safe_int_convert(self, value) -> Optional[int]:
        """Safely convert string to int"""
        if not value:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _store_protocol(self, user_id: str, protocol_text: str, filename: Optional[str],
                       file_type: str, research_field: str, form_data: Dict) -> int:
        """Store protocol in database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO protocols (
                    user_id, protocol_text, original_filename, file_type,
                    study_type, research_field, sample_size, duration,
                    focus_areas, status, processing_started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                protocol_text,
                filename,
                file_type,
                form_data.get('study_type'),
                research_field,
                form_data.get('sample_size'),
                form_data.get('duration'),
                json.dumps(form_data.get('focus_areas', [])),
                'processing',
                datetime.now().isoformat()
            ))
            
            protocol_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return protocol_id
            
        except Exception as e:
            logger.error(f"Protocol storage failed: {str(e)}")
            raise Exception(f"Database storage failed: {str(e)}")
    
    def _analyze_with_ai(self, protocol_text: str, research_field: str, 
                        form_data: Dict) -> Dict[str, Any]:
        """Analyze protocol with AI using existing AI manager"""
        try:
            start_time = datetime.now()
            
            # Get specialized prompt for protocol optimization
            prompt = self.prompt_templates.get_protocol_optimization_prompt(
                protocol=protocol_text,
                field=research_field
            )
            
            # Get system prompt
            system_prompt = self.prompt_templates.get_feature_system_prompt('protocol_optimizer')
            
            # Call AI with context about focus areas
            focus_areas = form_data.get('focus_areas', [])
            enhanced_prompt = f"{prompt}\n\nFOCUS AREAS REQUESTED: {', '.join(focus_areas)}"
            
            ai_response = self.ai_manager.process_request(
                feature='protocol_optimizer',
                user_input=enhanced_prompt,
                system_prompt=system_prompt,
                model_preference='llama-3-70b'  # Use larger model for complex analysis
            )
            
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if not ai_response.get('success'):
                return {
                    'success': False,
                    'error': ai_response.get('error', 'AI analysis failed'),
                    'processing_time_ms': processing_time_ms
                }
            
            # Parse AI response into structured results
            parsed_results = self._parse_ai_response(ai_response['response'])
            
            return {
                'success': True,
                'results': parsed_results,
                'processing_time_ms': processing_time_ms,
                'ai_model': ai_response.get('model_used', 'llama-3-70b'),
                'tokens_used': ai_response.get('tokens_used', 0)
            }
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            return {
                'success': False,
                'error': f'AI analysis failed: {str(e)}',
                'processing_time_ms': 0
            }
    
    def _parse_ai_response(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured analysis results"""
        results = []
        
        try:
            # Split response into sections (this is a simplified parser)
            # In production, you might want more sophisticated parsing
            sections = ai_response.split('\n\n')
            
            current_result = {}
            result_type = 'improvement'  # default
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                # Detect section types
                if any(keyword in section.lower() for keyword in ['optimized protocol', 'improvements', 'enhanced']):
                    result_type = 'improvement'
                    current_result = {
                        'type': 'improvement',
                        'title': 'Protocol Enhancement',
                        'description': section,
                        'severity': 'medium',
                        'category': 'methodology_optimization'
                    }
                    results.append(current_result)
                
                elif any(keyword in section.lower() for keyword in ['risk', 'issue', 'problem', 'concern']):
                    result_type = 'risk'
                    current_result = {
                        'type': 'risk',
                        'title': 'Potential Risk Identified',
                        'description': section,
                        'severity': 'medium',
                        'category': 'bias_detection'
                    }
                    results.append(current_result)
                
                elif any(keyword in section.lower() for keyword in ['recommend', 'suggest', 'consider']):
                    result_type = 'suggestion'
                    current_result = {
                        'type': 'suggestion',
                        'title': 'Methodology Suggestion',
                        'description': section,
                        'severity': 'low',
                        'category': 'methodology_optimization'
                    }
                    results.append(current_result)
                
                elif any(keyword in section.lower() for keyword in ['statistical', 'power', 'sample size']):
                    current_result = {
                        'type': 'improvement',
                        'title': 'Statistical Power Enhancement',
                        'description': section,
                        'severity': 'high',
                        'category': 'statistical_power'
                    }
                    results.append(current_result)
            
            # If no structured results found, create a general improvement
            if not results:
                results.append({
                    'type': 'improvement',
                    'title': 'Protocol Analysis Complete',
                    'description': ai_response[:500] + '...' if len(ai_response) > 500 else ai_response,
                    'severity': 'medium',
                    'category': 'general'
                })
            
            return results
            
        except Exception as e:
            logger.error(f"AI response parsing failed: {str(e)}")
            # Fallback: return the raw response as a single result
            return [{
                'type': 'improvement',
                'title': 'Protocol Analysis',
                'description': ai_response,
                'severity': 'medium',
                'category': 'general'
            }]
    
    def _store_analysis_results(self, protocol_id: int, results: List[Dict]) -> None:
        """Store AI analysis results in database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            for i, result in enumerate(results):
                cursor.execute("""
                    INSERT INTO protocol_analysis_results (
                        protocol_id, category, severity, result_type, title,
                        description, confidence_score, ai_model, priority_rank,
                        impact_level
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    protocol_id,
                    result.get('category', 'general'),
                    result.get('severity', 'medium'),
                    result.get('type', 'improvement'),
                    result.get('title', 'Protocol Analysis'),
                    result.get('description', ''),
                    0.85,  # Default confidence
                    'llama-3-70b',
                    i + 1,  # Priority rank
                    'medium'  # Default impact
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Results storage failed: {str(e)}")
            # Don't raise exception here - we still want to return results
    
    def _update_protocol_status(self, protocol_id: int, status: str, 
                               error_message: Optional[str] = None) -> None:
        """Update protocol processing status"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            if status == 'completed':
                cursor.execute("""
                    UPDATE protocols 
                    SET status = ?, processing_completed_at = ?, updated_at = ?
                    WHERE protocol_id = ?
                """, (status, datetime.now().isoformat(), datetime.now().isoformat(), protocol_id))
            else:
                cursor.execute("""
                    UPDATE protocols 
                    SET status = ?, updated_at = ?
                    WHERE protocol_id = ?
                """, (status, datetime.now().isoformat(), protocol_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Status update failed: {str(e)}")
    
    def _format_results_for_frontend(self, results: List[Dict]) -> List[Dict]:
        """Format results for frontend display matching HTML expectations"""
        formatted_results = []
        
        for result in results:
            # Determine CSS class based on type and severity
            css_class = 'improvement-card'
            if result.get('type') == 'risk' or result.get('severity') == 'high':
                css_class += ' risk-card'
            elif result.get('type') == 'suggestion':
                css_class += ' suggestion-card'
            
            # Create icon based on type
            icon = '✅'
            if result.get('type') == 'risk':
                icon = '⚠️'
            elif result.get('type') == 'suggestion':
                icon = '💡'
            elif result.get('category') == 'statistical_power':
                icon = '📊'
            elif result.get('category') == 'reproducibility':
                icon = '🔄'
            
            formatted_results.append({
                'title': f"{icon} {result.get('title', 'Protocol Analysis')}",
                'description': result.get('description', ''),
                'css_class': css_class,
                'type': result.get('type', 'improvement'),
                'category': result.get('category', 'general'),
                'severity': result.get('severity', 'medium')
            })
        
        return formatted_results
    
    def get_protocol_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's protocol optimization history"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT protocol_id, study_type, research_field, status, 
                       created_at, sample_size, duration
                FROM protocols 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                history.append({
                    'protocol_id': row[0],
                    'study_type': row[1],
                    'research_field': row[2],
                    'status': row[3],
                    'created_at': row[4],
                    'sample_size': row[5],
                    'duration': row[6]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"History retrieval failed: {str(e)}")
            return []

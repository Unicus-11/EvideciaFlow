"""
Contradiction Detector Backend Feature
Analyzes research texts for logical contradictions and inconsistencies
"""

import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_manager import AIManager
from backend.utils.database_helper import DatabaseHelper
from backend.utils.file_processor import FileProcessor


class ContradictionDetector:
    """Backend handler for contradiction detection feature"""
    
    def __init__(self, ai_manager: AIManager = None, db_helper: DatabaseHelper = None, 
                 file_processor: FileProcessor = None):
        """
        Initialize ContradictionDetector with dependencies
        
        Args:
            ai_manager: AIManager instance for AI processing
            db_helper: DatabaseHelper instance for database operations
            file_processor: FileProcessor instance for file handling
        """
        self.ai_manager = ai_manager or AIManager()
        self.db_helper = db_helper or DatabaseHelper()
        self.file_processor = file_processor or FileProcessor()
        
        self.logger = logging.getLogger(__name__)
        
        # Validation constants
        self.MIN_TEXT_LENGTH = 10
        self.MAX_TEXT_LENGTH = 50000  # ~50KB text limit
        self.VALID_CHECK_TYPES = ['internal', 'external', 'both']
    
    def analyze_text_contradictions(self, text: str, session_id: str, 
                                  check_type: str = 'internal') -> Dict[str, Any]:
        """
        Analyze text for contradictions using AI
        
        Args:
            text: Text to analyze for contradictions
            session_id: User session ID
            check_type: Type of contradiction check ('internal', 'external', 'both')
            
        Returns:
            Dict with analysis results and metadata
        """
        try:
            # Input validation
            validation_error = self._validate_text_input(text, session_id, check_type)
            if validation_error:
                return validation_error
            
            # Update user session activity
            self.db_helper.update_session_activity(session_id)
            
            # Prepare AI request data
            ai_request_data = {
                'text': text,
                'check_type': check_type
            }
            
            self.logger.info(f"Starting contradiction analysis for session {session_id}")
            
            # Process with AI
            ai_response = self.ai_manager.process_request('contradiction_detector', ai_request_data)
            
            if not ai_response.get('success', False):
                self.logger.error(f"AI processing failed: {ai_response.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': f"AI analysis failed: {ai_response.get('error', 'Unknown error')}",
                    'session_id': session_id
                }
            
            # Extract results from AI response
            analysis_results = {
                'contradictions': ai_response.get('contradictions', []),
                'logical_issues': ai_response.get('logical_issues', []),
                'consistency_score': ai_response.get('consistency_score', 0),
                'recommendations': ai_response.get('recommendations', []),
                'check_type': check_type,
                'text_length': len(text.split()),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Save to database
            try:
                analysis_id = self.db_helper.save_contradiction_analysis(
                    session_id=session_id,
                    analyzed_text=text[:1000],  # Store first 1000 chars for reference
                    contradictions=analysis_results,
                    metadata={
                        'contradictions_count': len(analysis_results['contradictions']),
                        'consistency_score': analysis_results['consistency_score'],
                        'check_type': check_type,
                        'text_word_count': len(text.split())
                    }
                )
                
                analysis_results['analysis_id'] = analysis_id
                self.logger.info(f"Contradiction analysis completed and saved (ID: {analysis_id})")
                
            except Exception as db_error:
                self.logger.error(f"Database save failed: {str(db_error)}")
                # Continue with results even if DB save fails
                analysis_results['database_warning'] = "Results not saved to database"
            
            return {
                'success': True,
                'feature': 'contradiction_detector',
                'session_id': session_id,
                **analysis_results
            }
            
        except Exception as e:
            self.logger.error(f"Contradiction analysis failed: {str(e)}")
            return {
                'success': False,
                'error': f"Analysis failed: {str(e)}",
                'session_id': session_id,
                'feature': 'contradiction_detector'
            }
    
    def analyze_file_contradictions(self, file_path: str, session_id: str, 
                                  check_type: str = 'internal') -> Dict[str, Any]:
        """
        Analyze uploaded file for contradictions
        
        Args:
            file_path: Path to uploaded file
            session_id: User session ID
            check_type: Type of contradiction check
            
        Returns:
            Dict with analysis results and metadata
        """
        try:
            # Validate inputs
            if not session_id or not session_id.strip():
                return {
                    'success': False,
                    'error': "Valid session ID is required",
                    'feature': 'contradiction_detector'
                }
            
            if check_type not in self.VALID_CHECK_TYPES:
                check_type = 'internal'  # Default fallback
            
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': "File not found",
                    'session_id': session_id,
                    'file_path': file_path
                }
            
            self.logger.info(f"Processing file for contradiction analysis: {file_path}")
            
            # Extract text from file
            extraction_result = self.file_processor.extract_text_from_file(file_path)
            
            if not extraction_result.get('success', False):
                return {
                    'success': False,
                    'error': f"File processing failed: {extraction_result.get('error', 'Unknown error')}",
                    'session_id': session_id,
                    'file_path': file_path
                }
            
            extracted_text = extraction_result.get('text', '')
            
            if not extracted_text or len(extracted_text.strip()) < self.MIN_TEXT_LENGTH:
                return {
                    'success': False,
                    'error': "No sufficient text content found in file",
                    'session_id': session_id,
                    'file_path': file_path
                }
            
            # Analyze extracted text
            analysis_result = self.analyze_text_contradictions(
                text=extracted_text,
                session_id=session_id,
                check_type=check_type
            )
            
            # Add file metadata to result
            if analysis_result.get('success'):
                analysis_result['source_file'] = os.path.basename(file_path)
                analysis_result['file_type'] = extraction_result.get('file_type', 'unknown')
                analysis_result['extraction_metadata'] = extraction_result.get('metadata', {})
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"File contradiction analysis failed: {str(e)}")
            return {
                'success': False,
                'error': f"File analysis failed: {str(e)}",
                'session_id': session_id,
                'file_path': file_path,
                'feature': 'contradiction_detector'
            }
    
    def get_analysis_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's contradiction analysis history
        
        Args:
            session_id: User session ID
            limit: Maximum number of records to return
            
        Returns:
            List of analysis history records
        """
        try:
            if not session_id or not session_id.strip():
                self.logger.warning("Empty session_id provided for history request")
                return []
            
            with self.db_helper.get_db_connection('users') as conn:
                cursor = conn.execute("""
                    SELECT feature_used, action_taken, metadata, timestamp
                    FROM activity_logs 
                    WHERE session_id = ? AND feature_used = 'contradiction_detector'
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit))
                
                history = []
                for row in cursor.fetchall():
                    try:
                        metadata = row['metadata']
                        if isinstance(metadata, str):
                            import json
                            metadata = json.loads(metadata)
                        
                        history_item = {
                            'timestamp': row['timestamp'],
                            'action': row['action_taken'],
                            'contradictions_count': metadata.get('contradictions_count', 0),
                            'consistency_score': metadata.get('consistency_score', 0),
                            'check_type': metadata.get('check_type', 'internal'),
                            'text_word_count': metadata.get('text_word_count', 0)
                        }
                        history.append(history_item)
                        
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(f"Skipping malformed history record: {e}")
                        continue
                
                return history
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve analysis history: {str(e)}")
            return []
    
    def get_contradiction_statistics(self, session_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get user's contradiction analysis statistics
        
        Args:
            session_id: User session ID
            days: Number of days to analyze
            
        Returns:
            Dict with statistics
        """
        try:
            history = self.get_analysis_history(session_id, limit=100)  # Get more data for stats
            
            if not history:
                return {
                    'total_analyses': 0,
                    'average_consistency_score': 0,
                    'total_contradictions_found': 0,
                    'analysis_types': {},
                    'period_days': days
                }
            
            # Calculate statistics
            total_analyses = len(history)
            consistency_scores = [item['consistency_score'] for item in history if item['consistency_score']]
            avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0
            total_contradictions = sum(item['contradictions_count'] for item in history)
            
            # Analysis types breakdown
            analysis_types = {}
            for item in history:
                check_type = item.get('check_type', 'internal')
                analysis_types[check_type] = analysis_types.get(check_type, 0) + 1
            
            return {
                'total_analyses': total_analyses,
                'average_consistency_score': round(avg_consistency, 2),
                'total_contradictions_found': total_contradictions,
                'analysis_types': analysis_types,
                'period_days': days,
                'last_analysis': history[0]['timestamp'] if history else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate statistics: {str(e)}")
            return {
                'total_analyses': 0,
                'average_consistency_score': 0,
                'total_contradictions_found': 0,
                'analysis_types': {},
                'period_days': days,
                'error': str(e)
            }
    
    def _validate_text_input(self, text: str, session_id: str, check_type: str) -> Optional[Dict[str, Any]]:
        """
        Validate text input parameters
        
        Args:
            text: Text to validate
            session_id: Session ID to validate
            check_type: Check type to validate
            
        Returns:
            Error dict if validation fails, None if valid
        """
        # Validate session ID
        if not session_id or not session_id.strip():
            return {
                'success': False,
                'error': "Valid session ID is required",
                'feature': 'contradiction_detector'
            }
        
        # Validate text
        if not text or not text.strip():
            return {
                'success': False,
                'error': "Text cannot be empty",
                'session_id': session_id
            }
        
        if len(text.strip()) < self.MIN_TEXT_LENGTH:
            return {
                'success': False,
                'error': f"Text too short. Minimum {self.MIN_TEXT_LENGTH} characters required.",
                'session_id': session_id
            }
        
        if len(text) > self.MAX_TEXT_LENGTH:
            return {
                'success': False,
                'error': f"Text too long. Maximum {self.MAX_TEXT_LENGTH} characters allowed.",
                'session_id': session_id
            }
        
        # Validate check type
        if check_type not in self.VALID_CHECK_TYPES:
            # Don't fail, just log warning and use default
            self.logger.warning(f"Invalid check_type '{check_type}', using 'internal'")
        
        return None  # No validation errors
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if contradiction detector service is healthy
        
        Returns:
            Dict with health status
        """
        try:
            # Test AI manager
            ai_health = self.ai_manager.health_check()
            
            # Test database connection
            db_connections = self.db_helper.test_database_connections()
            
            # Test file processor (basic check)
            file_processor_healthy = hasattr(self.file_processor, 'extract_text_from_file')
            
            return {
                'service': 'contradiction_detector',
                'status': 'healthy' if ai_health.get('status') == 'healthy' else 'unhealthy',
                'ai_service': ai_health,
                'database_connections': db_connections,
                'file_processor': file_processor_healthy,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'service': 'contradiction_detector',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Utility function for standalone testing
def main():
    """Test function for development"""
    # Initialize detector
    detector = ContradictionDetector()
    
    # Test text
    test_text = """
    Climate change is primarily caused by human activities like burning fossil fuels.
    However, recent studies show that climate change is entirely natural and humans
    have no impact on global warming. The evidence clearly demonstrates that
    anthropogenic factors are the main driver of current climate trends.
    """
    
    # Test analysis
    result = detector.analyze_text_contradictions(
        text=test_text,
        session_id="test_session_123",
        check_type="internal"
    )
    
    print("Contradiction Analysis Result:")
    print(f"Success: {result.get('success')}")
    print(f"Contradictions found: {len(result.get('contradictions', []))}")
    print(f"Consistency score: {result.get('consistency_score')}")
    
    # Test health check
    health = detector.health_check()
    print(f"\nHealth Status: {health.get('status')}")


if __name__ == "__main__":
    main()

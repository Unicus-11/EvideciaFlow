"""
Database Helper for Research Platform
Centralized database operations for all features
"""

import sqlite3
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
from contextlib import contextmanager


class DatabaseHelper:
    """Centralized database operations manager"""
    
    def __init__(self, db_path: str = "databases/"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(exist_ok=True)
        
        # Database file paths
        self.databases = {
            'users': self.db_path / 'users.db',
            'journal_requirements': self.db_path / 'journal_requirements.db',
            'figures': self.db_path / 'figures.db',
            'research_papers_content': self.db_path / 'research_papers_content.db',
            'protocols': self.db_path / 'protocols.db',
            'references': self.db_path / 'references.db',
            'knowledge_base': self.db_path / 'knowledge_base.db'
        }
        
        self.logger = logging.getLogger(__name__)
    
    @contextmanager
    def get_db_connection(self, db_name: str):
        """Context manager for database connections"""
        if db_name not in self.databases:
            raise ValueError(f"Unknown database: {db_name}")
        
        conn = sqlite3.connect(self.databases[db_name])
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
        finally:
            conn.close()
    
    # User Management
    def create_anonymous_session(self) -> str:
        """Create anonymous session ID"""
        session_id = hashlib.md5(f"{datetime.now().isoformat()}{id(object())}".encode()).hexdigest()
        
        with self.get_db_connection('users') as conn:
            conn.execute("""
                INSERT INTO anonymous_sessions (session_id, created_at, last_activity)
                VALUES (?, ?, ?)
            """, (session_id, datetime.now(), datetime.now()))
            conn.commit()
        
        return session_id
    
    def update_session_activity(self, session_id: str):
        """Update last activity for session"""
        with self.get_db_connection('users') as conn:
            conn.execute("""
                UPDATE anonymous_sessions 
                SET last_activity = ? 
                WHERE session_id = ?
            """, (datetime.now(), session_id))
            conn.commit()
    
    def get_user_preferences(self, session_id: str = None, user_id: int = None) -> Dict[str, Any]:
        """Get user preferences (registered or anonymous)"""
        with self.get_db_connection('users') as conn:
            if user_id:
                cursor = conn.execute("""
                    SELECT preferred_language, preferred_citation_style, journal_preferences
                    FROM users WHERE user_id = ?
                """, (user_id,))
            else:
                cursor = conn.execute("""
                    SELECT preferred_language, preferred_citation_style, journal_preferences
                    FROM anonymous_sessions WHERE session_id = ?
                """, (session_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'language': row['preferred_language'] or 'American English',
                    'citation_style': row['preferred_citation_style'] or 'APA',
                    'journal_preferences': json.loads(row['journal_preferences'] or '[]')
                }
            else:
                return {
                    'language': 'American English',
                    'citation_style': 'APA',
                    'journal_preferences': []
                }
    
    def update_user_preferences(self, preferences: Dict[str, Any], session_id: str = None, user_id: int = None):
        """Update user preferences"""
        with self.get_db_connection('users') as conn:
            if user_id:
                conn.execute("""
                    UPDATE users 
                    SET preferred_language = ?, preferred_citation_style = ?, journal_preferences = ?
                    WHERE user_id = ?
                """, (
                    preferences.get('language'),
                    preferences.get('citation_style'),
                    json.dumps(preferences.get('journal_preferences', [])),
                    user_id
                ))
            else:
                conn.execute("""
                    UPDATE anonymous_sessions 
                    SET preferred_language = ?, preferred_citation_style = ?, journal_preferences = ?
                    WHERE session_id = ?
                """, (
                    preferences.get('language'),
                    preferences.get('citation_style'),
                    json.dumps(preferences.get('journal_preferences', [])),
                    session_id
                ))
            conn.commit()
    
    # Journal Requirements
    def get_journal_requirements(self, journal_name: str) -> Dict[str, Any]:
        """Get requirements for specific journal"""
        with self.get_db_connection('journal_requirements') as conn:
            cursor = conn.execute("""
                SELECT * FROM publications 
                WHERE LOWER(name) = LOWER(?) OR LOWER(short_name) = LOWER(?)
            """, (journal_name, journal_name))
            
            row = cursor.fetchone()
            if row:
                return {
                    'publication_id': row['publication_id'],
                    'name': row['name'],
                    'type': row['type'],
                    'word_limits': json.loads(row['word_limits']),
                    'structure_requirements': json.loads(row['structure_requirements']),
                    'formatting_rules': json.loads(row['formatting_rules']),
                    'language_variant': row['language_variant'],
                    'citation_style': row['citation_style'],
                    'special_requirements': json.loads(row['special_requirements'])
                }
            else:
                return self._get_default_journal_requirements()
    
    def _get_default_journal_requirements(self) -> Dict[str, Any]:
        """Return default journal requirements"""
        return {
            'publication_id': 0,
            'name': 'Generic Academic Journal',
            'type': 'journal',
            'word_limits': {'abstract': 200, 'main_text': 4000},
            'structure_requirements': {'abstract_format': 'IMRAD'},
            'formatting_rules': {'line_numbers': False, 'double_spaced': True},
            'language_variant': 'American English',
            'citation_style': 'APA',
            'special_requirements': []
        }
    
    def get_available_journals(self) -> List[Dict[str, Any]]:
        """Get list of all available journals"""
        with self.get_db_connection('journal_requirements') as conn:
            cursor = conn.execute("""
                SELECT publication_id, name, short_name, type, citation_style
                FROM publications ORDER BY name
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Activity Logging
    def log_activity(self, session_id: str, feature: str, action: str, metadata: Dict[str, Any] = None):
        """Log user activity"""
        with self.get_db_connection('users') as conn:
            conn.execute("""
                INSERT INTO activity_logs (session_id, feature_used, action_taken, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                feature,
                action,
                json.dumps(metadata or {}),
                datetime.now()
            ))
            conn.commit()
    
    def get_user_activity_stats(self, session_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user activity statistics"""
        since_date = datetime.now() - timedelta(days=days)
        
        with self.get_db_connection('users') as conn:
            # Total activities
            cursor = conn.execute("""
                SELECT COUNT(*) as total_activities
                FROM activity_logs 
                WHERE session_id = ? AND timestamp >= ?
            """, (session_id, since_date))
            total_activities = cursor.fetchone()['total_activities']
            
            # Feature usage
            cursor = conn.execute("""
                SELECT feature_used, COUNT(*) as count
                FROM activity_logs 
                WHERE session_id = ? AND timestamp >= ?
                GROUP BY feature_used
                ORDER BY count DESC
            """, (session_id, since_date))
            feature_usage = dict(cursor.fetchall())
            
            return {
                'total_activities': total_activities,
                'feature_usage': feature_usage,
                'period_days': days
            }
    
    # Figure Management
    def save_figure_upload(self, session_id: str, filename: str, file_path: str, 
                          original_specs: Dict[str, Any]) -> int:
        """Save figure upload information"""
        with self.get_db_connection('figures') as conn:
            cursor = conn.execute("""
                INSERT INTO user_figures (session_id, filename, file_path, original_specs, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                filename,
                file_path,
                json.dumps(original_specs),
                datetime.now()
            ))
            conn.commit()
            return cursor.lastrowid
    
    def save_figure_analysis(self, figure_id: int, analysis_results: Dict[str, Any]):
        """Save figure analysis results"""
        with self.get_db_connection('figures') as conn:
            conn.execute("""
                INSERT INTO figure_analysis (figure_id, analysis_results, analyzed_at)
                VALUES (?, ?, ?)
            """, (
                figure_id,
                json.dumps(analysis_results),
                datetime.now()
            ))
            conn.commit()
    
    def get_figure_info(self, figure_id: int) -> Optional[Dict[str, Any]]:
        """Get figure information by ID"""
        with self.get_db_connection('figures') as conn:
            cursor = conn.execute("""
                SELECT uf.*, fa.analysis_results, fa.analyzed_at
                FROM user_figures uf
                LEFT JOIN figure_analysis fa ON uf.figure_id = fa.figure_id
                WHERE uf.figure_id = ?
            """, (figure_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'figure_id': row['figure_id'],
                    'session_id': row['session_id'],
                    'filename': row['filename'],
                    'file_path': row['file_path'],
                    'original_specs': json.loads(row['original_specs']),
                    'uploaded_at': row['uploaded_at'],
                    'analysis_results': json.loads(row['analysis_results']) if row['analysis_results'] else None,
                    'analyzed_at': row['analyzed_at']
                }
            return None
    
    def get_user_figures(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's uploaded figures"""
        with self.get_db_connection('figures') as conn:
            cursor = conn.execute("""
                SELECT uf.*, fa.analysis_results, fa.analyzed_at
                FROM user_figures uf
                LEFT JOIN figure_analysis fa ON uf.figure_id = fa.figure_id
                WHERE uf.session_id = ?
                ORDER BY uf.uploaded_at DESC
                LIMIT ?
            """, (session_id, limit))
            
            return [
                {
                    'figure_id': row['figure_id'],
                    'filename': row['filename'],
                    'file_path': row['file_path'],
                    'original_specs': json.loads(row['original_specs']),
                    'uploaded_at': row['uploaded_at'],
                    'has_analysis': row['analysis_results'] is not None,
                    'analyzed_at': row['analyzed_at']
                }
                for row in cursor.fetchall()
            ]
    
    # Processing Jobs Management
    def create_processing_job(self, session_id: str, feature: str, input_data: Dict[str, Any], 
                            priority: int = 5) -> int:
        """Create a new processing job"""
        with self.get_db_connection('figures') as conn:  # Using figures db for job queue
            cursor = conn.execute("""
                INSERT INTO processing_jobs (session_id, job_type, input_data, status, priority, created_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
            """, (
                session_id,
                feature,
                json.dumps(input_data),
                priority,
                datetime.now()
            ))
            conn.commit()
            return cursor.lastrowid
    
    def update_job_status(self, job_id: int, status: str, result_data: Dict[str, Any] = None, 
                         error_message: str = None):
        """Update processing job status"""
        with self.get_db_connection('figures') as conn:
            if result_data:
                conn.execute("""
                    UPDATE processing_jobs 
                    SET status = ?, result_data = ?, completed_at = ?
                    WHERE job_id = ?
                """, (status, json.dumps(result_data), datetime.now(), job_id))
            elif error_message:
                conn.execute("""
                    UPDATE processing_jobs 
                    SET status = ?, error_message = ?, completed_at = ?
                    WHERE job_id = ?
                """, (status, error_message, datetime.now(), job_id))
            else:
                conn.execute("""
                    UPDATE processing_jobs 
                    SET status = ?, updated_at = ?
                    WHERE job_id = ?
                """, (status, datetime.now(), job_id))
            conn.commit()
    
    def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get processing job status"""
        with self.get_db_connection('figures') as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_jobs WHERE job_id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'job_id': row['job_id'],
                    'session_id': row['session_id'],
                    'job_type': row['job_type'],
                    'status': row['status'],
                    'input_data': json.loads(row['input_data']),
                    'result_data': json.loads(row['result_data']) if row['result_data'] else None,
                    'error_message': row['error_message'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'completed_at': row['completed_at']
                }
            return None
    
    def get_user_jobs(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's recent processing jobs"""
        with self.get_db_connection('figures') as conn:
            cursor = conn.execute("""
                SELECT job_id, job_type, status, created_at, completed_at, error_message
                FROM processing_jobs 
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Content Storage (for explain/rewrite feature)
    def save_rewrite_request(self, session_id: str, original_text: str, target_journal: str, 
                           rewritten_text: str, improvements: str, metadata: Dict[str, Any]) -> int:
        """Save explain/rewrite request and results"""
        # This would use research_papers_content.db when created
        # For now, log to activity
        self.log_activity(session_id, 'explain_rewrite', 'rewrite_completed', {
            'target_journal': target_journal,
            'original_length': len(original_text.split()),
            'rewritten_length': len(rewritten_text.split()),
            'improvements_count': len(improvements.split('\n')),
            **metadata
        })
        return 0  # Placeholder
    
    # Protocol Storage
    def save_protocol_optimization(self, session_id: str, original_protocol: str, 
                                 optimized_protocol: str, improvements: str, 
                                 metadata: Dict[str, Any]) -> int:
        """Save protocol optimization results"""
        self.log_activity(session_id, 'protocol_optimizer', 'optimization_completed', {
            'original_length': len(original_protocol.split()),
            'optimized_length': len(optimized_protocol.split()),
            **metadata
        })
        return 0  # Placeholder
    
    # Citation Analysis Storage
    def save_citation_analysis(self, session_id: str, analyzed_text: str, 
                             citation_results: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Save citation analysis results"""
        self.log_activity(session_id, 'citation_context', 'analysis_completed', {
            'text_length': len(analyzed_text.split()),
            'citations_found': metadata.get('citations_count', 0),
            'missing_citations': metadata.get('missing_citations_count', 0),
            **metadata
        })
        return 0  # Placeholder
    
    # Idea Recombination Storage
    def save_idea_recombination(self, session_id: str, sources: List[str], 
                              generated_ideas: str, metadata: Dict[str, Any]) -> int:
        """Save idea recombination results"""
        self.log_activity(session_id, 'idea_recombinator', 'ideas_generated', {
            'sources_count': len(sources),
            'ideas_generated': metadata.get('ideas_generated', 0),
            **metadata
        })
        return 0  # Placeholder
    
    # Contradiction Detection Storage
    def save_contradiction_analysis(self, session_id: str, analyzed_text: str, 
                                  contradictions: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Save contradiction analysis results"""
        self.log_activity(session_id, 'contradiction_detector', 'analysis_completed', {
            'text_length': len(analyzed_text.split()),
            'contradictions_found': metadata.get('contradictions_count', 0),
            'consistency_score': metadata.get('consistency_score'),
            **metadata
        })
        return 0  # Placeholder
    
    # Cleanup and Maintenance
    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up old anonymous sessions and their data"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with self.get_db_connection('users') as conn:
            # Get old session IDs
            cursor = conn.execute("""
                SELECT session_id FROM anonymous_sessions 
                WHERE last_activity < ?
            """, (cutoff_date,))
            old_sessions = [row['session_id'] for row in cursor.fetchall()]
            
            if old_sessions:
                # Delete activity logs
                placeholders = ','.join(['?' for _ in old_sessions])
                conn.execute(f"""
                    DELETE FROM activity_logs 
                    WHERE session_id IN ({placeholders})
                """, old_sessions)
                
                # Delete sessions
                conn.execute(f"""
                    DELETE FROM anonymous_sessions 
                    WHERE session_id IN ({placeholders})
                """, old_sessions)
                
                conn.commit()
                self.logger.info(f"Cleaned up {len(old_sessions)} old sessions")
        
        # Clean up old figures
        with self.get_db_connection('figures') as conn:
            conn.execute("""
                DELETE FROM user_figures 
                WHERE session_id IN (
                    SELECT session_id FROM anonymous_sessions 
                    WHERE last_activity < ?
                )
            """, (cutoff_date,))
            conn.commit()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        # Users database stats
        with self.get_db_connection('users') as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM anonymous_sessions")
            stats['anonymous_sessions'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM activity_logs")
            stats['total_activities'] = cursor.fetchone()[0]
        
        # Figures database stats
        try:
            with self.get_db_connection('figures') as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM user_figures")
                stats['uploaded_figures'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM processing_jobs")
                stats['processing_jobs'] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats['uploaded_figures'] = 0
            stats['processing_jobs'] = 0
        
        return stats
    
    def test_database_connections(self) -> Dict[str, bool]:
        """Test all database connections"""
        results = {}
        
        for db_name in self.databases:
            try:
                with self.get_db_connection(db_name) as conn:
                    conn.execute("SELECT 1")
                    results[db_name] = True
            except Exception as e:
                results[db_name] = False
                self.logger.error(f"Database {db_name} connection failed: {e}")
        
        return results
    
    def backup_database(self, db_name: str, backup_path: str):
        """Create backup of specific database"""
        if db_name not in self.databases:
            raise ValueError(f"Unknown database: {db_name}")
        
        import shutil
        shutil.copy2(self.databases[db_name], backup_path)
        self.logger.info(f"Database {db_name} backed up to {backup_path}")
    
    def get_feature_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get platform-wide feature usage statistics"""
        since_date = datetime.now() - timedelta(days=days)
        
        with self.get_db_connection('users') as conn:
            cursor = conn.execute("""
                SELECT feature_used, COUNT(*) as usage_count,
                       COUNT(DISTINCT session_id) as unique_users
                FROM activity_logs 
                WHERE timestamp >= ?
                GROUP BY feature_used
                ORDER BY usage_count DESC
            """, (since_date,))
            
            feature_stats = {}
            for row in cursor.fetchall():
                feature_stats[row['feature_used']] = {
                    'usage_count': row['usage_count'],
                    'unique_users': row['unique_users']
                }
            
            # Total stats
            cursor = conn.execute("""
                SELECT COUNT(*) as total_activities,
                       COUNT(DISTINCT session_id) as total_users
                FROM activity_logs 
                WHERE timestamp >= ?
            """, (since_date,))
            
            totals = cursor.fetchone()
            
            return {
                'period_days': days,
                'total_activities': totals['total_activities'],
                'total_unique_users': totals['total_users'],
                'feature_breakdown': feature_stats
            }

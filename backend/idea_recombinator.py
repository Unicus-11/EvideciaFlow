"""
Idea Recombinator Backend Handler
Synthesizes novel research ideas through AI-powered analysis of user interests and knowledge sources.
"""

import json
import logging
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse

from ai.ai_manager import AIManager
from backend.utils.database_helper import DatabaseHelper
from backend.utils.file_processor import FileProcessor


class IdeaRecombinator:
    """
    Handles the synthesis of novel research ideas through AI-powered recombination
    of user research interests and knowledge sources.
    """
    
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        self.logger = logging.getLogger(__name__)
        
    def process_idea_generation_request(self, form_data: Dict, files: Dict, user_id: str = None) -> Dict[str, Any]:
        """
        Main entry point for processing idea generation requests.
        
        Args:
            form_data: Form data from the frontend including interests, sources, options
            files: Uploaded files (research papers, documents)
            user_id: User ID if registered user, None for anonymous
        
        Returns:
            Dictionary containing processing results and generated ideas
        """
        try:
            # Generate session ID for anonymous users
            session_id = user_id if user_id else self.db_helper.create_anonymous_session()
            
            # Log activity
            self.db_helper.log_activity(session_id, 'idea_recombinator', 'request_started', {
                'has_files': len(files) > 0,
                'source_types': list(form_data.keys())
            })
            
            # Process research interests
            interests_result = self._process_research_interests(form_data.get('research_interests', ''), session_id, user_id)
            if not interests_result['success']:
                return self._error_response("Failed to process research interests", interests_result['error'])
            
            # Process knowledge sources
            sources_result = self._process_knowledge_sources(form_data, files, session_id, user_id)
            if not sources_result['success']:
                return self._error_response("Failed to process knowledge sources", sources_result['error'])
            
            # Create synthesis request
            synthesis_config = self._extract_synthesis_config(form_data)
            request_id = self._create_synthesis_request(session_id, user_id, synthesis_config)
            
            # Link sources and interests to the request
            self._link_request_data(request_id, interests_result['interest_ids'], sources_result['source_ids'])
            
            # Generate ideas using AI
            generation_result = self._generate_ideas(request_id, interests_result['interests'], 
                                                   sources_result['sources'], synthesis_config)
            
            if generation_result['success']:
                # Save generated ideas to database
                self._save_generated_ideas(request_id, generation_result['ideas'])
                
                # Update request status
                self._update_synthesis_status(request_id, 'completed')
                
                # Log successful completion
                self.db_helper.log_activity(session_id, 'idea_recombinator', 'ideas_generated', {
                    'ideas_count': len(generation_result['ideas']),
                    'creativity_level': synthesis_config['creativity_level'],
                    'synthesis_methods': synthesis_config['synthesis_methods']
                })
                
                return {
                    'success': True,
                    'request_id': request_id,
                    'ideas': generation_result['ideas'],
                    'metadata': generation_result.get('metadata', {}),
                    'processing_time': generation_result.get('processing_time', 0)
                }
            else:
                self._update_synthesis_status(request_id, 'failed', generation_result.get('error'))
                return self._error_response("AI idea generation failed", generation_result.get('error'))
                
        except Exception as e:
            self.logger.error(f"Idea generation request failed: {e}")
            return self._error_response("Request processing failed", str(e))
    
    def _process_research_interests(self, interests_string: str, session_id: str, user_id: str = None) -> Dict[str, Any]:
        """Process and save research interests from form data"""
        try:
            if not interests_string or not interests_string.strip():
                return {'success': False, 'error': 'No research interests provided'}
            
            # Parse interests (assuming comma-separated or JSON array)
            interests = []
            try:
                # Try parsing as JSON first
                parsed_interests = json.loads(interests_string)
                if isinstance(parsed_interests, list):
                    interests = [str(interest).strip() for interest in parsed_interests if str(interest).strip()]
                else:
                    interests = [str(interests_string).strip()]
            except json.JSONDecodeError:
                # Fall back to comma separation
                interests = [interest.strip() for interest in interests_string.split(',') if interest.strip()]
            
            if not interests:
                return {'success': False, 'error': 'No valid research interests found'}
            
            interest_ids = []
            processed_interests = []
            
            with self.db_helper.get_db_connection('knowledge_base') as conn:
                for interest_text in interests:
                    # Categorize interest (simple heuristic-based categorization)
                    category = self._categorize_interest(interest_text)
                    
                    # Save to database
                    cursor = conn.execute("""
                        INSERT INTO research_interests (session_id, user_id, interest_text, category, weight)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, user_id, interest_text, category, 1.0))
                    
                    interest_id = cursor.lastrowid
                    interest_ids.append(interest_id)
                    processed_interests.append({
                        'id': interest_id,
                        'text': interest_text,
                        'category': category,
                        'weight': 1.0
                    })
                
                conn.commit()
            
            return {
                'success': True,
                'interest_ids': interest_ids,
                'interests': processed_interests,
                'count': len(interests)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing research interests: {e}")
            return {'success': False, 'error': str(e)}
    
    def _categorize_interest(self, interest_text: str) -> str:
        """Categorize research interest based on keywords"""
        text_lower = interest_text.lower()
        
        methodology_keywords = ['learning', 'analysis', 'method', 'approach', 'technique', 'algorithm', 'framework']
        domain_keywords = ['medicine', 'healthcare', 'biology', 'physics', 'chemistry', 'engineering', 'psychology']
        application_keywords = ['in', 'for', 'application', 'applied', 'clinical', 'industrial']
        
        if any(keyword in text_lower for keyword in methodology_keywords):
            return 'methodology'
        elif any(keyword in text_lower for keyword in domain_keywords):
            return 'domain'
        elif any(keyword in text_lower for keyword in application_keywords):
            return 'application'
        else:
            return 'general'
    
    def _process_knowledge_sources(self, form_data: Dict, files: Dict, session_id: str, user_id: str = None) -> Dict[str, Any]:
        """Process and save knowledge sources from various inputs"""
        try:
            source_ids = []
            processed_sources = []
            
            with self.db_helper.get_db_connection('knowledge_base') as conn:
                # Process uploaded files
                if files:
                    file_results = self._process_uploaded_files(files, session_id, user_id, conn)
                    source_ids.extend(file_results['source_ids'])
                    processed_sources.extend(file_results['sources'])
                
                # Process web sources (URLs)
                web_sources = form_data.get('web_sources', '').strip()
                if web_sources:
                    url_results = self._process_web_sources(web_sources, session_id, user_id, conn)
                    source_ids.extend(url_results['source_ids'])
                    processed_sources.extend(url_results['sources'])
                
                # Process current projects description
                current_projects = form_data.get('current_projects', '').strip()
                if current_projects:
                    project_results = self._process_project_description(current_projects, session_id, user_id, conn)
                    source_ids.extend(project_results['source_ids'])
                    processed_sources.extend(project_results['sources'])
                
                conn.commit()
            
            if not source_ids:
                return {'success': False, 'error': 'No valid knowledge sources provided'}
            
            return {
                'success': True,
                'source_ids': source_ids,
                'sources': processed_sources,
                'count': len(source_ids)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing knowledge sources: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_uploaded_files(self, files: Dict, session_id: str, user_id: str, conn) -> Dict[str, Any]:
        """Process uploaded research files"""
        source_ids = []
        sources = []
        
        for field_name, file_data in files.items():
            if field_name == 'source_files' and hasattr(file_data, 'read'):
                # Handle file upload
                filename = getattr(file_data, 'filename', 'unknown_file.pdf')
                file_content = file_data.read()
                
                # Save file using file processor
                save_success, file_path, file_info = self.file_processor.save_uploaded_file(
                    file_content, filename, session_id, 'paper'
                )
                
                if save_success:
                    # Extract text content
                    text_success, extracted_text, extraction_metadata = self.file_processor.extract_text_from_file(file_path)
                    
                    # Save to knowledge sources
                    cursor = conn.execute("""
                        INSERT INTO knowledge_sources 
                        (session_id, user_id, source_type, title, content, file_path, 
                         file_metadata, word_count, processing_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, user_id, 'file', filename,
                        extracted_text if text_success else '',
                        file_path,
                        json.dumps({**file_info, **extraction_metadata}),
                        extraction_metadata.get('word_count', 0) if text_success else 0,
                        'processed' if text_success else 'failed'
                    ))
                    
                    source_id = cursor.lastrowid
                    source_ids.append(source_id)
                    sources.append({
                        'id': source_id,
                        'type': 'file',
                        'title': filename,
                        'content': extracted_text if text_success else '',
                        'word_count': extraction_metadata.get('word_count', 0) if text_success else 0,
                        'status': 'processed' if text_success else 'failed'
                    })
        
        return {'source_ids': source_ids, 'sources': sources}
    
    def _process_web_sources(self, web_sources_text: str, session_id: str, user_id: str, conn) -> Dict[str, Any]:
        """Process web URLs as knowledge sources"""
        source_ids = []
        sources = []
        
        # Extract URLs from text
        urls = self._extract_urls(web_sources_text)
        
        for url in urls:
            try:
                # Validate URL
                parsed_url = urlparse(url)
                if not all([parsed_url.scheme, parsed_url.netloc]):
                    continue
                
                # For now, save URL info (actual web scraping would require additional libraries)
                cursor = conn.execute("""
                    INSERT INTO knowledge_sources 
                    (session_id, user_id, source_type, title, url, content, 
                     processing_status, processing_error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, user_id, 'url', f"Web Source: {parsed_url.netloc}", url,
                    f"Source URL: {url}\nNote: Content extraction from URLs requires web scraping implementation.",
                    'pending', 'Web content extraction not yet implemented'
                ))
                
                source_id = cursor.lastrowid
                source_ids.append(source_id)
                sources.append({
                    'id': source_id,
                    'type': 'url',
                    'title': f"Web Source: {parsed_url.netloc}",
                    'url': url,
                    'content': f"URL reference: {url}",
                    'status': 'pending'
                })
                
            except Exception as e:
                self.logger.warning(f"Failed to process URL {url}: {e}")
                continue
        
        return {'source_ids': source_ids, 'sources': sources}
    
    def _process_project_description(self, project_text: str, session_id: str, user_id: str, conn) -> Dict[str, Any]:
        """Process current project description as a knowledge source"""
        if not project_text or len(project_text.strip()) < 10:
            return {'source_ids': [], 'sources': []}
        
        word_count = len(project_text.split())
        
        cursor = conn.execute("""
            INSERT INTO knowledge_sources 
            (session_id, user_id, source_type, title, content, word_count, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, user_id, 'text', 'Current Research Projects',
            project_text, word_count, 'processed'
        ))
        
        source_id = cursor.lastrowid
        
        return {
            'source_ids': [source_id],
            'sources': [{
                'id': source_id,
                'type': 'text',
                'title': 'Current Research Projects',
                'content': project_text,
                'word_count': word_count,
                'status': 'processed'
            }]
        }
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        urls = url_pattern.findall(text)
        
        # Also try to find URLs that start with www.
        www_pattern = re.compile(r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        www_urls = ['http://' + url for url in www_pattern.findall(text)]
        
        return list(set(urls + www_urls))
    
    def _extract_synthesis_config(self, form_data: Dict) -> Dict[str, Any]:
        """Extract synthesis configuration from form data"""
        return {
            'synthesis_methods': form_data.getlist('synthesis_methods') if hasattr(form_data, 'getlist') 
                               else form_data.get('synthesis_methods', []),
            'innovation_focus': form_data.getlist('innovation_focus') if hasattr(form_data, 'getlist')
                              else form_data.get('innovation_focus', []),
            'creativity_level': form_data.get('creativity_level', 'moderate'),
            'target_domain': form_data.get('target_domain', ''),
            'idea_count': int(form_data.get('idea_count', 5))
        }
    
    def _create_synthesis_request(self, session_id: str, user_id: str, config: Dict[str, Any]) -> int:
        """Create synthesis request in database"""
        with self.

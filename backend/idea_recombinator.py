"""
Idea Recombinator Backend Handler
Synthesizes novel research ideas through AI-powered analysis of user interests and knowledge sources.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from backend.utils.database_helper import DatabaseHelper
from backend.utils.file_processor import FileProcessor
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai.ai_manager import AIManager


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

    # -------------------- Public --------------------
    def process_idea_generation_request(self, form_data: Dict, files: Dict, user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            session_id = user_id or self.db_helper.create_anonymous_session()

            self.db_helper.log_activity(session_id, 'idea_recombinator', 'request_started', {
                'has_files': bool(files),
                'source_types': list(form_data.keys())
            })

            # Process interests
            interests_result = self._process_research_interests(form_data.get('research_interests', ''), session_id, user_id)
            if not interests_result['success']:
                return self._error_response("Failed to process research interests", interests_result['error'])

            # Process sources
            sources_result = self._process_knowledge_sources(form_data, files, session_id, user_id)
            if not sources_result['success']:
                return self._error_response("Failed to process knowledge sources", sources_result['error'])

            # Synthesis config
            synthesis_config = self._extract_synthesis_config(form_data)

            # Create request in DB
            request_id = self._create_synthesis_request(session_id, user_id, synthesis_config, sources_result['source_ids'])

            # Generate ideas
            generation_result = self._generate_ideas(request_id, interests_result['interests'], sources_result['sources'], synthesis_config)

            if generation_result['success']:
                self._save_generated_ideas(request_id, generation_result['ideas'])
                self._update_synthesis_status(request_id, 'completed')

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

    # -------------------- Private Helpers --------------------
    def _process_research_interests(self, interests_string: str, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            if not interests_string.strip():
                return {'success': False, 'error': 'No research interests provided'}

            try:
                parsed = json.loads(interests_string)
                interests = [str(i).strip() for i in parsed if str(i).strip()] if isinstance(parsed, list) else [interests_string.strip()]
            except json.JSONDecodeError:
                interests = [i.strip() for i in interests_string.split(',') if i.strip()]

            if not interests:
                return {'success': False, 'error': 'No valid research interests found'}

            interest_ids = []
            processed_interests = []

            with self.db_helper.get_db_connection('knowledge_base') as conn:
                for interest in interests:
                    category = self._categorize_interest(interest)
                    cursor = conn.execute("""
                        INSERT INTO research_interests (session_id, user_id, interest_text, category, weight)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, user_id, interest, category, 1.0))
                    interest_id = cursor.lastrowid
                    interest_ids.append(interest_id)
                    processed_interests.append({'id': interest_id, 'text': interest, 'category': category, 'weight': 1.0})

                conn.commit()

            return {'success': True, 'interest_ids': interest_ids, 'interests': processed_interests, 'count': len(interests)}
        except Exception as e:
            self.logger.error(f"Error processing research interests: {e}")
            return {'success': False, 'error': str(e)}

    def _categorize_interest(self, interest_text: str) -> str:
        text = interest_text.lower()
        methodology = ['learning', 'analysis', 'method', 'approach', 'technique', 'algorithm', 'framework']
        domain = ['medicine', 'healthcare', 'biology', 'physics', 'chemistry', 'engineering', 'psychology']
        application = ['in', 'for', 'application', 'applied', 'clinical', 'industrial']

        if any(k in text for k in methodology):
            return 'methodology'
        if any(k in text for k in domain):
            return 'domain'
        if any(k in text for k in application):
            return 'application'
        return 'general'

    def _process_knowledge_sources(self, form_data: Dict, files: Dict, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        source_ids = []
        processed_sources = []

        with self.db_helper.get_db_connection('knowledge_base') as conn:
            if files:
                file_results = self._process_uploaded_files(files, session_id, user_id, conn)
                source_ids.extend(file_results['source_ids'])
                processed_sources.extend(file_results['sources'])

            web_sources = form_data.get('web_sources', '').strip()
            if web_sources:
                url_results = self._process_web_sources(web_sources, session_id, user_id, conn)
                source_ids.extend(url_results['source_ids'])
                processed_sources.extend(url_results['sources'])

            current_projects = form_data.get('current_projects', '').strip()
            if current_projects:
                proj_results = self._process_project_description(current_projects, session_id, user_id, conn)
                source_ids.extend(proj_results['source_ids'])
                processed_sources.extend(proj_results['sources'])

            conn.commit()

        if not source_ids:
            return {'success': False, 'error': 'No valid knowledge sources provided'}

        return {'success': True, 'source_ids': source_ids, 'sources': processed_sources, 'count': len(source_ids)}

    def _process_uploaded_files(self, files: Dict, session_id: str, user_id: Optional[str], conn) -> Dict[str, Any]:
        source_ids = []
        sources = []

        for name, file_data in files.items():
            if hasattr(file_data, 'read'):
                filename = getattr(file_data, 'filename', 'unknown.pdf')
                content = file_data.read()
                save_success, path, file_info = self.file_processor.save_uploaded_file(content, filename, session_id, 'paper')

                if save_success:
                    text_success, extracted_text, meta = self.file_processor.extract_text_from_file(path)
                    cursor = conn.execute("""
                        INSERT INTO knowledge_sources
                        (session_id, user_id, source_type, title, content, file_path, file_metadata, word_count, processing_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (session_id, user_id, 'file', filename,
                          extracted_text if text_success else '',
                          path, json.dumps({**file_info, **meta}),
                          meta.get('word_count', 0) if text_success else 0,
                          'processed' if text_success else 'failed'))
                    source_id = cursor.lastrowid
                    source_ids.append(source_id)
                    sources.append({'id': source_id, 'type': 'file', 'title': filename, 'content': extracted_text if text_success else '', 'word_count': meta.get('word_count', 0), 'status': 'processed' if text_success else 'failed'})

        return {'source_ids': source_ids, 'sources': sources}

    def _process_web_sources(self, text: str, session_id: str, user_id: Optional[str], conn) -> Dict[str, Any]:
        urls = self._extract_urls(text)
        source_ids = []
        sources = []

        for url in urls:
            try:
                parsed_url = urlparse(url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    continue
                cursor = conn.execute("""
                    INSERT INTO knowledge_sources
                    (session_id, user_id, source_type, title, url, content, processing_status, processing_error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, user_id, 'url', f"Web Source: {parsed_url.netloc}", url,
                      f"Reference URL: {url}. Extraction not implemented.", 'pending', 'Web extraction not implemented'))
                source_id = cursor.lastrowid
                source_ids.append(source_id)
                sources.append({'id': source_id, 'type': 'url', 'title': f"Web Source: {parsed_url.netloc}", 'url': url, 'content': f"Reference URL: {url}", 'status': 'pending'})
            except Exception as e:
                self.logger.warning(f"Failed to process URL {url}: {e}")

        return {'source_ids': source_ids, 'sources': sources}

    def _process_project_description(self, text: str, session_id: str, user_id: Optional[str], conn) -> Dict[str, Any]:
        if not text or len(text.strip()) < 10:
            return {'source_ids': [], 'sources': []}

        word_count = len(text.split())
        cursor = conn.execute("""
            INSERT INTO knowledge_sources (session_id, user_id, source_type, title, content, word_count, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, 'text', 'Current Research Projects', text, word_count, 'processed'))
        source_id = cursor.lastrowid

        return {'source_ids': [source_id], 'sources': [{'id': source_id, 'type': 'text', 'title': 'Current Research Projects', 'content': text, 'word_count': word_count, 'status': 'processed'}]}

    def _extract_urls(self, text: str) -> List[str]:
        urls = re.findall(r'http[s]?://[^\s]+', text)
        urls += ['http://' + u for u in re.findall(r'www\.[^\s]+', text)]
        return list(set(urls))

    def _extract_synthesis_config(self, form_data: Dict) -> Dict[str, Any]:
        return {
            'synthesis_methods': form_data.get('synthesis_methods', []),
            'innovation_focus': form_data.get('innovation_focus', []),
            'creativity_level': form_data.get('creativity_level', 'moderate'),
            'target_domain': form_data.get('target_domain', ''),
            'idea_count': int(form_data.get('idea_count', 5))
        }

    def _create_synthesis_request(self, session_id: str, user_id: Optional[str], config: Dict[str, Any], source_ids: List[int]) -> int:
        with self.db_helper.get_db_connection('knowledge_base') as conn:
            cursor = conn.execute("""
                INSERT INTO synthesis_requests (session_id, user_id, config, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, user_id, json.dumps(config), 'processing', datetime.now().isoformat()))
            request_id = cursor.lastrowid
            for sid in source_ids:
                conn.execute("INSERT INTO request_sources (request_id, source_id) VALUES (?, ?)", (request_id, sid))
            conn.commit()
            return request_id

    def _generate_ideas(self, request_id: int, interests: List[Dict], sources: List[Dict], config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            start = datetime.now()
            ai_resp = self.ai_manager.process_request('idea_recombinator', {'interests': interests, 'sources': sources, 'config': config})
            elapsed = (datetime.now() - start).total_seconds()

            if ai_resp['success']:
                return {'success': True, 'ideas': ai_resp['result'].get('novel_ideas', []), 'metadata': ai_resp['result'].get('metadata', {}), 'processing_time': elapsed}
            else:
                return {'success': False, 'error': ai_resp.get('error', 'AI failed'), 'processing_time': elapsed}
        except Exception as e:
            self.logger.error(f"AI generation error: {e}")
            return {'success': False, 'error': str(e)}

    def _save_generated_ideas(self, request_id: int, ideas: List[Dict]):
        with self.db_helper.get_db_connection('knowledge_base') as conn:
            for idx, idea in enumerate(ideas):
                conn.execute("""
                    INSERT INTO generated_ideas 
                    (request_id, idea_order, title, description, methodology, feasibility_score, novelty_score, impact_score, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request_id, idx + 1,
                    idea.get('title', ''),
                    idea.get('description', ''),
                    idea.get('methodology', ''),
                    idea.get('feasibility_score', 0.0),
                    idea.get('novelty_score', 0.0),
                    idea.get('impact_score', 0.0),
                    json.dumps(idea.get('metadata', {}))
                ))
            conn.commit()

    def _update_synthesis_status(self, request_id: int, status: str, error: Optional[str] = None):
        with self.db_helper.get_db_connection('knowledge_base') as conn:
            conn.execute("""
                UPDATE synthesis_requests SET status = ?, error_message = ? WHERE id = ?
            """, (status, error, request_id))
            conn.commit()

    def _error_response(self, message: str, error: Optional[str] = None) -> Dict[str, Any]:
        return {'success': False, 'error': error or message}


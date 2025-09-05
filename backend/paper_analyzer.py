"""
Paper Analyzer Backend Handler
Coordinates all analysis tools for comprehensive research paper processing.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from backend.utils.database_helper import DatabaseHelper
from backend.utils.file_processor import FileProcessor


class PaperAnalyzer:
    """
    Main handler for comprehensive paper analysis using all available tools.
    Coordinates between different analysis features and manages results.
    """
    
    def __init__(self, ai_manager=None):
        self.ai_manager = ai_manager
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        self.logger = logging.getLogger(__name__)
        
        # Define available analysis tools
        self.available_tools = {
            'polish': {
                'feature': 'explain_rewrite',
                'name': 'Paper Polisher',
                'description': 'Improve writing style, grammar, and academic tone'
            },
            'figure': {
                'feature': 'figure_fixer',
                'name': 'Figure Fixer',
                'description': 'Enhance figures and charts with better formatting'
            },
            'citation': {
                'feature': 'citation_context',
                'name': 'Smart Citation',
                'description': 'Optimize citations and references'
            },
            'claim': {
                'feature': 'contradiction_detector',
                'name': 'Claim Checker',
                'description': 'Detect contradictions and verify claims'
            },
            'protocol': {
                'feature': 'protocol_optimizer',
                'name': 'Protocol Optimizer',
                'description': 'Improve methodology and experimental protocols'
            }
        }
    
    def analyze_paper(self, paper_file, user_id: str = None) -> Dict[str, Any]:
        """
        Initial paper analysis and setup for tool processing.
        
        Args:
            paper_file: Uploaded paper file object
            user_id: User session ID
            
        Returns:
            Dict containing analysis ID, extracted content, and metadata
        """
        try:
            # Generate analysis session
            analysis_id = str(uuid.uuid4())
            session_id = user_id if user_id else self.db_helper.create_anonymous_session()
            
            # Log analysis start
            self.db_helper.log_activity(session_id, 'paper_analyzer', 'analysis_started', {
                'analysis_id': analysis_id,
                'filename': getattr(paper_file, 'filename', 'unknown.pdf')
            })
            
            # Process uploaded file
            filename = getattr(paper_file, 'filename', 'uploaded_paper.pdf')
            file_content = paper_file.read()
            
            # Save file temporarily
            save_success, file_path, file_info = self.file_processor.save_uploaded_file(
                file_content, filename, session_id, 'analysis'
            )
            
            if not save_success:
                return self._error_response("Failed to save uploaded file", file_info.get('error'))
            
            # Extract text content
            text_success, extracted_text, extraction_metadata = self.file_processor.extract_text_from_file(file_path)
            
            if not text_success:
                return self._error_response("Failed to extract text from PDF", extraction_metadata.get('error'))
            
            # Store analysis data in database
            analysis_data = {
                'analysis_id': analysis_id,
                'session_id': session_id,
                'user_id': user_id,
                'filename': filename,
                'file_path': file_path,
                'extracted_text': extracted_text,
                'word_count': extraction_metadata.get('word_count', 0),
                'page_count': extraction_metadata.get('page_count', 0),
                'file_size': len(file_content),
                'created_at': datetime.now().isoformat(),
                'status': 'ready'
            }
            
            # Save to database
            self._save_analysis_data(analysis_data)
            
            # Parse paper structure for better tool targeting
            paper_structure = self._analyze_paper_structure(extracted_text)
            
            return {
                'success': True,
                'analysis_id': analysis_id,
                'metadata': {
                    'filename': filename,
                    'word_count': extraction_metadata.get('word_count', 0),
                    'page_count': extraction_metadata.get('page_count', 0),
                    'file_size_mb': round(len(file_content) / (1024 * 1024), 2),
                    'structure': paper_structure
                },
                'available_tools': list(self.available_tools.keys()),
                'processing_time': extraction_metadata.get('processing_time', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Paper analysis failed: {e}")
            return self._error_response("Analysis failed", str(e))
    
    def run_analysis_tool(self, analysis_id: str, tool_name: str, tool_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run a specific analysis tool on the processed paper.
        
        Args:
            analysis_id: ID of the analysis session
            tool_name: Name of the tool to run (polish, figure, citation, claim, protocol)
            tool_config: Configuration parameters for the tool
            
        Returns:
            Dict containing tool results and processing information
        """
        try:
            if not self.ai_manager:
                return self._error_response("AI Manager not available", "AI processing is currently unavailable")
            
            if tool_name not in self.available_tools:
                return self._error_response("Invalid tool", f"Tool '{tool_name}' not available")
            
            # Retrieve analysis data
            analysis_data = self._get_analysis_data(analysis_id)
            if not analysis_data:
                return self._error_response("Analysis not found", f"No analysis found with ID: {analysis_id}")
            
            # Prepare tool-specific data
            tool_data = self._prepare_tool_data(analysis_data, tool_name, tool_config or {})
            
            # Get the feature name for AI Manager
            feature_name = self.available_tools[tool_name]['feature']
            
            # Log tool execution start
            self.db_helper.log_activity(analysis_data['session_id'], 'paper_analyzer', f'{tool_name}_started', {
                'analysis_id': analysis_id,
                'tool': tool_name,
                'feature': feature_name
            })
            
            # Process with AI Manager
            ai_result = self.ai_manager.process_request(
                feature=feature_name,
                data=tool_data,
                session_id=analysis_data['session_id']
            )
            
            if ai_result['success']:
                # Process and format results for frontend
                formatted_result = self._format_tool_result(tool_name, ai_result['result'])
                
                # Save results to database
                self._save_tool_result(analysis_id, tool_name, formatted_result, ai_result)
                
                # Log successful completion
                self.db_helper.log_activity(analysis_data['session_id'], 'paper_analyzer', f'{tool_name}_completed', {
                    'analysis_id': analysis_id,
                    'tool': tool_name,
                    'success': True
                })
                
                return {
                    'success': True,
                    'tool': tool_name,
                    'data': formatted_result,
                    'processing_time': ai_result.get('processing_time', 0),
                    'analysis_id': analysis_id
                }
            else:
                error_msg = ai_result.get('error', 'Unknown AI processing error')
                self.logger.error(f"AI processing failed for {tool_name}: {error_msg}")
                
                # Log failed completion
                self.db_helper.log_activity(analysis_data['session_id'], 'paper_analyzer', f'{tool_name}_failed', {
                    'analysis_id': analysis_id,
                    'tool': tool_name,
                    'error': error_msg
                })
                
                return self._error_response(f"{tool_name} processing failed", error_msg)
                
        except Exception as e:
            self.logger.error(f"Tool execution failed for {tool_name}: {e}")
            return self._error_response("Tool execution failed", str(e))
    
    def _analyze_paper_structure(self, text: str) -> Dict[str, Any]:
        """Analyze paper structure to identify sections and content types."""
        structure = {
            'has_abstract': 'abstract' in text.lower(),
            'has_introduction': 'introduction' in text.lower(),
            'has_methods': any(word in text.lower() for word in ['method', 'methodology', 'materials']),
            'has_results': 'results' in text.lower(),
            'has_discussion': 'discussion' in text.lower(),
            'has_conclusion': 'conclusion' in text.lower(),
            'has_references': any(word in text.lower() for word in ['references', 'bibliography', 'citations']),
            'has_figures': any(word in text.lower() for word in ['figure', 'fig.', 'chart', 'graph']),
            'sections_detected': []
        }
        
        # Detect common section headers
        common_sections = [
            'abstract', 'introduction', 'literature review', 'methodology', 'methods',
            'results', 'discussion', 'conclusion', 'references', 'appendix'
        ]
        
        for section in common_sections:
            if section in text.lower():
                structure['sections_detected'].append(section)
        
        return structure
    
    def _prepare_tool_data(self, analysis_data: Dict[str, Any], tool_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for specific analysis tools based on their requirements."""
        base_data = {
            'text': analysis_data['extracted_text'],
            'filename': analysis_data['filename'],
            'analysis_id': analysis_data['analysis_id']
        }
        
        # Tool-specific data preparation
        if tool_name == 'polish':
            return {
                **base_data,
                'target_journal': config.get('target_journal', 'General Academic'),
                'language': config.get('language', 'American English'),
                'creativity_level': config.get('creativity_level', 'moderate'),
                'focus_areas': config.get('focus_areas', ['grammar', 'style', 'clarity'])
            }
        
        elif tool_name == 'figure':
            return {
                **base_data,
                'figure_description': self._extract_figure_descriptions(analysis_data['extracted_text']),
                'target_journal': config.get('target_journal', 'General Academic'),
                'current_specs': config.get('current_specs', {}),
                'style_preferences': config.get('style', 'academic')
            }
        
        elif tool_name == 'citation':
            return {
                **base_data,
                'citation_style': config.get('citation_style', 'APA'),
                'check_context': config.get('check_context', True),
                'target_journal': config.get('target_journal', 'General Academic')
            }
        
        elif tool_name == 'claim':
            return {
                **base_data,
                'check_type': config.get('check_type', 'comprehensive'),
                'depth': config.get('depth', 'thorough'),
                'sources': config.get('sources', 'comprehensive'),
                'focus_sections': config.get('focus_sections', ['results', 'discussion', 'conclusion'])
            }
        
        elif tool_name == 'protocol':
            return {
                **base_data,
                'protocol_text': self._extract_methods_section(analysis_data['extracted_text']),
                'research_field': config.get('research_field', 'General'),
                'focus': config.get('focus', 'reproducibility'),
                'optimization_goals': config.get('optimization_goals', ['efficiency', 'reproducibility'])
            }
        
        return base_data
    
    def _extract_figure_descriptions(self, text: str) -> str:
        """Extract figure descriptions and captions from paper text."""
        figure_sections = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(word in line_lower for word in ['figure', 'fig.', 'chart', 'graph', 'table']):
                figure_sections.append(line.strip())
        
        return '\n'.join(figure_sections) if figure_sections else "No figure descriptions found in paper."
    
    def _extract_methods_section(self, text: str) -> str:
        """Extract methodology/methods section from paper text."""
        lines = text.split('\n')
        methods_section = []
        in_methods = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Start of methods section
            if any(word in line_lower for word in ['method', 'methodology', 'materials']):
                in_methods = True
                methods_section.append(line)
                continue
            
            # End of methods section (start of results)
            if in_methods and any(word in line_lower for word in ['result', 'finding', 'discussion']):
                break
            
            if in_methods:
                methods_section.append(line)
        
        return '\n'.join(methods_section) if methods_section else text[:2000]  # Fallback to first part of paper
    
    def _format_tool_result(self, tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format AI tool results for frontend display."""
        formatted = {
            'tool': tool_name,
            'timestamp': datetime.now().isoformat(),
            'result': result
        }
        
        # Tool-specific formatting for better UI display
        if tool_name == 'polish':
            formatted['html'] = self._format_rewrite_html(result)
        elif tool_name == 'figure':
            formatted['html'] = self._format_figure_html(result)
        elif tool_name == 'citation':
            formatted['html'] = self._format_citation_html(result)
        elif tool_name == 'claim':
            formatted['html'] = self._format_claim_html(result)
        elif tool_name == 'protocol':
            formatted['html'] = self._format_protocol_html(result)
        
        return formatted
    
    def _format_rewrite_html(self, result: Dict[str, Any]) -> str:
        """Format paper polisher results for HTML display."""
        html = f"""
        <div class="rewrite-results">
            <h4>📝 Writing Improvements</h4>
            <div class="improvement-summary">
                <p><strong>Word Count:</strong> {result.get('word_count', 'N/A')}</p>
                <p><strong>Target Journal:</strong> {result.get('target_journal', 'N/A')}</p>
                <p><strong>Language:</strong> {result.get('language', 'N/A')}</p>
            </div>
            
            <div class="improvements-list">
                <h5>Key Improvements:</h5>
                <ul>
        """
        
        improvements = result.get('improvements', [])
        if isinstance(improvements, list):
            for improvement in improvements[:5]:  # Limit to top 5
                html += f"<li>{improvement}</li>"
        elif isinstance(improvements, str):
            html += f"<li>{improvements}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="rewritten-content">
                <h5>Enhanced Content Preview:</h5>
                <div class="content-preview">
        """
        
        rewritten = result.get('rewritten_text', '')
        if rewritten:
            # Show first 500 characters as preview
            preview = rewritten[:500] + "..." if len(rewritten) > 500 else rewritten
            html += f"<p>{preview}</p>"
        else:
            html += "<p>Rewritten content available for download.</p>"
        
        html += """
                </div>
            </div>
        </div>
        """
        
        return html
    
    def _format_figure_html(self, result: Dict[str, Any]) -> str:
        """Format figure fixer results for HTML display."""
        html = f"""
        <div class="figure-results">
            <h4>🎨 Figure Analysis</h4>
            <div class="analysis-summary">
                <p><strong>Target Journal:</strong> {result.get('target_journal', 'N/A')}</p>
            </div>
            
            <div class="issues-found">
                <h5>Issues Identified:</h5>
                <ul>
        """
        
        issues = result.get('issues_found', [])
        if isinstance(issues, list):
            for issue in issues:
                html += f"<li>{issue}</li>"
        elif isinstance(issues, str):
            html += f"<li>{issues}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="recommendations">
                <h5>Recommendations:</h5>
                <div class="recommendations-content">
        """
        
        recommendations = result.get('recommendations', '')
        if recommendations:
            html += f"<p>{recommendations}</p>"
        else:
            html += "<p>No specific recommendations available.</p>"
        
        html += """
                </div>
            </div>
        </div>
        """
        
        return html
    
    def _format_citation_html(self, result: Dict[str, Any]) -> str:
        """Format citation analysis results for HTML display."""
        html = f"""
        <div class="citation-results">
            <h4>📚 Citation Analysis</h4>
            <div class="citation-summary">
                <p><strong>Style:</strong> {result.get('citation_style', 'N/A')}</p>
                <p><strong>Citations Found:</strong> {len(result.get('citations_found', []))}</p>
                <p><strong>Missing Citations:</strong> {len(result.get('missing_citations', []))}</p>
            </div>
            
            <div class="style-issues">
                <h5>Style Issues:</h5>
                <ul>
        """
        
        issues = result.get('style_issues', [])
        if isinstance(issues, list):
            for issue in issues[:10]:  # Limit to top 10
                html += f"<li>{issue}</li>"
        elif isinstance(issues, str):
            html += f"<li>{issues}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="missing-citations">
                <h5>Suggested Citations:</h5>
                <ul>
        """
        
        missing = result.get('missing_citations', [])
        if isinstance(missing, list):
            for citation in missing[:5]:  # Limit to top 5
                html += f"<li>{citation}</li>"
        elif isinstance(missing, str):
            html += f"<li>{missing}</li>"
        
        html += """
                </ul>
            </div>
        </div>
        """
        
        return html
    
    def _format_claim_html(self, result: Dict[str, Any]) -> str:
        """Format contradiction detection results for HTML display."""
        html = f"""
        <div class="claim-results">
            <h4>🔍 Claim Analysis</h4>
            <div class="consistency-score">
                <p><strong>Consistency Score:</strong> {result.get('consistency_score', 'N/A')}/10</p>
                <p><strong>Check Type:</strong> {result.get('check_type', 'N/A')}</p>
            </div>
            
            <div class="contradictions">
                <h5>Contradictions Found:</h5>
                <ul>
        """
        
        contradictions = result.get('contradictions', [])
        if isinstance(contradictions, list):
            for contradiction in contradictions:
                html += f"<li><strong>Issue:</strong> {contradiction}</li>"
        elif isinstance(contradictions, str) and contradictions:
            html += f"<li>{contradictions}</li>"
        else:
            html += "<li>No significant contradictions detected.</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="recommendations">
                <h5>Recommendations:</h5>
                <div class="recommendations-content">
        """
        
        recommendations = result.get('recommendations', '')
        if recommendations:
            html += f"<p>{recommendations}</p>"
        else:
            html += "<p>Paper appears logically consistent.</p>"
        
        html += """
                </div>
            </div>
        </div>
        """
        
        return html
    
    def _format_protocol_html(self, result: Dict[str, Any]) -> str:
        """Format protocol optimization results for HTML display."""
        html = f"""
        <div class="protocol-results">
            <h4>🧪 Protocol Optimization</h4>
            <div class="protocol-summary">
                <p><strong>Research Field:</strong> {result.get('research_field', 'N/A')}</p>
            </div>
            
            <div class="improvements">
                <h5>Optimization Suggestions:</h5>
                <ul>
        """
        
        improvements = result.get('improvements', [])
        if isinstance(improvements, list):
            for improvement in improvements:
                html += f"<li>{improvement}</li>"
        elif isinstance(improvements, str):
            html += f"<li>{improvements}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="risk-assessment">
                <h5>Risk Assessment:</h5>
                <div class="risk-content">
        """
        
        risk_assessment = result.get('risk_assessment', '')
        if risk_assessment:
            html += f"<p>{risk_assessment}</p>"
        else:
            html += "<p>No significant risks identified.</p>"
        
        html += """
                </div>
            </div>
        </div>
        """
        
        return html
    
    def _save_analysis_data(self, analysis_data: Dict[str, Any]):
        """Save analysis data to database."""
        try:
            with self.db_helper.get_db_connection('research_paper_content') as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS paper_analyses (
                        analysis_id TEXT PRIMARY KEY,
                        session_id TEXT,
                        user_id TEXT,
                        filename TEXT,
                        file_path TEXT,
                        extracted_text TEXT,
                        word_count INTEGER,
                        page_count INTEGER,
                        file_size INTEGER,
                        created_at TEXT,
                        status TEXT
                    )
                """)
                
                conn.execute("""
                    INSERT INTO paper_analyses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_data['analysis_id'],
                    analysis_data['session_id'],
                    analysis_data['user_id'],
                    analysis_data['filename'],
                    analysis_data['file_path'],
                    analysis_data['extracted_text'],
                    analysis_data['word_count'],
                    analysis_data['page_count'],
                    analysis_data['file_size'],
                    analysis_data['created_at'],
                    analysis_data['status']
                ))
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save analysis data: {e}")
    
    def _get_analysis_data(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve analysis data from database."""
        try:
            with self.db_helper.get_db_connection('research_paper_content') as conn:
                cursor = conn.execute("""
                    SELECT * FROM paper_analyses WHERE analysis_id = ?
                """, (analysis_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                
                return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve analysis data: {e}")
            return None
    
    def _save_tool_result(self, analysis_id: str, tool_name: str, result: Dict[str, Any], ai_result: Dict[str, Any]):
        """Save tool results to database."""
        try:
            with self.db_helper.get_db_connection('research_paper_content') as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tool_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        analysis_id TEXT,
                        tool_name TEXT,
                        result_data TEXT,
                        ai_result_data TEXT,
                        created_at TEXT
                    )
                """)
                
                conn.execute("""
                    INSERT INTO tool_results (analysis_id, tool_name, result_data, ai_result_data, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    analysis_id,
                    tool_name,
                    json.dumps(result),
                    json.dumps(ai_result),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save tool result: {e}")
    
    def _error_response(self, message: str, details: str = None) -> Dict[str, Any]:
        """Return standardized error response."""
        return {
            'success': False,
            'error': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
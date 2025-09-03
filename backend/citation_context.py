"""
Citation Context Analyzer - Backend Handler
Analyzes citation usage, context, accuracy, and compliance with journal requirements.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

# Import your existing modules (adjust paths based on your structure)
try:
    from ai.ai_manager import AIManager
except ImportError:
    import sys
    sys.path.append('..')
    from ai.ai_manager import AIManager

try:
    from backend.utils.database_helper import DatabaseHelper
    from backend.utils.file_processor import FileProcessor
except ImportError:
    from utils.database_helper import DatabaseHelper
    from utils.file_processor import FileProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CitationContextAnalyzer:
    """
    Handles citation analysis for research papers.
    Analyzes citation accuracy, context relevance, and compliance with journal requirements.
    """
    
    def __init__(self):
        self.ai_manager = AIManager()
        self.db_helper = DatabaseHelper()
        self.file_processor = FileProcessor()
        self.logger = logging.getLogger(__name__)
        
        # Citation pattern regex for common styles
        self.citation_patterns = {
            'APA': [
                r'\(([^()]+,\s*\d{4}[a-z]?(?:,\s*p\.?\s*\d+)?)\)',  # (Author, 2024)
                r'\(([^()]+\s+\d{4}[a-z]?(?:,\s*p\.?\s*\d+)?)\)',   # (Author 2024)
            ],
            'MLA': [
                r'\(([^()]+\s+\d+)\)',  # (Author 123)
                r'\((\d+)\)',           # (123)
            ],
            'Chicago': [
                r'\(([^()]+,\s*\d{4}(?:,\s*\d+)?)\)',  # (Author, 2024, 123)
            ],
            'Nature': [
                r'(\d+(?:,\s*\d+)*)',   # Superscript numbers: 1,2,3
                r'\[(\d+(?:,\s*\d+)*)\]', # Bracketed numbers: [1,2,3]
            ],
            'IEEE': [
                r'\[(\d+(?:,\s*\d+)*)\]', # [1], [1,2,3]
                r'\[(\d+)–(\d+)\]',       # [1-5]
            ]
        }
    
    def process_citation_analysis(self, session_id: str, paper_content: str, 
                                target_journal: str = "nature", analysis_type: str = "comprehensive",
                                custom_requirements: str = None, content_type: str = "text") -> Dict[str, Any]:
        """
        Main method to process citation analysis request.
        
        Args:
            session_id: User session identifier
            paper_content: Paper text content or file path
            target_journal: Target journal name
            analysis_type: Type of analysis (comprehensive, citation-accuracy, etc.)
            custom_requirements: Custom citation requirements if target_journal is "custom"
            content_type: "text" or "file"
        
        Returns:
            Dict containing analysis results
        """
        try:
            # Update session activity
            self.db_helper.update_session_activity(session_id)
            
            # Extract text content
            if content_type == "file":
                text_content = self._extract_text_from_file(paper_content)
                if not text_content:
                    return {
                        'success': False,
                        'error': 'Failed to extract text from file. Please ensure the file is readable.'
                    }
            else:
                text_content = paper_content
            
            if not text_content.strip():
                return {
                    'success': False,
                    'error': 'No text content provided for analysis.'
                }
            
            # Get journal requirements
            journal_requirements = self._get_journal_citation_requirements(target_journal, custom_requirements)
            
            # Extract citations from text
            citations_found = self._extract_citations(text_content, journal_requirements['citation_style'])
            
            # Perform AI analysis
            ai_analysis = self._perform_ai_citation_analysis(
                text_content, citations_found, journal_requirements, analysis_type
            )
            
            if not ai_analysis.get('success', False):
                return {
                    'success': False,
                    'error': ai_analysis.get('error', 'AI analysis failed')
                }
            
            # Process and structure results
            analysis_results = self._process_analysis_results(
                ai_analysis['result'], citations_found, journal_requirements
            )
            
            # Save analysis to database
            self._save_analysis_results(session_id, text_content, analysis_results, {
                'target_journal': target_journal,
                'analysis_type': analysis_type,
                'citations_count': len(citations_found),
                'text_length': len(text_content.split())
            })
            
            # Log activity
            self.db_helper.log_activity(
                session_id, 
                'citation_context', 
                'analysis_completed',
                {
                    'target_journal': target_journal,
                    'analysis_type': analysis_type,
                    'citations_found': len(citations_found),
                    'success': True
                }
            )
            
            return {
                'success': True,
                'analysis': analysis_results
            }
            
        except Exception as e:
            self.logger.error(f"Citation analysis failed: {str(e)}", exc_info=True)
            
            # Log failed activity
            self.db_helper.log_activity(
                session_id, 
                'citation_context', 
                'analysis_failed',
                {'error': str(e)}
            )
            
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }
    
    def _extract_text_from_file(self, file_path: str) -> Optional[str]:
        """Extract text content from uploaded file"""
        try:
            return self.file_processor.extract_text_content(file_path)
        except Exception as e:
            self.logger.error(f"Text extraction failed: {str(e)}")
            return None
    
    def _get_journal_citation_requirements(self, journal_name: str, custom_requirements: str = None) -> Dict[str, Any]:
        """Get citation requirements for target journal"""
        if journal_name.lower() == "custom" and custom_requirements:
            return {
                'citation_style': 'Custom',
                'requirements': custom_requirements,
                'reference_limits': {},
                'special_notes': custom_requirements
            }
        
        # Get from database
        journal_requirements = self.db_helper.get_journal_requirements(journal_name)
        
        # Map journal requirements to citation analysis format
        citation_style_map = {
            'Nature format': 'Nature',
            'APA': 'APA',
            'IEEE': 'IEEE',
            'Chicago': 'Chicago',
            'MLA': 'MLA'
        }
        
        citation_style = citation_style_map.get(
            journal_requirements.get('citation_style', 'APA'), 
            'APA'
        )
        
        return {
            'journal_name': journal_requirements['name'],
            'citation_style': citation_style,
            'requirements': journal_requirements.get('special_requirements', []),
            'reference_limits': journal_requirements.get('word_limits', {}),
            'formatting_rules': journal_requirements.get('formatting_rules', {}),
            'language_variant': journal_requirements.get('language_variant', 'American English')
        }
    
    def _extract_citations(self, text: str, citation_style: str) -> List[Dict[str, Any]]:
        """Extract citations from text based on citation style"""
        citations = []
        patterns = self.citation_patterns.get(citation_style, self.citation_patterns['APA'])
        
        for i, pattern in enumerate(patterns):
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                citation = {
                    'text': match.group(0),
                    'content': match.group(1) if len(match.groups()) >= 1 else match.group(0),
                    'position': {
                        'start': match.start(),
                        'end': match.end()
                    },
                    'style': citation_style,
                    'pattern_type': i,
                    'surrounding_context': self._get_surrounding_context(text, match.start(), match.end())
                }
                citations.append(citation)
        
        # Remove duplicates and sort by position
        unique_citations = []
        seen_positions = set()
        
        for citation in sorted(citations, key=lambda x: x['position']['start']):
            pos_key = (citation['position']['start'], citation['position']['end'])
            if pos_key not in seen_positions:
                unique_citations.append(citation)
                seen_positions.add(pos_key)
        
        return unique_citations
    
    def _get_surrounding_context(self, text: str, start: int, end: int, context_length: int = 150) -> str:
        """Get surrounding context for a citation"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        context = text[context_start:context_end].strip()
        
        # Mark the citation within the context
        citation_in_context = text[start:end]
        context = context.replace(citation_in_context, f"**{citation_in_context}**", 1)
        
        return context
    
    def _perform_ai_citation_analysis(self, text: str, citations: List[Dict], 
                                    journal_requirements: Dict, analysis_type: str) -> Dict[str, Any]:
        """Use AI to analyze citations and context"""
        try:
            # Prepare data for AI analysis
            analysis_data = {
                'text': text,
                'citations': citations,
                'target_journal': journal_requirements['journal_name'],
                'citation_style': journal_requirements['citation_style'],
                'analysis_type': analysis_type,
                'requirements': journal_requirements.get('requirements', [])
            }
            
            # Call AI manager for citation analysis
            ai_result = self.ai_manager.process_request(
                feature='citation_context',
                data=analysis_data,
                session_id=None  # Not needed for AI analysis
            )
            
            return ai_result
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {str(e)}")
            return {
                'success': False,
                'error': f'AI analysis failed: {str(e)}'
            }
    
    def _process_analysis_results(self, ai_results: Dict, citations: List[Dict], 
                                journal_requirements: Dict) -> Dict[str, Any]:
        """Process and structure the analysis results"""
        # Calculate overall score based on various factors
        total_issues = len(ai_results.get('style_issues', []))
        missing_citations = len(ai_results.get('missing_citations', []))
        total_citations = len(citations)
        
        # Simple scoring algorithm
        base_score = 100
        if total_citations > 0:
            style_penalty = min(30, (total_issues / total_citations) * 50)
            missing_penalty = min(40, missing_citations * 5)
            overall_score = max(10, base_score - style_penalty - missing_penalty)
        else:
            overall_score = 50 if missing_citations == 0 else 30
        
        # Generate summary
        summary = self._generate_analysis_summary(ai_results, overall_score, journal_requirements)
        
        # Structure issues and improvements
        issues = self._structure_issues(ai_results, citations)
        improvements = self._structure_improvements(ai_results)
        
        return {
            'overall_score': int(overall_score),
            'summary': summary,
            'total_citations_found': len(citations),
            'target_journal': journal_requirements['journal_name'],
            'citation_style': journal_requirements['citation_style'],
            'issues': issues,
            'improvements': improvements,
            'detailed_analysis': ai_results,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _generate_analysis_summary(self, ai_results: Dict, score: int, journal_requirements: Dict) -> str:
        """Generate a summary of the analysis"""
        journal_name = journal_requirements['journal_name']
        citation_style = journal_requirements['citation_style']
        
        if score >= 80:
            quality = "excellent"
        elif score >= 60:
            quality = "good"
        elif score >= 40:
            quality = "fair"
        else:
            quality = "needs significant improvement"
        
        style_issues_count = len(ai_results.get('style_issues', []))
        missing_count = len(ai_results.get('missing_citations', []))
        
        summary_parts = [
            f"Your paper's citation quality is {quality} with a score of {score}/100 for {journal_name} standards."
        ]
        
        if style_issues_count > 0:
            summary_parts.append(f"Found {style_issues_count} citation formatting issues that need attention for {citation_style} style.")
        
        if missing_count > 0:
            summary_parts.append(f"Identified {missing_count} claims that would benefit from additional citation support.")
        
        if score >= 80:
            summary_parts.append("Your citations are well-formatted and appropriately support your arguments.")
        
        return " ".join(summary_parts)
    
    def _structure_issues(self, ai_results: Dict, citations: List[Dict]) -> List[Dict[str, str]]:
        """Structure issues found during analysis"""
        issues = []
        
        # Style issues from AI
        for style_issue in ai_results.get('style_issues', []):
            issues.append({
                'type': 'Citation Format Issue',
                'location': f"Citation: {style_issue.get('citation', 'Unknown')}",
                'description': style_issue.get('issue', 'Formatting issue detected'),
                'suggestion': style_issue.get('correction', 'Please review citation format')
            })
        
        # Missing citations from AI
        for missing in ai_results.get('missing_citations', []):
            issues.append({
                'type': 'Missing Citation',
                'location': f"Near: {missing.get('location', 'Unknown location')}",
                'description': missing.get('claim', 'Unsupported claim detected'),
                'suggestion': missing.get('suggestion', 'Consider adding citation support')
            })
        
        # Context issues from AI
        for context_issue in ai_results.get('context_analysis', []):
            if context_issue.get('relevance_score', 100) < 70:  # Threshold for relevance
                issues.append({
                    'type': 'Citation Context Issue',
                    'location': f"Citation: {context_issue.get('citation', 'Unknown')}",
                    'description': context_issue.get('issue', 'Citation may not strongly support the claim'),
                    'suggestion': 'Review if citation directly supports the statement'
                })
        
        return issues
    
    def _structure_improvements(self, ai_results: Dict) -> List[Dict[str, str]]:
        """Structure positive improvements and good practices found"""
        improvements = []
        
        # Check for good citation practices
        citations_found = ai_results.get('citations', [])
        
        if citations_found:
            improvements.append({
                'type': 'Citation Coverage',
                'description': f"Found {len(citations_found)} citations throughout the paper",
                'impact': 'Good citation coverage helps support your arguments'
            })
        
        # Check for recent sources (if AI provides this data)
        recent_sources = [c for c in citations_found if self._is_recent_citation(c)]
        if recent_sources:
            improvements.append({
                'type': 'Source Currency',
                'description': f"Includes {len(recent_sources)} recent sources",
                'impact': 'Recent sources demonstrate awareness of current research'
            })
        
        # Add AI-suggested improvements
        if 'strengths' in ai_results:
            for strength in ai_results['strengths']:
                improvements.append({
                    'type': strength.get('type', 'Good Practice'),
                    'description': strength.get('description', 'Positive aspect identified'),
                    'impact': strength.get('impact', 'Contributes to overall paper quality')
                })
        
        return improvements
    
    def _is_recent_citation(self, citation: Dict) -> bool:
        """Check if citation appears to be recent (basic heuristic)"""
        current_year = datetime.now().year
        citation_text = citation.get('content', '')
        
        # Look for years in citation
        year_matches = re.findall(r'\b(20[0-2]\d)\b', citation_text)
        
        if year_matches:
            latest_year = max(int(year) for year in year_matches)
            return (current_year - latest_year) <= 5  # Within 5 years
        
        return False
    
    def _save_analysis_results(self, session_id: str, text_content: str, 
                             analysis_results: Dict, metadata: Dict):
        """Save analysis results to database"""
        try:
            self.db_helper.save_citation_analysis(
                session_id=session_id,
                analyzed_text=text_content,
                citation_results=analysis_results,
                metadata={
                    **metadata,
                    'overall_score': analysis_results['overall_score'],
                    'issues_count': len(analysis_results['issues']),
                    'missing_citations_count': len([i for i in analysis_results['issues'] if i['type'] == 'Missing Citation'])
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to save analysis results: {str(e)}")
            # Don't fail the whole request if database save fails
    
    def get_analysis_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's citation analysis history"""
        try:
            # This would be implemented when references.db is created
            # For now, return empty list
            return []
        except Exception as e:
            self.logger.error(f"Failed to get analysis history: {str(e)}")
            return []
    
    def get_supported_citation_styles(self) -> List[str]:
        """Get list of supported citation styles"""
        return list(self.citation_patterns.keys())
    
    def validate_citation_format(self, citation_text: str, style: str) -> Dict[str, Any]:
        """Validate a specific citation format"""
        patterns = self.citation_patterns.get(style, self.citation_patterns['APA'])
        
        for pattern in patterns:
            if re.match(pattern, citation_text.strip()):
                return {
                    'valid': True,
                    'style': style,
                    'message': f'Citation appears to follow {style} format'
                }
        
        return {
            'valid': False,
            'style': style,
            'message': f'Citation does not match expected {style} format',
            'expected_formats': self._get_style_examples(style)
        }
    
    def _get_style_examples(self, style: str) -> List[str]:
        """Get example citation formats for a style"""
        examples = {
            'APA': ['(Smith, 2024)', '(Johnson & Brown, 2023, p. 45)'],
            'MLA': ['(Smith 123)', '(45)'],
            'Chicago': ['(Smith, 2024, 123)', '(Brown, 2023)'],
            'Nature': ['1,2,3', '[1-3]'],
            'IEEE': ['[1]', '[1,2,3]', '[1-5]']
        }
        
        return examples.get(style, examples['APA'])


# Initialize global instance for import
citation_analyzer = CitationContextAnalyzer()

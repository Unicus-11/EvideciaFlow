"""
Response Parser for Research Platform
Processes and structures AI responses from different features
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedResponse:
    """Structured response from AI processing"""
    main_content: str
    sections: Dict[str, str]
    metadata: Dict[str, Any]
    success: bool
    errors: List[str]
    timestamp: datetime


class ResponseParser:
    """Parses AI responses for different research platform features"""
    
    def __init__(self):
        self.section_patterns = {
            # Common patterns for section detection
            'rewritten_text': [r'REWRITTEN TEXT[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)', 
                             r'IMPROVED VERSION[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'],
            'key_improvements': [r'KEY IMPROVEMENTS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)',
                               r'CHANGES MADE[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'],
            'compliance_check': [r'COMPLIANCE CHECK[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)',
                               r'REQUIREMENTS CHECK[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'],
            'optimized_protocol': [r'OPTIMIZED PROTOCOL[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'],
            'risk_assessment': [r'RISK ASSESSMENT[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'],
            'novel_ideas': [r'NOVEL IDEAS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)',
                          r'INNOVATIVE CONCEPTS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'],
            'contradictions_found': [r'CONTRADICTIONS FOUND[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)',
                                   r'LOGICAL CONFLICTS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'],
            'recommendations': [r'RECOMMENDATIONS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)',
                              r'SUGGESTIONS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)']
        }
    
    def parse_explain_rewrite_response(self, response: str, word_count_limit: int = None) -> ParsedResponse:
        """Parse response from explain/rewrite feature"""
        
        sections = {}
        errors = []
        
        try:
            # Extract main rewritten content
            rewritten_text = self._extract_section(response, 'rewritten_text')
            if rewritten_text:
                sections['rewritten_text'] = rewritten_text.strip()
                
                # Check word count if limit provided
                if word_count_limit:
                    word_count = len(rewritten_text.split())
                    if word_count > word_count_limit:
                        errors.append(f"Text exceeds word limit: {word_count}/{word_count_limit} words")
            else:
                errors.append("Could not find rewritten text in response")
            
            # Extract improvements
            improvements = self._extract_section(response, 'key_improvements')
            if improvements:
                sections['improvements'] = improvements.strip()
            
            # Extract compliance check
            compliance = self._extract_section(response, 'compliance_check')
            if compliance:
                sections['compliance'] = compliance.strip()
            
            # Generate metadata
            metadata = {
                'word_count': len(rewritten_text.split()) if rewritten_text else 0,
                'improvements_count': len(re.findall(r'^\d+\.|\n\d+\.', improvements)) if improvements else 0,
                'processing_type': 'explain_rewrite'
            }
            
            return ParsedResponse(
                main_content=sections.get('rewritten_text', ''),
                sections=sections,
                metadata=metadata,
                success=len(errors) == 0,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ParsedResponse(
                main_content='',
                sections={},
                metadata={'processing_type': 'explain_rewrite'},
                success=False,
                errors=[f"Parsing error: {str(e)}"],
                timestamp=datetime.now()
            )
    
    def parse_protocol_optimization_response(self, response: str) -> ParsedResponse:
        """Parse response from protocol optimization feature"""
        
        sections = {}
        errors = []
        
        try:
            # Extract optimized protocol
            optimized = self._extract_section(response, 'optimized_protocol')
            if optimized:
                sections['optimized_protocol'] = optimized.strip()
            else:
                errors.append("Could not find optimized protocol in response")
            
            # Extract improvements
            improvements = self._extract_section(response, 'key_improvements')
            if improvements:
                sections['improvements'] = improvements.strip()
            
            # Extract risk assessment
            risks = self._extract_section(response, 'risk_assessment')
            if risks:
                sections['risk_assessment'] = risks.strip()
            
            # Extract recommendations
            recommendations = self._extract_section(response, 'recommendations')
            if recommendations:
                sections['recommendations'] = recommendations.strip()
            
            metadata = {
                'sections_found': len(sections),
                'has_risk_assessment': 'risk_assessment' in sections,
                'processing_type': 'protocol_optimization'
            }
            
            return ParsedResponse(
                main_content=sections.get('optimized_protocol', ''),
                sections=sections,
                metadata=metadata,
                success=len(errors) == 0,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ParsedResponse(
                main_content='',
                sections={},
                metadata={'processing_type': 'protocol_optimization'},
                success=False,
                errors=[f"Parsing error: {str(e)}"],
                timestamp=datetime.now()
            )
    
    def parse_figure_analysis_response(self, response: str) -> ParsedResponse:
        """Parse response from figure analysis feature"""
        
        sections = {}
        errors = []
        
        try:
            # Extract compliance analysis
            compliance = self._extract_section(response, 'compliance_check')
            if compliance:
                sections['compliance_analysis'] = compliance.strip()
            
            # Extract issues
            issues_pattern = r'ISSUES IDENTIFIED[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            issues_match = re.search(issues_pattern, response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                sections['issues_identified'] = issues_match.group(1).strip()
            
            # Extract recommendations
            recommendations = self._extract_section(response, 'recommendations')
            if recommendations:
                sections['recommendations'] = recommendations.strip()
            
            # Extract technical specs
            tech_pattern = r'TECHNICAL SPECIFICATIONS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            tech_match = re.search(tech_pattern, response, re.DOTALL | re.IGNORECASE)
            if tech_match:
                sections['technical_specs'] = tech_match.group(1).strip()
            
            # Parse technical requirements from response
            dpi_match = re.search(r'(\d+)\s*DPI', response, re.IGNORECASE)
            format_match = re.search(r'Format[:\s]*(PDF|PNG|TIFF|JPG)', response, re.IGNORECASE)
            
            metadata = {
                'required_dpi': dpi_match.group(1) if dpi_match else None,
                'required_format': format_match.group(1) if format_match else None,
                'issues_count': len(re.findall(r'^\d+\.|\n\d+\.', sections.get('issues_identified', ''))),
                'processing_type': 'figure_analysis'
            }
            
            if not any(sections.values()):
                errors.append("Could not parse figure analysis sections")
            
            return ParsedResponse(
                main_content=sections.get('compliance_analysis', ''),
                sections=sections,
                metadata=metadata,
                success=len(errors) == 0,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ParsedResponse(
                main_content='',
                sections={},
                metadata={'processing_type': 'figure_analysis'},
                success=False,
                errors=[f"Parsing error: {str(e)}"],
                timestamp=datetime.now()
            )
    
    def parse_citation_analysis_response(self, response: str) -> ParsedResponse:
        """Parse response from citation analysis feature"""
        
        sections = {}
        errors = []
        
        try:
            # Extract citations found
            citations_pattern = r'CITATIONS FOUND[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            citations_match = re.search(citations_pattern, response, re.DOTALL | re.IGNORECASE)
            if citations_match:
                sections['citations_found'] = citations_match.group(1).strip()
            
            # Extract context analysis
            context_pattern = r'CONTEXT ANALYSIS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            context_match = re.search(context_pattern, response, re.DOTALL | re.IGNORECASE)
            if context_match:
                sections['context_analysis'] = context_match.group(1).strip()
            
            # Extract missing citations
            missing_pattern = r'MISSING CITATIONS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            missing_match = re.search(missing_pattern, response, re.DOTALL | re.IGNORECASE)
            if missing_match:
                sections['missing_citations'] = missing_match.group(1).strip()
            
            # Extract style issues
            style_pattern = r'STYLE ISSUES[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            style_match = re.search(style_pattern, response, re.DOTALL | re.IGNORECASE)
            if style_match:
                sections['style_issues'] = style_match.group(1).strip()
            
            # Extract recommendations
            recommendations = self._extract_section(response, 'recommendations')
            if recommendations:
                sections['recommendations'] = recommendations.strip()
            
            # Count citations and issues
            citation_count = len(re.findall(r'\([^)]*\d{4}[^)]*\)', sections.get('citations_found', '')))
            missing_count = len(re.findall(r'^\d+\.|\n\d+\.', sections.get('missing_citations', '')))
            
            metadata = {
                'citations_count': citation_count,
                'missing_citations_count': missing_count,
                'has_style_issues': len(sections.get('style_issues', '')) > 0,
                'processing_type': 'citation_analysis'
            }
            
            return ParsedResponse(
                main_content=sections.get('context_analysis', ''),
                sections=sections,
                metadata=metadata,
                success=len(errors) == 0,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ParsedResponse(
                main_content='',
                sections={},
                metadata={'processing_type': 'citation_analysis'},
                success=False,
                errors=[f"Parsing error: {str(e)}"],
                timestamp=datetime.now()
            )
    
    def parse_idea_recombination_response(self, response: str) -> ParsedResponse:
        """Parse response from idea recombination feature"""
        
        sections = {}
        errors = []
        
        try:
            # Extract novel ideas
            ideas = self._extract_section(response, 'novel_ideas')
            if ideas:
                sections['novel_ideas'] = ideas.strip()
            else:
                errors.append("Could not find novel ideas in response")
            
            # Extract methodological combinations
            methods_pattern = r'METHODOLOGICAL COMBINATIONS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            methods_match = re.search(methods_pattern, response, re.DOTALL | re.IGNORECASE)
            if methods_match:
                sections['methodological_combinations'] = methods_match.group(1).strip()
            
            # Extract research gaps
            gaps_pattern = r'RESEARCH GAPS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            gaps_match = re.search(gaps_pattern, response, re.DOTALL | re.IGNORECASE)
            if gaps_match:
                sections['research_gaps'] = gaps_match.group(1).strip()
            
            # Extract collaboration opportunities
            collab_pattern = r'COLLABORATION OPPORTUNITIES[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            collab_match = re.search(collab_pattern, response, re.DOTALL | re.IGNORECASE)
            if collab_match:
                sections['collaboration_opportunities'] = collab_match.group(1).strip()
            
            # Count ideas generated
            idea_count = len(re.findall(r'^\d+\.|\n\d+\.', sections.get('novel_ideas', '')))
            
            metadata = {
                'ideas_generated': idea_count,
                'has_methodological_combinations': 'methodological_combinations' in sections,
                'has_collaboration_opportunities': 'collaboration_opportunities' in sections,
                'processing_type': 'idea_recombination'
            }
            
            return ParsedResponse(
                main_content=sections.get('novel_ideas', ''),
                sections=sections,
                metadata=metadata,
                success=len(errors) == 0,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ParsedResponse(
                main_content='',
                sections={},
                metadata={'processing_type': 'idea_recombination'},
                success=False,
                errors=[f"Parsing error: {str(e)}"],
                timestamp=datetime.now()
            )
    
    def parse_contradiction_detection_response(self, response: str) -> ParsedResponse:
        """Parse response from contradiction detection feature"""
        
        sections = {}
        errors = []
        
        try:
            # Extract contradictions found
            contradictions = self._extract_section(response, 'contradictions_found')
            if contradictions:
                sections['contradictions_found'] = contradictions.strip()
            
            # Extract logical issues
            logic_pattern = r'LOGICAL ISSUES[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            logic_match = re.search(logic_pattern, response, re.DOTALL | re.IGNORECASE)
            if logic_match:
                sections['logical_issues'] = logic_match.group(1).strip()
            
            # Extract consistency score
            score_pattern = r'CONSISTENCY SCORE[:\s]*([0-9]+(?:\.[0-9]+)?)'
            score_match = re.search(score_pattern, response, re.IGNORECASE)
            consistency_score = float(score_match.group(1)) if score_match else None
            
            # Extract evidence gaps
            gaps_pattern = r'EVIDENCE GAPS[:\s]*\n(.*?)(?=\n[A-Z\s]+:|$)'
            gaps_match = re.search(gaps_pattern, response, re.DOTALL | re.IGNORECASE)
            if gaps_match:
                sections['evidence_gaps'] = gaps_match.group(1).strip()
            
            # Extract recommendations
            recommendations = self._extract_section(response, 'recommendations')
            if recommendations:
                sections['recommendations'] = recommendations.strip()
            
            # Count issues
            contradiction_count = len(re.findall(r'^\d+\.|\n\d+\.', sections.get('contradictions_found', '')))
            
            metadata = {
                'contradictions_count': contradiction_count,
                'consistency_score': consistency_score,
                'has_evidence_gaps': 'evidence_gaps' in sections,
                'processing_type': 'contradiction_detection'
            }
            
            if contradiction_count == 0 and not sections.get('logical_issues'):
                sections['summary'] = "No significant contradictions or logical issues detected."
            
            return ParsedResponse(
                main_content=sections.get('contradictions_found', sections.get('summary', '')),
                sections=sections,
                metadata=metadata,
                success=len(errors) == 0,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ParsedResponse(
                main_content='',
                sections={},
                metadata={'processing_type': 'contradiction_detection'},
                success=False,
                errors=[f"Parsing error: {str(e)}"],
                timestamp=datetime.now()
            )
    
    def _extract_section(self, text: str, section_key: str) -> Optional[str]:
        """Extract a specific section from response text using patterns"""
        
        patterns = self.section_patterns.get(section_key, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_word_count(self, text: str) -> int:
        """Extract word count from text"""
        return len(text.split())
    
    def extract_numbered_items(self, text: str) -> List[str]:
        """Extract numbered list items from text"""
        items = re.findall(r'^\d+\.\s*(.+?)(?=\n\d+\.|\n[A-Z]|\n\n|$)', text, re.MULTILINE | re.DOTALL)
        return [item.strip() for item in items]
    
    def clean_response_text(self, text: str) -> str:
        """Clean and format response text"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove markdown-style formatting that might interfere
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'__(.*?)__', r'\1', text)      # Remove underline
        
        return text.strip()
    
    def validate_response_completeness(self, parsed_response: ParsedResponse, expected_sections: List[str]) -> Tuple[bool, List[str]]:
        """Validate that response contains expected sections"""
        missing_sections = []
        
        for section in expected_sections:
            if section not in parsed_response.sections or not parsed_response.sections[section].strip():
                missing_sections.append(section)
        
        is_complete = len(missing_sections) == 0
        return is_complete, missing_sections
    
    def get_response_summary(self, parsed_response: ParsedResponse) -> Dict[str, Any]:
        """Generate summary statistics for parsed response"""
        
        return {
            'success': parsed_response.success,
            'processing_type': parsed_response.metadata.get('processing_type'),
            'sections_count': len(parsed_response.sections),
            'main_content_length': len(parsed_response.main_content),
            'has_errors': len(parsed_response.errors) > 0,
            'error_count': len(parsed_response.errors),
            'timestamp': parsed_response.timestamp.isoformat(),
            'metadata': parsed_response.metadata
        }

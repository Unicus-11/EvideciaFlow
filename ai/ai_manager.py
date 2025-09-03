"""
AI Manager for Research Platform
Handles AI client selection and routing to appropriate features
"""

import os
from typing import Dict, Any, Optional
from groq_client import GroqClient
from prompt_templates import PromptTemplates
from response_parser import ResponseParser


class AIManager:
    """Central manager for all AI operations in the research platform"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key not found. Set GROQ_API_KEY environment variable.")
        
        # Initialize clients and utilities
        self.groq_client = GroqClient(self.api_key)
        self.prompt_templates = PromptTemplates()
        self.response_parser = ResponseParser()
        
        # Feature routing
        self.feature_handlers = {
            'explain_rewrite': self._handle_explain_rewrite,
            'protocol_optimizer': self._handle_protocol_optimizer,
            'figure_fixer': self._handle_figure_fixer,
            'citation_context': self._handle_citation_context,
            'idea_recombinator': self._handle_idea_recombinator,
            'contradiction_detector': self._handle_contradiction_detector
        }
    
    def process_request(self, feature: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route request to appropriate feature handler
        
        Args:
            feature: Feature name (e.g., 'explain_rewrite')
            data: Request data including text, parameters, etc.
            
        Returns:
            Dict with processed results and metadata
        """
        if feature not in self.feature_handlers:
            raise ValueError(f"Unknown feature: {feature}")
        
        try:
            return self.feature_handlers[feature](data)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'feature': feature
            }
    
    def _handle_explain_rewrite(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle explain/rewrite feature requests"""
        text = data.get('text', '')
        target_journal = data.get('target_journal', 'Nature')
        language = data.get('language', 'American English')
        
        # Generate prompt
        prompt = self.prompt_templates.get_rewrite_prompt(
            text=text,
            journal=target_journal,
            language=language
        )
        
        # Get AI response
        response = self.groq_client.generate_text(
            prompt=prompt,
            model='llama3-70b-8192',  # Best model for academic writing
            max_tokens=4000
        )
        
        if not response['success']:
            return response
        
        # Parse response
        parsed = self.response_parser.parse_rewrite_response(response['text'])
        
        return {
            'success': True,
            'feature': 'explain_rewrite',
            'original_text': text,
            'rewritten_text': parsed['rewritten_text'],
            'improvements': parsed['improvements'],
            'target_journal': target_journal,
            'language': language,
            'word_count': len(parsed['rewritten_text'].split()),
            'processing_time': response.get('processing_time', 0)
        }
    
    def _handle_protocol_optimizer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle protocol optimization requests"""
        protocol_text = data.get('protocol_text', '')
        research_field = data.get('research_field', 'general')
        
        prompt = self.prompt_templates.get_protocol_optimization_prompt(
            protocol=protocol_text,
            field=research_field
        )
        
        response = self.groq_client.generate_text(
            prompt=prompt,
            model='llama3-70b-8192',
            max_tokens=3000
        )
        
        if not response['success']:
            return response
        
        parsed = self.response_parser.parse_protocol_response(response['text'])
        
        return {
            'success': True,
            'feature': 'protocol_optimizer',
            'original_protocol': protocol_text,
            'optimized_protocol': parsed['optimized_protocol'],
            'improvements': parsed['improvements'],
            'risk_assessment': parsed['risk_assessment'],
            'research_field': research_field
        }
    
    def _handle_figure_fixer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle figure analysis and fixing suggestions"""
        figure_description = data.get('figure_description', '')
        target_journal = data.get('target_journal', 'Nature')
        current_specs = data.get('current_specs', {})
        
        prompt = self.prompt_templates.get_figure_analysis_prompt(
            description=figure_description,
            journal=target_journal,
            specs=current_specs
        )
        
        response = self.groq_client.generate_text(
            prompt=prompt,
            model='llama3-8b-8192',  # Faster model for analysis
            max_tokens=2000
        )
        
        if not response['success']:
            return response
        
        parsed = self.response_parser.parse_figure_response(response['text'])
        
        return {
            'success': True,
            'feature': 'figure_fixer',
            'analysis': parsed['analysis'],
            'issues_found': parsed['issues'],
            'recommendations': parsed['recommendations'],
            'target_requirements': parsed['requirements'],
            'target_journal': target_journal
        }
    
    def _handle_citation_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle citation context analysis"""
        text = data.get('text', '')
        citation_style = data.get('citation_style', 'APA')
        
        prompt = self.prompt_templates.get_citation_analysis_prompt(
            text=text,
            style=citation_style
        )
        
        response = self.groq_client.generate_text(
            prompt=prompt,
            model='llama3-70b-8192',
            max_tokens=2500
        )
        
        if not response['success']:
            return response
        
        parsed = self.response_parser.parse_citation_response(response['text'])
        
        return {
            'success': True,
            'feature': 'citation_context',
            'citations_found': parsed['citations'],
            'context_analysis': parsed['context'],
            'missing_citations': parsed['missing'],
            'style_issues': parsed['style_issues'],
            'citation_style': citation_style
        }
    
    def _handle_idea_recombinator(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle idea recombination from multiple sources"""
        sources = data.get('sources', [])
        research_question = data.get('research_question', '')
        
        prompt = self.prompt_templates.get_idea_recombination_prompt(
            sources=sources,
            question=research_question
        )
        
        response = self.groq_client.generate_text(
            prompt=prompt,
            model='llama3-70b-8192',
            max_tokens=3500
        )
        
        if not response['success']:
            return response
        
        parsed = self.response_parser.parse_recombination_response(response['text'])
        
        return {
            'success': True,
            'feature': 'idea_recombinator',
            'novel_ideas': parsed['ideas'],
            'combinations': parsed['combinations'],
            'research_gaps': parsed['gaps'],
            'methodology_suggestions': parsed['methods'],
            'research_question': research_question
        }
    
    def _handle_contradiction_detector(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contradiction detection in research text"""
        text = data.get('text', '')
        check_type = data.get('check_type', 'internal')  # 'internal' or 'external'
        
        prompt = self.prompt_templates.get_contradiction_detection_prompt(
            text=text,
            check_type=check_type
        )
        
        response = self.groq_client.generate_text(
            prompt=prompt,
            model='llama3-70b-8192',
            max_tokens=2500
        )
        
        if not response['success']:
            return response
        
        parsed = self.response_parser.parse_contradiction_response(response['text'])
        
        return {
            'success': True,
            'feature': 'contradiction_detector',
            'contradictions': parsed['contradictions'],
            'logical_issues': parsed['logical_issues'],
            'consistency_score': parsed['consistency_score'],
            'recommendations': parsed['recommendations'],
            'check_type': check_type
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check if AI service is available"""
        try:
            test_response = self.groq_client.generate_text(
                prompt="Test connection",
                model='llama3-8b-8192',
                max_tokens=10
            )
            return {
                'status': 'healthy' if test_response['success'] else 'unhealthy',
                'service': 'groq',
                'model_available': test_response['success']
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'groq',
                'error': str(e)
            }

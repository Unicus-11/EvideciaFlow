"""
Prompt Templates for Research Platform Features
Specialized prompts for academic writing and research analysis
"""

from typing import Dict, List, Any, Optional


class PromptTemplates:
    """Collection of prompt templates for research platform features"""
    
    def __init__(self):
        self.journal_requirements = {
            'Nature': {
                'style': 'concise, impactful, accessible to broad readership',
                'language': 'British English',
                'word_limits': {'abstract': 150, 'main_text': 3000}
            },
            'Science': {
                'style': 'clear, significant findings emphasized',
                'language': 'American English', 
                'word_limits': {'abstract': 125, 'main_text': 2500}
            },
            'Cell': {
                'style': 'detailed methodology, clear significance',
                'language': 'American English',
                'word_limits': {'abstract': 150, 'main_text': 4000}
            }
        }
    
    def get_rewrite_prompt(self, text: str, journal: str = 'Nature', language: str = 'American English') -> str:
        """Generate prompt for explain/rewrite feature"""
        
        journal_info = self.journal_requirements.get(journal, {
            'style': 'clear and academic',
            'language': language,
            'word_limits': {'abstract': 200, 'main_text': 4000}
        })
        
        return f"""You are an expert academic writing assistant specialized in {journal} submissions.

TASK: Rewrite the following research

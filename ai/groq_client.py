import os
import time
from typing import Dict, Any, Optional, List

# Install python-dotenv if not already: pip install python-dotenv
from dotenv import load_dotenv

# Load .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment. Please check your .env file.")

from groq import Groq  # Make sure groq SDK is installed

class GroqClient:
    """Client for Groq API with error handling and rate limiting"""
    
    def __init__(self, api_key: str = GROQ_API_KEY):
        self.client = Groq(api_key=api_key)
        self.last_request_time = 0
        self.min_request_interval = 2  # 2 seconds between requests (30/min = 2s interval)
    
    def generate_text(
        self, 
        prompt: str, 
        model: str = 'llama3-8b-8192',
        max_tokens: int = 1000,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        self._enforce_rate_limit()
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                stream=False
            )
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'text': response.choices[0].message.content,
                'model': model,
                'tokens_used': response.usage.total_tokens,
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'processing_time': processing_time
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'model': model,
                'processing_time': time.time() - start_time
            }
    
    def generate_streaming_text(
        self,
        prompt: str,
        model: str = 'llama3-8b-8192',
        max_tokens: int = 1000,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ):
        self._enforce_rate_limit()
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def analyze_text_quality(self, text: str, context: str = "academic") -> Dict[str, Any]:
        prompt = f"""
        Analyze the quality of this {context} text and provide scores (1-10):

        Text: "{text}"

        Please evaluate:
        1. Clarity (1-10)
        2. Academic rigor (1-10) 
        3. Grammar and style (1-10)
        4. Readability (1-10)
        5. Technical accuracy (1-10)

        Provide brief explanations for each score.
        Format your response as JSON.
        """
        
        response = self.generate_text(
            prompt=prompt,
            model='llama3-70b-8192',
            temperature=0.1,
            max_tokens=500
        )
        
        if response['success']:
            try:
                import json
                analysis = json.loads(response['text'])
                return {'success': True, 'analysis': analysis}
            except:
                return {'success': True, 'analysis': response['text']}
        else:
            return response
    
    def get_available_models(self) -> List[str]:
        return [
            'llama3-70b-8192',
            'llama3-8b-8192',
            'mixtral-8x7b-32768',
            'gemma-7b-it'
        ]
    
    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4  # Rough estimate: 1 token ≈ 4 characters
    
    def _enforce_rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def batch_process_texts(
        self, 
        texts: List[str], 
        prompt_template: str,
        model: str = 'llama3-8b-8192'
    ) -> List[Dict[str, Any]]:
        results = []
        for i, text in enumerate(texts):
            prompt = prompt_template.format(text=text)
            result = self.generate_text(prompt=prompt, model=model)
            result['batch_index'] = i
            result['input_text'] = text
            results.append(result)
            time.sleep(0.5)
        return results
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = self.generate_text(
                prompt="Hello, please respond with 'OK'",
                model='llama3-8b-8192',
                max_tokens=5
            )
            return {
                'status': 'healthy' if response['success'] else 'unhealthy',
                'response_time': response.get('processing_time', 0),
                'model_available': response['success']
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
"""
AI Manager for Research Platform
Handles AI client selection and routing to appropriate features
"""

import os
import importlib
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass


@dataclass
class GenerationParams:
    """Configuration for AI model generation parameters"""
    temperature: float
    top_p: float


@dataclass
class ModelResponse:
    """Normalized response from AI model"""
    success: bool
    text: str
    processing_time: float
    raw: Any = None
    error: Optional[str] = None


class AIManager:
    """Central manager for all AI operations in the research platform"""
    
    # Default models for different features
    DEFAULT_MODELS = {
        "explain_rewrite": "llama3-70b-8192",
        "protocol_optimizer": "llama3-70b-8192", 
        "figure_fixer": "llama3-8b-8192",
        "citation_context": "llama3-70b-8192",
        "idea_recombinator": "llama3-70b-8192",
        "contradiction_detector": "llama3-70b-8192"
    }
    
    # Generation parameters by creativity level
    CREATIVITY_PARAMS = {
        "low": GenerationParams(temperature=0.2, top_p=0.6),
        "moderate": GenerationParams(temperature=0.6, top_p=0.9), 
        "high": GenerationParams(temperature=0.95, top_p=0.95)
    }

    def __init__(self, api_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("Groq API key not found. Set GROQ_API_KEY environment variable.")
        
        self._initialize_components()
        self._setup_feature_handlers()

    def _initialize_components(self) -> None:
        """Initialize AI client and supporting components"""
        try:
            from ai.groq_client import GroqClient
            self.groq_client = GroqClient(self.api_key)
            
            # Initialize prompt templates
            prompt_module = self._safe_import("prompt_templates", ["ai.prompt_templates", "prompt_templates"])
            self.prompt_templates = prompt_module.PromptTemplates()
            
            # Initialize response parser  
            parser_module = self._safe_import("response_parser", ["ai.response_parser", "response_parser"])
            self.response_parser = parser_module.ResponseParser()
            
        except Exception as e:
            self.logger.exception("Failed to initialize AI components")
            raise RuntimeError(f"AI Manager initialization failed: {e}")

    def _safe_import(self, component_name: str, import_paths: List[str]):
        """Safely import a component from multiple possible paths"""
        last_error = None
        for path in import_paths:
            try:
                return importlib.import_module(path)
            except ImportError as e:
                last_error = e
                continue
        
        raise ImportError(f"Could not import {component_name}. Tried: {import_paths}. Last error: {last_error}")

    def _setup_feature_handlers(self) -> None:
        """Setup internal feature handlers"""
        self.feature_handlers: Dict[str, Callable] = {
            "explain_rewrite": self._handle_explain_rewrite,
            "protocol_optimizer": self._handle_protocol_optimizer,
            "figure_fixer": self._handle_figure_fixer,
            "citation_context": self._handle_citation_context,
            "idea_recombinator": self._handle_idea_recombinator,
            "contradiction_detector": self._handle_contradiction_detector,
        }

    def process_request(self, feature: str, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Route request to appropriate feature handler
        
        Args:
            feature: Feature name to process
            data: Request data
            session_id: Optional session identifier
            
        Returns:
            Normalized response dict with success, feature, result, and error fields
        """
        feature_key = (feature or "").strip().lower()
        if not feature_key:
            return self._error_response(feature, "Feature name is required")

        # Try internal handler first
        handler = self.feature_handlers.get(feature_key)
        if handler:
            return self._execute_handler(handler, feature_key, data, session_id)

        # Fallback to external module
        return self._try_external_handler(feature_key, data, session_id)

    def _execute_handler(self, handler: Callable, feature: str, data: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Execute a feature handler with error handling"""
        try:
            result = handler(data, session_id)
            return {"success": True, "feature": feature, "result": result, "error": None}
        except Exception as e:
            self.logger.exception(f"Handler {feature} failed")
            return self._error_response(feature, str(e))

    def _try_external_handler(self, feature: str, data: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Attempt to load and execute external feature handler"""
        try:
            module_name = f"backend.features.{feature}"
            module = importlib.import_module(module_name)
            
            # Try common handler class/method patterns
            handler_candidates = [
                "IdeaRecombinator", "Handler", 
                f"{feature.title().replace('_', '')}Handler"
            ]
            
            for class_name in handler_candidates:
                if hasattr(module, class_name):
                    handler_class = getattr(module, class_name)
                    instance = handler_class()
                    
                    # Try common method names
                    for method_name in ["process", "process_request", "handle"]:
                        if hasattr(instance, method_name):
                            method = getattr(instance, method_name)
                            result = self._call_handler_method(method, data, session_id)
                            if result is not None:
                                return {"success": True, "feature": feature, "result": result, "error": None}
            
            return self._error_response(feature, f"No callable handler found in module {module_name}")
            
        except ModuleNotFoundError:
            return self._error_response(feature, f"Unknown feature: {feature}")
        except Exception as e:
            self.logger.exception(f"External handler {feature} failed")
            return self._error_response(feature, str(e))

    def _call_handler_method(self, method: Callable, data: Dict[str, Any], session_id: Optional[str]) -> Any:
        """Try calling handler method with different parameter combinations"""
        for args in [(data, session_id), (data,), ()]:
            try:
                return method(*args)
            except TypeError:
                continue
        return None

    def _error_response(self, feature: str, error: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {"success": False, "feature": feature, "result": None, "error": error}

    def _call_model(self, prompt: str, model: str, max_tokens: int, 
                   temperature: Optional[float] = None, top_p: Optional[float] = None) -> ModelResponse:
        """
        Call the AI model with normalized response handling
        
        Args:
            prompt: Input prompt
            model: Model name
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            
        Returns:
            ModelResponse object with normalized fields
        """
        try:
            params = {"prompt": prompt, "model": model, "max_tokens": max_tokens}
            if temperature is not None:
                params["temperature"] = temperature
            if top_p is not None:
                params["top_p"] = top_p

            # Try different client method names
            if hasattr(self.groq_client, "generate_text"):
                response = self.groq_client.generate_text(**params)
            elif hasattr(self.groq_client, "generate"):
                response = self.groq_client.generate(**params)
            else:
                raise RuntimeError("Groq client missing generate_text or generate method")

            return self._normalize_model_response(response)

        except Exception as e:
            self.logger.exception("Model call failed")
            return ModelResponse(success=False, text="", processing_time=0, error=str(e))

    def _normalize_model_response(self, response: Any) -> ModelResponse:
        """Normalize different response formats to ModelResponse"""
        if not isinstance(response, dict):
            return ModelResponse(success=False, text="", processing_time=0, raw=response)

        text = response.get("text") or response.get("output") or response.get("generated_text") or ""
        success = response.get("success", bool(text)) if isinstance(response.get("success"), bool) else bool(text)
        processing_time = response.get("processing_time", 0)

        return ModelResponse(success=success, text=text, processing_time=processing_time, raw=response)

    def get_generation_params(self, creativity_level: str = "moderate") -> GenerationParams:
        """Get generation parameters for specified creativity level"""
        return self.CREATIVITY_PARAMS.get(creativity_level.lower(), self.CREATIVITY_PARAMS["moderate"])

    # Feature Handlers
    
    def _handle_explain_rewrite(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle text rewriting and explanation requests"""
        text = data.get("text", "")
        target_journal = data.get("target_journal", "Nature")
        language = data.get("language", "American English")

        prompt = self.prompt_templates.get_rewrite_prompt(text=text, journal=target_journal, language=language)
        params = self.get_generation_params(data.get("creativity_level", "moderate"))
        
        response = self._call_model(
            prompt=prompt,
            model=self.DEFAULT_MODELS["explain_rewrite"], 
            max_tokens=4000,
            temperature=params.temperature,
            top_p=params.top_p
        )
        
        if not response.success:
            raise RuntimeError(response.error or "Model generation failed")

        parsed = self.response_parser.parse_rewrite_response(response.text)
        
        return {
            "original_text": text,
            "rewritten_text": parsed.get("rewritten_text", ""),
            "improvements": parsed.get("improvements", ""),
            "target_journal": target_journal,
            "language": language,
            "word_count": len(parsed.get("rewritten_text", "").split()),
            "processing_time": response.processing_time,
        }

    def _handle_protocol_optimizer(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle research protocol optimization"""
        protocol_text = data.get("protocol_text", "")
        research_field = data.get("research_field", "general")
        
        prompt = self.prompt_templates.get_protocol_optimization_prompt(
            protocol=protocol_text, field=research_field
        )
        response = self._call_model(prompt, self.DEFAULT_MODELS["protocol_optimizer"], 3000)
        
        if not response.success:
            raise RuntimeError(response.error or "Model generation failed")

        parsed = self.response_parser.parse_protocol_response(response.text)
        
        return {
            "original_protocol": protocol_text,
            "optimized_protocol": parsed.get("optimized_protocol", ""),
            "improvements": parsed.get("improvements", ""),
            "risk_assessment": parsed.get("risk_assessment", ""),
            "research_field": research_field,
            "processing_time": response.processing_time,
        }

    def _handle_figure_fixer(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle figure analysis and optimization"""
        figure_description = data.get("figure_description", "")
        target_journal = data.get("target_journal", "Nature")
        current_specs = data.get("current_specs", {})

        prompt = self.prompt_templates.get_figure_analysis_prompt(
            description=figure_description, journal=target_journal, specs=current_specs
        )
        response = self._call_model(prompt, self.DEFAULT_MODELS["figure_fixer"], 2000)
        
        if not response.success:
            raise RuntimeError(response.error or "Model generation failed")

        parsed = self.response_parser.parse_figure_response(response.text)
        
        return {
            "analysis": parsed.get("analysis", ""),
            "issues_found": parsed.get("issues", []),
            "recommendations": parsed.get("recommendations", []),
            "target_requirements": parsed.get("requirements", {}),
            "target_journal": target_journal,
            "processing_time": response.processing_time,
        }

    def _handle_citation_context(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle citation analysis and context checking"""
        text = data.get("text", "")
        citation_style = data.get("citation_style", "APA")

        prompt = self.prompt_templates.get_citation_analysis_prompt(text=text, style=citation_style)
        response = self._call_model(prompt, self.DEFAULT_MODELS["citation_context"], 2500)
        
        if not response.success:
            raise RuntimeError(response.error or "Model generation failed")

        parsed = self.response_parser.parse_citation_response(response.text)
        
        return {
            "citations_found": parsed.get("citations", []),
            "context_analysis": parsed.get("context", []),
            "missing_citations": parsed.get("missing", []),
            "style_issues": parsed.get("style_issues", []),
            "citation_style": citation_style,
            "processing_time": response.processing_time,
        }

    def _handle_idea_recombinator(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle idea recombination and synthesis"""
        sources = data.get("sources", [])
        research_question = data.get("research_question", "")

        prompt = self.prompt_templates.get_idea_recombination_prompt(
            sources=sources, question=research_question
        )
        params = self.get_generation_params(data.get("creativity_level", "moderate"))
        
        response = self._call_model(
            prompt=prompt,
            model=self.DEFAULT_MODELS["idea_recombinator"],
            max_tokens=3500,
            temperature=params.temperature,
            top_p=params.top_p
        )
        
        if not response.success:
            raise RuntimeError(response.error or "Model generation failed")

        parsed = self.response_parser.parse_recombination_response(response.text)
        
        return {
            "novel_ideas": parsed.get("ideas", []),
            "combinations": parsed.get("combinations", []),
            "research_gaps": parsed.get("gaps", []),
            "methodology_suggestions": parsed.get("methods", []),
            "research_question": research_question,
            "processing_time": response.processing_time,
        }

    def _handle_contradiction_detector(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle contradiction detection and logical analysis"""
        text = data.get("text", "")
        check_type = data.get("check_type", "internal")
        
        prompt = self.prompt_templates.get_contradiction_detection_prompt(
            text=text, check_type=check_type
        )
        response = self._call_model(prompt, self.DEFAULT_MODELS["contradiction_detector"], 2500)
        
        if not response.success:
            raise RuntimeError(response.error or "Model generation failed")

        parsed = self.response_parser.parse_contradiction_response(response.text)
        
        return {
            "contradictions": parsed.get("contradictions", []),
            "logical_issues": parsed.get("logical_issues", []),
            "consistency_score": parsed.get("consistency_score"),
            "recommendations": parsed.get("recommendations", []),
            "check_type": check_type,
            "processing_time": response.processing_time,
        }

    def health_check(self) -> Dict[str, Any]:
        """Check if AI service is available and responsive"""
        try:
            response = self._call_model("Test connection", "llama3-8b-8192", 10)
            status = "healthy" if response.success else "unhealthy"
            
            return {
                "status": status,
                "service": "groq",
                "model_available": response.success,
                "response_time": response.processing_time
            }
        except Exception as e:
            self.logger.exception("Health check failed")
            return {"status": "unhealthy", "service": "groq", "error": str(e)}

    def get_supported_features(self) -> List[str]:
        """Get list of supported features"""
        return list(self.feature_handlers.keys())

    def get_feature_info(self, feature: str) -> Dict[str, Any]:
        """Get information about a specific feature"""
        if feature not in self.feature_handlers:
            return {"error": f"Feature '{feature}' not found"}
            
        return {
            "feature": feature,
            "model": self.DEFAULT_MODELS.get(feature, "default"),
            "supported": True,
            "handler_type": "internal"
        }
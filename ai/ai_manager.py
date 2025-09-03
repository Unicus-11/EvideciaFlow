"""
AI Manager for Research Platform
Handles AI client selection and routing to appropriate features
"""

import os
import importlib
import logging
from typing import Dict, Any, Optional, Tuple

# Try multiple possible import paths for GroqClient / templates / parser
_GROQ_CLIENT_IMPORT_PATHS = [
    "groq_client",
    "backend.ai.groq_client",
    "backend.ai.groq_client.groq_client",  # if nested
]
_PROMPT_TEMPLATES_IMPORT_PATHS = [
    "prompt_templates",
    "backend.ai.prompt_templates",
]
_RESPONSE_PARSER_IMPORT_PATHS = [
    "response_parser",
    "backend.ai.response_parser",
]


def _try_import(paths: list, name: str):
    """Try import from several candidate module paths. Return module/class or raise ImportError."""
    last_exc = None
    for p in paths:
        try:
            mod = importlib.import_module(p)
            return mod
        except Exception as e:
            last_exc = e
            continue
    raise ImportError(f"Could not import {name}. Tried: {paths}. Last error: {last_exc}")


class AIManager:
    """Central manager for all AI operations in the research platform"""

    def __init__(self, api_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv("GROQ_API_KEY")

        # Strict original behavior: require API key
        if not self.api_key:
            raise ValueError("Groq API key not found. Set GROQ_API_KEY environment variable.")

        # Initialize groq client, prompt templates, and response parser (fail fast with helpful messages)
        try:
            groq_mod = _try_import(_GROQ_CLIENT_IMPORT_PATHS, "GroqClient")
            GroqClient = getattr(groq_mod, "GroqClient", None) or getattr(groq_mod, "Client", None)
            if GroqClient is None:
                raise ImportError("GroqClient class not found in groq_client module.")
            self.groq_client = GroqClient(self.api_key)
        except Exception as e:
            self.logger.exception("Failed to initialize GroqClient")
            raise

        try:
            pt_mod = _try_import(_PROMPT_TEMPLATES_IMPORT_PATHS, "PromptTemplates")
            PromptTemplates = getattr(pt_mod, "PromptTemplates", None)
            if PromptTemplates is None:
                raise ImportError("PromptTemplates class not found in prompt_templates module.")
            self.prompt_templates = PromptTemplates()
        except Exception as e:
            self.logger.exception("Failed to initialize PromptTemplates")
            raise

        try:
            rp_mod = _try_import(_RESPONSE_PARSER_IMPORT_PATHS, "ResponseParser")
            ResponseParser = getattr(rp_mod, "ResponseParser", None)
            if ResponseParser is None:
                raise ImportError("ResponseParser class not found in response_parser module.")
            self.response_parser = ResponseParser()
        except Exception as e:
            self.logger.exception("Failed to initialize ResponseParser")
            raise

        # Feature routing: prefer internal handler methods; these methods are defined on this class
        # If you later want external modules, the process_request fallback will attempt dynamic import.
        self.feature_handlers = {
            "explain_rewrite": self._handle_explain_rewrite,
            "protocol_optimizer": self._handle_protocol_optimizer,
            "figure_fixer": self._handle_figure_fixer,
            "citation_context": self._handle_citation_context,
            "idea_recombinator": self._handle_idea_recombinator,
            "contradiction_detector": self._handle_contradiction_detector,
        }

    # -------------------- Public API --------------------
    def process_request(self, feature: str, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Route request to appropriate feature handler.

        Returns a normalized dict:
          { 'success': bool, 'feature': str, 'result': Any, 'error': Optional[str] }
        """
        feature_key = (feature or "").strip().lower()
        if not feature_key:
            return {"success": False, "feature": feature, "result": None, "error": "feature is required"}

        handler = self.feature_handlers.get(feature_key)
        if handler:
            try:
                result = handler(data, session_id)
                return {"success": True, "feature": feature_key, "result": result, "error": None}
            except Exception as e:
                self.logger.exception("Handler raised an exception")
                return {"success": False, "feature": feature_key, "result": None, "error": str(e)}

        # Fallback: attempt to import an external handler module named backend.features.<feature>
        try:
            module_name = f"backend.features.{feature_key}"
            module = importlib.import_module(module_name)
            # try common entry points
            for candidate in ("IdeaRecombinator", "Handler", f"{feature_key.title().replace('_', '')}Handler"):
                if hasattr(module, candidate):
                    cls = getattr(module, candidate)
                    inst = cls()
                    # Try call with common method names
                    for m in ("process", "process_request", "process_idea_generation_request", "handle"):
                        if hasattr(inst, m):
                            method = getattr(inst, m)
                            try:
                                return {"success": True, "feature": feature_key, "result": method(data, session_id), "error": None}
                            except TypeError:
                                try:
                                    return {"success": True, "feature": feature_key, "result": method(data), "error": None}
                                except TypeError:
                                    try:
                                        return {"success": True, "feature": feature_key, "result": method(), "error": None}
                                    except TypeError:
                                        continue
            return {"success": False, "feature": feature_key, "result": None, "error": f"No callable handler found in module {module_name}"}
        except ModuleNotFoundError:
            return {"success": False, "feature": feature_key, "result": None, "error": f"Unknown feature: {feature_key}"}
        except Exception as e:
            self.logger.exception("Error while importing external handler")
            return {"success": False, "feature": feature_key, "result": None, "error": str(e)}

    # -------------------- Model caller helper --------------------
    def _call_model(self, prompt: str, model: str, max_tokens: int, temperature: Optional[float] = None, top_p: Optional[float] = None) -> Dict[str, Any]:
        """
        Call the groq client and normalize the response.
        Expected groq_client.generate_text(prompt, model, max_tokens, **kwargs)
        Returns: { 'success': bool, 'text': str, 'processing_time': float, 'raw': ... }
        """
        try:
            params = {"prompt": prompt, "model": model, "max_tokens": max_tokens}
            if temperature is not None:
                params["temperature"] = temperature
            if top_p is not None:
                params["top_p"] = top_p

            # many groq clients use generate_text or generate; adapt if needed
            if hasattr(self.groq_client, "generate_text"):
                resp = self.groq_client.generate_text(**params)
            elif hasattr(self.groq_client, "generate"):
                resp = self.groq_client.generate(**params)
            else:
                raise RuntimeError("Groq client does not expose generate_text or generate")

            # Normalize common response shapes
            if not isinstance(resp, dict):
                return {"success": False, "text": "", "raw": resp, "processing_time": 0}

            text = resp.get("text") or resp.get("output") or resp.get("generated_text") or ""
            success = resp.get("success", True) if isinstance(resp.get("success", True), bool) else bool(text)
            return {"success": success, "text": text, "raw": resp, "processing_time": resp.get("processing_time", 0)}
        except Exception as e:
            self.logger.exception("Model call failed")
            return {"success": False, "text": "", "raw": None, "processing_time": 0, "error": str(e)}

    # -------------------- Handlers --------------------
    def _handle_explain_rewrite(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        text = data.get("text", "")
        target_journal = data.get("target_journal", "Nature")
        language = data.get("language", "American English")

        prompt = self.prompt_templates.get_rewrite_prompt(text=text, journal=target_journal, language=language)
        gen_params = self.compute_generation_params(data.get("creativity_level", "moderate"))
        model_resp = self._call_model(prompt, model="llama3-70b-8192", max_tokens=4000, temperature=gen_params.get("temperature"), top_p=gen_params.get("top_p"))
        if not model_resp.get("success"):
            raise RuntimeError(model_resp.get("error") or "Model generation failed")

        parsed = self.response_parser.parse_rewrite_response(model_resp["text"])
        return {
            "original_text": text,
            "rewritten_text": parsed.get("rewritten_text", ""),
            "improvements": parsed.get("improvements", ""),
            "target_journal": target_journal,
            "language": language,
            "word_count": len(parsed.get("rewritten_text", "").split()),
            "processing_time": model_resp.get("processing_time", 0),
        }

    def _handle_protocol_optimizer(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        protocol_text = data.get("protocol_text", "")
        research_field = data.get("research_field", "general")
        prompt = self.prompt_templates.get_protocol_optimization_prompt(protocol=protocol_text, field=research_field)
        model_resp = self._call_model(prompt, model="llama3-70b-8192", max_tokens=3000)
        if not model_resp.get("success"):
            raise RuntimeError(model_resp.get("error") or "Model generation failed")

        parsed = self.response_parser.parse_protocol_response(model_resp["text"])
        return {
            "original_protocol": protocol_text,
            "optimized_protocol": parsed.get("optimized_protocol", ""),
            "improvements": parsed.get("improvements", ""),
            "risk_assessment": parsed.get("risk_assessment", ""),
            "research_field": research_field,
        }

    def _handle_figure_fixer(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        figure_description = data.get("figure_description", "")
        target_journal = data.get("target_journal", "Nature")
        current_specs = data.get("current_specs", {})

        prompt = self.prompt_templates.get_figure_analysis_prompt(description=figure_description, journal=target_journal, specs=current_specs)
        model_resp = self._call_model(prompt, model="llama3-8b-8192", max_tokens=2000)
        if not model_resp.get("success"):
            raise RuntimeError(model_resp.get("error") or "Model generation failed")

        parsed = self.response_parser.parse_figure_response(model_resp["text"])
        return {
            "analysis": parsed.get("analysis", ""),
            "issues_found": parsed.get("issues", []),
            "recommendations": parsed.get("recommendations", []),
            "target_requirements": parsed.get("requirements", {}),
            "target_journal": target_journal,
        }

    def _handle_citation_context(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        text = data.get("text", "")
        citation_style = data.get("citation_style", "APA")

        prompt = self.prompt_templates.get_citation_analysis_prompt(text=text, style=citation_style)
        model_resp = self._call_model(prompt, model="llama3-70b-8192", max_tokens=2500)
        if not model_resp.get("success"):
            raise RuntimeError(model_resp.get("error") or "Model generation failed")

        parsed = self.response_parser.parse_citation_response(model_resp["text"])
        return {
            "citations_found": parsed.get("citations", []),
            "context_analysis": parsed.get("context", []),
            "missing_citations": parsed.get("missing", []),
            "style_issues": parsed.get("style_issues", []),
            "citation_style": citation_style,
        }

    def _handle_idea_recombinator(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        sources = data.get("sources", [])
        research_question = data.get("research_question", "")

        prompt = self.prompt_templates.get_idea_recombination_prompt(sources=sources, question=research_question)
        gen_params = self.compute_generation_params(data.get("creativity_level", "moderate"))
        model_resp = self._call_model(prompt, model="llama3-70b-8192", max_tokens=3500, temperature=gen_params.get("temperature"), top_p=gen_params.get("top_p"))
        if not model_resp.get("success"):
            raise RuntimeError(model_resp.get("error") or "Model generation failed")

        parsed = self.response_parser.parse_recombination_response(model_resp["text"])
        return {
            "novel_ideas": parsed.get("ideas", []),
            "combinations": parsed.get("combinations", []),
            "research_gaps": parsed.get("gaps", []),
            "methodology_suggestions": parsed.get("methods", []),
            "research_question": research_question,
        }

    def _handle_contradiction_detector(self, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        text = data.get("text", "")
        check_type = data.get("check_type", "internal")
        prompt = self.prompt_templates.get_contradiction_detection_prompt(text=text, check_type=check_type)
        model_resp = self._call_model(prompt, model="llama3-70b-8192", max_tokens=2500)
        if not model_resp.get("success"):
            raise RuntimeError(model_resp.get("error") or "Model generation failed")

        parsed = self.response_parser.parse_contradiction_response(model_resp["text"])
        return {
            "contradictions": parsed.get("contradictions", []),
            "logical_issues": parsed.get("logical_issues", []),
            "consistency_score": parsed.get("consistency_score", None),
            "recommendations": parsed.get("recommendations", []),
            "check_type": check_type,
        }

    # -------------------- Utilities --------------------
    def health_check(self) -> Dict[str, Any]:
        """Check if AI service is available"""
        try:
            test_resp = self._call_model(prompt="Test connection", model="llama3-8b-8192", max_tokens=10)
            status = "healthy" if test_resp.get("success") else "unhealthy"
            return {"status": status, "service": "groq", "model_available": test_resp.get("success")}
        except Exception as e:
            self.logger.exception("Health check failed")
            return {"status": "unhealthy", "service": "groq", "error": str(e)}

    def compute_generation_params(self, creativity_level: str) -> Dict[str, Any]:
        mapping = {
            "low": {"temperature": 0.2, "top_p": 0.6},
            "moderate": {"temperature": 0.6, "top_p": 0.9},
            "high": {"temperature": 0.95, "top_p": 0.95},
        }
        return mapping.get(str(creativity_level).lower(), mapping["moderate"])

"""
Unified model client supporting both LM Studio (local) and Anthropic API models.
"""
import time
import json
import requests
import os
from pathlib import Path


class ModelClient:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "models.json"
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.lm_studio_endpoint = self.config["lm_studio_endpoint"]
        self.models = self.config["models"]
        
        # Initialize Anthropic client if API key is available
        self.anthropic_client = None
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                from anthropic import Anthropic
                self.anthropic_client = Anthropic(api_key=api_key)
            except ImportError:
                print("Warning: anthropic package not installed. Install with: pip install anthropic")
    
    def chat(self, model_alias: str, messages: list, temperature: float = None, max_tokens: int = None):
        """
        Send a chat completion request to either LM Studio or Anthropic API.
        
        Args:
            model_alias: Model alias (e.g., "claude-opus", "glm-flash")
            messages: List of message dicts [{"role": "user/assistant/system", "content": "..."}]
            temperature: Optional override
            max_tokens: Optional override
        
        Returns:
            dict with keys: success, content, error, latency_ms, usage
        """
        if model_alias not in self.models:
            return {
                "success": False,
                "content": None,
                "error": f"Unknown model alias: {model_alias}",
                "latency_ms": 0,
                "usage": None
            }
        
        model_config = self.models[model_alias]
        model_type = model_config.get("type", "lm_studio")
        
        if model_type == "anthropic":
            return self._call_anthropic(model_alias, messages, temperature, max_tokens)
        else:
            return self._call_lm_studio(model_alias, messages, temperature, max_tokens)
    
    def _call_anthropic(self, model_alias: str, messages: list, temperature: float = None, max_tokens: int = None):
        """Call Anthropic API (Claude models)."""
        if not self.anthropic_client:
            return {
                "success": False,
                "content": None,
                "error": "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable.",
                "latency_ms": 0,
                "usage": None
            }
        
        model_config = self.models[model_alias]
        model_id = model_config["id"]
        
        temp = temperature if temperature is not None else model_config.get("temperature", 0.7)
        max_tok = max_tokens if max_tokens is not None else model_config.get("max_tokens", 4096)
        
        # Convert messages format - Anthropic requires system message separate
        system_message = None
        converted_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                converted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        try:
            start_time = time.time()
            
            kwargs = {
                "model": model_id,
                "max_tokens": max_tok,
                "temperature": temp,
                "messages": converted_messages
            }
            
            if system_message:
                kwargs["system"] = system_message
            
            response = self.anthropic_client.messages.create(**kwargs)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract text content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text
            
            return {
                "success": True,
                "content": content,
                "error": None,
                "latency_ms": latency_ms,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "content": None,
                "error": str(e),
                "latency_ms": 0,
                "usage": None
            }
    
    def _call_lm_studio(self, model_alias: str, messages: list, temperature: float = None, max_tokens: int = None):
        """Call LM Studio (local models)."""
        model_config = self.models[model_alias]
        model_id = model_config["id"]
        
        temp = temperature if temperature is not None else model_config.get("temperature", 0.3)
        max_tok = max_tokens if max_tokens is not None else model_config.get("max_tokens", 512)
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok
        }
        
        try:
            start_time = time.time()
            response = requests.post(self.lm_studio_endpoint, json=payload, timeout=120)
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "content": content,
                    "error": None,
                    "latency_ms": latency_ms,
                    "usage": data.get("usage")
                }
            else:
                return {
                    "success": False,
                    "content": None,
                    "error": f"LM Studio returned status {response.status_code}: {response.text}",
                    "latency_ms": latency_ms,
                    "usage": None
                }
        
        except Exception as e:
            return {
                "success": False,
                "content": None,
                "error": str(e),
                "latency_ms": 0,
                "usage": None
            }

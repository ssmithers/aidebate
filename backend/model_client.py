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
        """
        Call Anthropic API (Claude models) via DALS bridge.

        Routes through bridge.py to use subscription credits first, then API key.
        """
        import hashlib
        from pathlib import Path

        model_config = self.models[model_alias]

        temp = temperature if temperature is not None else model_config.get("temperature", 0.7)
        max_tok = max_tokens if max_tokens is not None else model_config.get("max_tokens", 4096)

        # Bridge communication files
        bridge_base = Path("/Users/ssmithers/Desktop/CODE/dals")
        passon_file = bridge_base / "passon.md"
        response_file = bridge_base / "response.md"

        # Extract debate context from messages
        system_message = None
        conversation = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                conversation.append(msg["content"])

        # Parse debate parameters from system message
        topic = "Unknown topic"
        position = "Unknown position"
        speech_type = "speech"

        if system_message:
            # Extract topic (after "debate on: '")
            if "debate on:" in system_message or "topic:" in system_message.lower():
                import re
                topic_match = re.search(r"(?:debate on|topic):\s*['\"]([^'\"]+)['\"]", system_message, re.IGNORECASE)
                if topic_match:
                    topic = topic_match.group(1)

            # Determine position
            if "AFFIRMATIVE" in system_message or "affirmative" in system_message.lower():
                position = "Affirmative (Pro)"
            elif "NEGATIVE" in system_message or "negative" in system_message.lower():
                position = "Negative (Con)"

            # Determine speech type
            if "CONSTRUCTIVE" in system_message:
                speech_type = "constructive"
            elif "CROSS-EXAMINATION" in system_message or "cx_question" in system_message:
                speech_type = "cross-examination question"
            elif "ANSWERING cross-examination" in system_message or "cx_answer" in system_message:
                speech_type = "cross-examination answer"
            elif "REBUTTAL" in system_message:
                speech_type = "rebuttal"

        # Build DALS task request
        request = (
            "## DALS Task: Generate Debate Content for AI Debate Simulator\n\n"
            f"**Project**: AI Debate Simulator (aidebate)\n"
            f"**Topic**: {topic}\n"
            f"**Position**: {position}\n"
            f"**Speech Type**: {speech_type}\n"
            f"**Settings**: temperature={temp}, max_tokens={max_tok}\n\n"
            "**Task**: Generate a debate argument for this position and speech type. "
        )

        # Add previous conversation context if exists
        if conversation:
            request += f"\n\n**Previous exchanges in this debate**:\n"
            for i, msg in enumerate(conversation[-3:], 1):  # Last 3 exchanges for context
                preview = msg[:200] + "..." if len(msg) > 200 else msg
                request += f"\n{i}. {preview}\n"

        request += (
            "\n\n**Instructions**:\n"
            "- Provide a concise, well-structured argument\n"
            "- Use [Source: ...] format for citations\n"
            "- Match the tone and style appropriate for policy debate\n"
            "- Return only the debate content, no meta-commentary\n"
        )

        request_message = request

        # Helper to get file hash
        def get_file_hash(path):
            if not path.exists():
                return ""
            return hashlib.md5(path.read_text().encode()).hexdigest()

        # Get current response.md hash before writing
        old_response_hash = get_file_hash(response_file)

        # Write request to passon.md
        passon_file.write_text(request_message)
        print(f"[Bridge] Debate request sent to Opus via bridge")

        # Wait for response.md to update (poll with timeout)
        timeout = 120  # 2 minutes for debate responses (longer than formatting)
        poll_interval = 2
        elapsed = 0
        start_time = time.time()

        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval

            current_hash = get_file_hash(response_file)
            if current_hash and current_hash != old_response_hash:
                # Response received!
                response_text = response_file.read_text()

                # Strip bridge header and metadata
                lines = response_text.split('\n')
                content_lines = []
                usage_info = None

                for line in lines:
                    # Extract token usage if present
                    if '*[Opus' in line and 'tokens]*' in line:
                        # Parse: *[Opus 4.6 | 1234 in / 5678 out tokens]*
                        import re
                        match = re.search(r'(\d+) in / (\d+) out', line)
                        if match:
                            usage_info = {
                                "input_tokens": int(match.group(1)),
                                "output_tokens": int(match.group(2))
                            }
                        continue

                    # Skip HTML comments
                    if line.strip().startswith('<!--'):
                        continue

                    content_lines.append(line)

                content = '\n'.join(content_lines).strip()
                latency_ms = int((time.time() - start_time) * 1000)

                print(f"[Bridge] Opus debate response received via bridge (subscription)")

                return {
                    "success": True,
                    "content": content,
                    "error": None,
                    "latency_ms": latency_ms,
                    "usage": usage_info
                }

        # Timeout
        print(f"[Bridge] ⚠️  WARNING: No Opus response after {timeout}s")
        print(f"[Bridge] ⚠️  Is bridge.py running? Check: ps aux | grep bridge.py")

        return {
            "success": False,
            "content": None,
            "error": f"Bridge timeout after {timeout}s. Is bridge.py running?",
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

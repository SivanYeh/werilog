import os
import requests
import time

def load_config_yaml():
    config = {}
    config_path = "config.yaml"
    if not os.path.exists(config_path) and os.path.exists("../config.yaml"):
        config_path = "../config.yaml"
    try:
        with open(config_path, "r") as f:
            current_section = None
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.endswith(":"):
                    current_section = line[:-1].strip()
                    config[current_section] = {}
                elif ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if current_section:
                        config[current_section][key] = val
                    else:
                        config[key] = val
    except Exception:
        pass
    return config

def load_env():
    env_path = ".env"
    if not os.path.exists(env_path) and os.path.exists("../.env"):
        env_path = "../.env"
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")
    except Exception:
        pass

class VerilogAgent:
    def __init__(self, model_name="dummy-model"):
        self.config = load_config_yaml()
        load_env()
        self.inference_config = self.config.get("inference", {})
        self.backend = self.inference_config.get("backend", "ollama").lower()
        self.model_name = self.inference_config.get("model", "qwen2.5-coder:1.5b")
        self.last_error_time = 0
        self.cooldown_period = 15  # seconds

    def infer_json(self, verilog_text):
        """
        Simulates an LLM agent translating Verilog to the required JSON structure.
        In a real scenario, this would call an API like OpenAI, Anthropic, or Google Gemini.
        """
        print(f"[Agent] Using dummy model to parse Verilog...")
        import time
        time.sleep(1)
        
        print("[Agent] Inference complete (simulated).")
        return [
            {
                "type": "module",
                "name": "agent_inferred_module",
                "ports": [
                    {"type": "port", "name": "in_a", "direction": "input"},
                    {"type": "port", "name": "out_b", "direction": "output"}
                ],
                "elements": [
                    {"type": "element", "op": "buffer", "in": ["in_a"], "out": "out_b"}
                ],
                "wires": [
                    {"type": "wire", "target": "out_b", "source": "buffer_out_b"}
                ]
            }
        ]

    def suggest_completion(self, prefix, suffix="", errors=None):
        """
        Calls the LLM backend to suggest a code completion based on the prefix and any syntax errors.
        Returns a string suggestion.
        """
        if not prefix.strip():
            return ""

        # Check if we are currently in a cooldown period due to a previous error
        current_time = time.time()
        if current_time - self.last_error_time < self.cooldown_period:
            return ""

        print(f"[Agent] Requesting completion using backend: {self.backend}, model: {self.model_name}")

        # Construct dynamic prompt
        if errors and len(errors) > 0:
            error_details = "\n".join([str(e) for e in errors])
            prompt_content = (f"The following Verilog code snippet contains these syntax errors:\n{error_details}\n\n"
                              f"Please provide the necessary code completion to fix these errors. "
                              f"Do not include markdown formatting or explanations, just provide the raw code completion starting from the end of this prefix:\n\n{prefix}")
        else:
            prompt_content = f"Please complete the following Verilog code snippet. Do not include markdown formatting or explanations, just provide the raw code completion starting from the end of this prefix:\n\n{prefix}"

        try:
            if self.backend == "huggingface":
                api_key = os.environ.get("HUGGINGFACE_API_KEY")
                if not api_key:
                    self.last_error_time = current_time
                    print("[Agent] Error: HUGGINGFACE_API_KEY not found in .env. Cooldown active.")
                    return ""
                
                # Using the Inference Providers API (OpenAI compatible)
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                api_url = "https://router.huggingface.co/v1/chat/completions"
                
                # OpenAI-compatible schema for text completion
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "user", "content": prompt_content}
                    ],
                    "max_tokens": 50,
                    "temperature": 0.2,
                    "stop": ["\n"]
                }
                
                response = requests.post(api_url, headers=headers, json=payload, timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    choices = result.get("choices", [])
                    if choices and len(choices) > 0:
                        content = choices[0].get("message", {}).get("content", "")
                        return content.strip()
                else:
                    self.last_error_time = time.time()
                    print(f"[Agent] HuggingFace API error {response.status_code}: {response.text}. Cooldown active.")
                    return ""

            elif self.backend == "ollama":
                # Ollama local API
                api_url = "http://localhost:11434/api/generate"
                payload = {
                    "model": self.model_name,
                    "prompt": prompt_content,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 50,
                        "stop": ["\n"]
                    }
                }
                response = requests.post(api_url, json=payload, timeout=5)
                if response.status_code == 200:
                    return response.json().get("response", "")
                else:
                    self.last_error_time = time.time()
                    print(f"[Agent] Ollama API error {response.status_code}. Cooldown active.")
                    return ""
            else:
                self.last_error_time = time.time()
                print(f"[Agent] Unknown backend: {self.backend}. Cooldown active.")
                return ""
                
        except requests.exceptions.ConnectionError:
            self.last_error_time = time.time()
            if self.backend == "huggingface":
                print(f"[Agent] Connection error: HuggingFace API is unreachable. Please check your internet connection. (Cooldown active for {self.cooldown_period}s)")
            elif self.backend == "ollama":
                print(f"[Agent] Connection error: Local Ollama is unreachable. Is Ollama running on {api_url}? (Cooldown active for {self.cooldown_period}s)")
            else:
                print(f"[Agent] Connection error for {self.backend}. (Cooldown active for {self.cooldown_period}s)")
            return ""
        except Exception as e:
            self.last_error_time = time.time()
            print(f"[Agent] Exception during completion: {e}. (Cooldown active for {self.cooldown_period}s)")
            return ""

if __name__ == "__main__":
    agent = VerilogAgent()
    
    # Simulate a syntax error to test prompt injection
    class DummyError:
        def __str__(self):
            return "Line 1: [ERROR] Unclosed module declaration."
            
    test_errors = [DummyError()]
    completion = agent.suggest_completion("module test(input in_a, ", errors=test_errors)
    print("Agent Completion Suggestion:", completion)

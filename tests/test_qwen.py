import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from huggingface_hub.utils import RepositoryNotFoundError, HfHubHTTPError

# 1. Load environment variables from the .env file
load_dotenv()

# 2. Retrieve the token safely
hf_token = os.getenv("HUGGINGFACE_API_KEY")

if not hf_token:
    raise ValueError("Error: HUGGINGFACE_API_KEY not found in .env file.")

# 3. Initialize the Inference Client with the Qwen Coder model
MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B"
client = InferenceClient(model=MODEL_ID, token=hf_token)

# Example prompt matching your 'verilog-backward' project context
prompt = """// Verilog module for a 4-bit synchronous binary counter with asynchronous reset
module counter (
    input clk,
    input rst,
    output reg [3:0] out
);
"""

print(f"[Agent] Requesting completion from free API using backend: huggingface")
print(f"[Agent] Model: {MODEL_ID}\n" + "-"*50)

try:
    # 4. Request text generation from the free serverless endpoint
    # We use a low temperature to keep code completions deterministic and precise
    response = client.text_generation(
        prompt, 
        max_new_tokens=150, 
        temperature=0.1
    )
    
    print("Agent Completion Suggestion:")
    print(prompt + response)

except HfHubHTTPError as e:
    # Captures 401 (Invalid Token), 429 (Rate Limit), or 503 (Model Loading)
    print(f"\n[Agent] API Error: {e}")
    print("[Agent] Hint: Check if your network/DNS issue is resolved, or if you hit the free tier rate limit.")
except Exception as e:
    print(f"\n[Agent] An unexpected error occurred: {e}")
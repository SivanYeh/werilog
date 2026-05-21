import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from agent.core import VerilogAgent

def test_d_flip_flop():
    agent = VerilogAgent()
    # Scenario: The user started a D-FF but stopped inside the always block
    context = """
    module d_ff (input clk, input d, output reg q);
        always @(posedge clk) begin
    """
    
    completion = agent.generate_completion(context)
    
    # Simple check: Does it contain the non-blocking assignment?
    if "<=" in completion and "q" in completion:
        print("✅ Test Passed: Basic logic found.")
    else:
        print("❌ Test Failed: Logic missing.")

if __name__ == "__main__":
    test_d_flip_flop()

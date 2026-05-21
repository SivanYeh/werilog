def load_verilog_sample(file_path):
    """Utility for AgentTeam to load large datasets for testing."""
    with open(file_path, 'r') as f:
        return f.read()

# Example usage for AgentTeam:
# samples = load_verilog_sample("data/open_cores_sample.v")

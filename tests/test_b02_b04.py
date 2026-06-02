import json
from werilog.editor.extractverilog import extract_verilog

def test_file(filepath):
    print(f"--- Testing extraction on {filepath} ---")
    try:
        with open(filepath, "r") as f:
            verilog_text = f.read()
            
        modules = extract_verilog(verilog_text)
        print(f"Extracted {len(modules)} modules from {filepath}")
        print(json.dumps([m.to_dict() for m in modules], indent=2))
        print("------------------------------------------\n")
    except Exception as e:
        print(f"Failed to test {filepath}: {e}\n")

if __name__ == "__main__":
    import os
    # test_file("dataset/example-verilog/basic/b02.v")
    # test_file("dataset/example-verilog/basic/b04.v")
    test_file("dataset/example-verilog/connect/c01.v")

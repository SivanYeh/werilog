import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from werilog.agent.diagram_analyzer import DiagramAnalyzer


def test_image(filename):
    print(f"Loading image: {filename}")
    with DiagramAnalyzer() as analyzer:
        print("Analyzer created.")
        ds = analyzer.call_agent(
        image_path=filename,
        max_new_tokens=8192
    )

    print(ds)

if __name__ == "__main__":
    test_image("dataset/example-images/example-b01_2.png")

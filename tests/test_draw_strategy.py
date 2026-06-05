import sys
import argparse
from werilog.editor.draw_strategy import SquareWireStrategy, JumpWireStrategy, StraightWireStrategy

def run_tests(show_window=False):
    # Create a simple routing scenario
    start = (50, 100)
    end = (350, 100)
    
    # Existing wire: vertical line crossing at x = 200, from y = 50 to y = 150
    existing_wires = [
        [(200, 50), (200, 150)]
    ]
    
    # 1. Test SquareWireStrategy
    square_strategy = SquareWireStrategy()
    square_path = square_strategy.route(start, end)
    print("Square Strategy Path:", square_path)
    
    # 1.5. Test StraightWireStrategy
    straight_strategy = StraightWireStrategy()
    straight_path = straight_strategy.route(start, end)
    print("Straight Strategy Path:", straight_path)
    assert straight_path == [start, end], f"Expected straight path {[start, end]}, got {straight_path}"
    print("Straight path assertions passed successfully!")
    
    # 2. Test JumpWireStrategy
    jump_strategy = JumpWireStrategy(square_strategy)
    res = jump_strategy.route(start, end, existing_wires)
    path = res["path"]
    jumps = res["jumps"]
    print("Jump Strategy Path:", path)
    print("Detected Jump Points:", jumps)
    
    # Assertions for headless automated unit testing
    assert len(path) == 2, "Orthogonal path should have 2 points after simplification for straight line"
    assert len(jumps) == 1, "There should be exactly 1 intersection point detected"
    assert jumps[0] == (200, 100), f"Intersection should be at (200, 100), got {jumps[0]}"
    print("Collinear test assertions passed successfully!")
    
    # 3. Test Offset Path Routing
    start_offset = (50, 100)
    end_offset = (350, 200)
    existing_wires_offset = [
        [(120, 50), (120, 150)]  # Crosses first segment at x = 120, y = 100
    ]
    res_offset = jump_strategy.route(start_offset, end_offset, existing_wires_offset)
    path_offset = res_offset["path"]
    jumps_offset = res_offset["jumps"]
    print("Offset Strategy Path:", path_offset)
    print("Detected Offset Jump Points:", jumps_offset)
    
    assert len(path_offset) == 4, "Orthogonal path with vertical offset should have 4 points"
    assert len(jumps_offset) == 1, "There should be exactly 1 intersection point detected on offset path"
    assert jumps_offset[0] == (120, 100), f"Intersection should be at (120, 100), got {jumps_offset[0]}"
    print("Offset test assertions passed successfully!")
    
    print("All assertions passed successfully!")
    
    if show_window:
        import tkinter as tk
        root = tk.Tk()
        root.title("Routing & Jump Visualizer")
        root.geometry("400x200")
        
        canvas = tk.Canvas(root, width=400, height=200, bg="#1e1e1e")
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw existing wire (vertical crossing line in light grey)
        for old_path in existing_wires:
            coords = [c for pt in old_path for c in pt]
            canvas.create_line(*coords, fill="#555555", width=2)
            canvas.create_text(200, 40, text="Existing Wire", fill="#888888")
            
        # Draw routed path with a visual skip/arc at the jump point (200, 100)
        # Bounding box of the arc at (200, 100) is (194, 94, 206, 106)
        # Line 1: (50, 100) to (194, 100)
        # Arc: (194, 94, 206, 106) semi-circle skip
        # Line 2: (206, 100) to (350, 100)
        canvas.create_line(50, 100, 194, 100, fill="#c586c0", width=3)
        canvas.create_arc(194, 94, 206, 106, start=0, extent=180, outline="#c586c0", width=3, style=tk.ARC)
        canvas.create_line(206, 100, 350, 100, fill="#c586c0", width=3)
        
        # Draw start & end dots with labels
        canvas.create_oval(46, 96, 54, 104, fill="#ffcc00", outline="white")
        canvas.create_text(50, 120, text="Start (50, 100)", fill="white")
        canvas.create_oval(346, 96, 354, 104, fill="#ffcc00", outline="white")
        canvas.create_text(350, 120, text="End (350, 100)", fill="white")
        
        root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Wire Routing Strategies")
    parser.add_argument("--window", action="store_true", help="Launch Tkinter window to visually inspect jump routing")
    args = parser.parse_args()
    run_tests(show_window=args.window)

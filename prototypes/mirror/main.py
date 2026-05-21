import tkinter as tk
import re

class HDLEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bidirectional HDL & Diagram Editor")
        self.geometry("900x500")

        # --- Application State (The "Source of Truth") ---
        self.block_x = 200
        self.block_y = 250
        self.block_size = 100
        self.has_block = True
        self.is_connected = False
        
        # Interaction state
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.wiring = False
        self.temp_wire = None

        # --- UI Layout ---
        # Split window into Left (Canvas) and Right (Text)
        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Left Panel: Diagram Canvas
        self.canvas = tk.Canvas(self.paned_window, bg="#1e1e1e", width=450)
        self.paned_window.add(self.canvas)

        # Right Panel: Text Editor
        self.text_editor = tk.Text(self.paned_window, width=50, bg="#2d2d2d", fg="#d4d4d4", 
                                   font=("Courier New", 12), insertbackground="white")
        self.paned_window.add(self.text_editor)

        # --- Event Bindings ---
        # Canvas events for dragging and wiring
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Text events for bidirectional typing
        self.text_editor.bind("<KeyRelease>", self.on_text_change)

        # Initialize
        self.update_hdl_from_state()
        self.draw_diagram()

    # --- Drawing Logic (Diagram View) ---
    def draw_diagram(self):
        self.canvas.delete("all") # Clear canvas
        
        if not self.has_block:
            return

        bx, by, size = self.block_x, self.block_y, self.block_size
        half = size / 2

        # Draw the block (Square)
        self.canvas.create_rectangle(bx - half, by - half, bx + half, by + half, 
                                     fill="#007acc", outline="#ffffff", width=2, tags="block")
        self.canvas.create_text(bx, by, text="top_module", fill="white", tags="block")

        # Port coordinates (Left, Right, Top, Bottom midpoints)
        self.ports = {
            "in":  (bx - half, by), 
            "out": (bx + half, by),
        }

        # Draw connection dots
        r = 6
        for name, (px, py) in self.ports.items():
            color = "#ffcc00" if name in ["in", "out"] else "#aaaaaa"
            self.canvas.create_oval(px - r, py - r, px + r, py + r, 
                                    fill=color, outline="white", tags=f"port_{name}")

        # Draw completed wire if connected
        if self.is_connected:
            ix, iy = self.ports["in"]
            ox, oy = self.ports["out"]
            # Draw a curved or straight line representing the wire
            self.canvas.create_line(ix, iy, ox, oy, fill="#ffcc00", width=3, dash=(4, 2), tags="wire")

    # --- Canvas Interaction Logic ---
    def on_press(self, event):
        item = self.canvas.find_withtag("current")
        if not item: return
        tags = self.canvas.gettags(item[0])

        if "block" in tags:
            self.drag_data["item"] = "block"
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
        elif "port_in" in tags or "port_out" in tags:
            self.wiring = True
            self.drag_data["start_port"] = "in" if "port_in" in tags else "out"
            self.drag_data["start_x"] = event.x
            self.drag_data["start_y"] = event.y

    def on_drag(self, event):
        if self.drag_data.get("item") == "block":
            # Move the block state
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.block_x += dx
            self.block_y += dy
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.draw_diagram() # Redraw to move wires and dots together

        elif self.wiring:
            # Draw a temporary wire while dragging
            self.canvas.delete("temp_wire")
            self.temp_wire = self.canvas.create_line(
                self.drag_data["start_x"], self.drag_data["start_y"], 
                event.x, event.y, fill="#ffcc00", width=2, tags="temp_wire"
            )

    def on_release(self, event):
        self.drag_data["item"] = None
        
        if self.wiring:
            self.canvas.delete("temp_wire")
            self.wiring = False
            
            # Find items at the release location
            # We look for any item overlapping a small 2x2 square around the mouse
            items = self.canvas.find_overlapping(event.x-1, event.y-1, event.x+1, event.y+1)
            
            target_port = None
            for item in items:
                tags = self.canvas.gettags(item)
                if "port_out" in tags:
                    target_port = "out"
                    break
                elif "port_in" in tags:
                    target_port = "in"
                    break
            
            # Connection logic
            if target_port and target_port != self.drag_data["start_port"]:
                self.is_connected = True
                self.draw_diagram()
                self.update_hdl_from_state()
        

    # --- Synchronization Logic ---
    def update_hdl_from_state(self):
        """Generates HDL text based on visual state."""
        if not self.has_block:
            code = ""
        else:
            code = "module top_module( input in, output out );\n"
            if self.is_connected:
                code += "\n    assign out = in;\n"
                code += "    // Note that wires are directional, \n"
                code += "    // so 'assign in = out' is not equivalent.\n\n"
            else:
                code += "\n\n"
            code += "endmodule"

        # Update text box without triggering the key-release event
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert(tk.END, code)

    def on_text_change(self, event):
        """Parses HDL text to update visual state."""
        text = self.text_editor.get("1.0", tk.END)

        # Basic regex parsing to see if module and assign exist
        has_module = bool(re.search(r"module\s+top_module", text))
        has_assign = bool(re.search(r"assign\s+out\s*=\s*in\s*;", text))

        state_changed = False

        if has_module != self.has_block:
            self.has_block = has_module
            state_changed = True
        
        if has_assign != self.is_connected:
            self.is_connected = has_assign
            state_changed = True

        # Only redraw if the text actually changed the diagram's meaning
        if state_changed:
            self.draw_diagram()

if __name__ == "__main__":
    app = HDLEditorApp()
    app.mainloop()
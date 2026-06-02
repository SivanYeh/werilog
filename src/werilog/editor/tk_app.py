import tkinter as tk
import re
import threading
from abc import ABC, abstractmethod
from werilog.agent.autocomplete import VerilogAgent
from werilog.editor.draw_strategy import JumpWireStrategy, SquareWireStrategy, StraightWireStrategy
from werilog.editor.extractverilog import VerilogModule, ModuleInstance, Port, Element, Wire, extract_verilog
from werilog.editor.error_detector import VerilogSyntaxErrorDetector

# --- Config Parsing Helper (Mirroring display.py load_config) ---
def load_config_yaml():
    config = {}
    import os
    config_path = "config.yaml"
    if not os.path.exists(config_path) and os.path.exists("../config.yaml"):
        config_path = "../config.yaml"
    try:
        with open(config_path, "r") as f:
            current_section = None
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Match section header: 'module:'
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

# --- Global Styling Configuration ---
CONFIG = {}
def initialize_config():
    global CONFIG
    CONFIG = load_config_yaml()

initialize_config()

def get_config_val(section, key, default):
    return CONFIG.get(section, {}).get(key, default)

def get_config_px(section, key, default):
    val = get_config_val(section, key, None)
    if not val:
        return default
    m = re.match(r'(\d+)', str(val))
    return int(m.group(1)) if m else default

# --- Composite Pattern for Drawing (Modular Visual Representation) ---
# Abstract Base Class for visual canvas representations (Composite Pattern).
# All drawable components must implement the draw() method to render themselves on a Tkinter canvas.
class CanvasComponent(ABC):
    @abstractmethod
    def draw(self, canvas, module_name):
        pass

# Visual representation of a module port on the canvas.
# Positioned relative to the parent module block.
class CanvasPort(CanvasComponent):
    def __init__(self, name, direction, rel_x, rel_y, parent=None):
        self.name = name
        if direction not in ["input", "output"]:
            raise ValueError(f"Port direction must be 'input' or 'output', got '{direction}'")
        self.direction = direction
        self.rel_x = rel_x  # relative to parent module center
        self.rel_y = rel_y
        self.abs_x = 0
        self.abs_y = 0
        self.parent = parent

    def get_relative_name(self, root_module):
        if self.parent and self.parent != root_module:
            return f"{self.parent.name}.{self.name}"
        return self.name

    def update_position(self, parent_x, parent_y):
        self.abs_x = parent_x + self.rel_x
        self.abs_y = parent_y + self.rel_y

    def draw(self, canvas, module_name):
        r = 6
        if self.direction == "input":
            color = "#ffcc00"
        elif self.direction == "output":
            color = "#4ec9b0"
        else:
            raise ValueError(f"Unknown port direction: {self.direction}")
        canvas.create_oval(self.abs_x - r, self.abs_y - r, self.abs_x + r, self.abs_y + r, 
                           fill=color, outline="white", tags=(f"port_{module_name}_{self.name}", f"port_{self.name}"))

# Visual representation of a logical element/gate (e.g., AND, NOT).
class CanvasElement(CanvasComponent):
    def __init__(self, op_type, rel_x, rel_y, inputs, output):
        self.op_type = op_type
        self.rel_x = rel_x
        self.rel_y = rel_y
        self.inputs = inputs
        self.output = output
        self.abs_x = 0
        self.abs_y = 0

    def update_position(self, parent_x, parent_y):
        self.abs_x = parent_x + self.rel_x
        self.abs_y = parent_y + self.rel_y

    def draw(self, canvas, module_name):
        w = get_config_px("element", "width", 60)
        h = get_config_px("element", "height", 30)
        bg = get_config_val("element", "background_color", "#3e3e42")
        border = get_config_val("element", "border_color", "#4ec9b0")
        text_color = get_config_val("element", "text_color", "#4ec9b0")
        
        if self.op_type in ["~", "not"]:
            import xml.etree.ElementTree as ET
            import os
            svg_paths = ["dataset/basic-element/NOT-gate.svg", "../dataset/basic-element/NOT-gate.svg", "../../dataset/basic-element/NOT-gate.svg", os.path.join(os.path.dirname(__file__), "../../../dataset/basic-element/NOT-gate.svg")]
            svg_path = None
            for p in svg_paths:
                if os.path.exists(p):
                    svg_path = p
                    break
            if svg_path:
                # Basic representation of the NOT gate matching the SVG design
                canvas.create_polygon(self.abs_x - 12, self.abs_y - 12, 
                                      self.abs_x - 12, self.abs_y + 12, 
                                      self.abs_x + 8, self.abs_y, 
                                      fill=bg, outline=border, width=2, tags=(f"element_{module_name}", "element"))
                canvas.create_oval(self.abs_x + 8, self.abs_y - 4, 
                                   self.abs_x + 16, self.abs_y + 4, 
                                   fill=bg, outline=border, width=2, tags=(f"element_{module_name}", "element"))
                return
                
        canvas.create_rectangle(self.abs_x - w/2, self.abs_y - h/2,
                                self.abs_x + w/2, self.abs_y + h/2,
                                fill=bg, outline=border, width=2, tags=(f"element_{module_name}", "element"))
        canvas.create_text(self.abs_x, self.abs_y, text=self.op_type, fill=text_color, tags=(f"element_{module_name}", "element"))

class CanvasWire(CanvasComponent):
    def __init__(self, start_pt, end_pt, parent_x=0, parent_y=0, name=None):
        self.name = name
        self.start_rel_x = start_pt[0] - parent_x
        self.start_rel_y = start_pt[1] - parent_y
        self.end_rel_x = end_pt[0] - parent_x
        self.end_rel_y = end_pt[1] - parent_y
        
        self.start_pt = start_pt  # (x, y) absolute
        self.end_pt = end_pt      # (x, y) absolute
        # TODO: there must be a better way to handle JumpWireStrategy and other strategies. This is a quick hack to allow testing different strategies without changing the overall structure.
        self.router = JumpWireStrategy(StraightWireStrategy())
        self.cached_route = None

    def update_position(self, parent_x, parent_y):
        self.start_pt = (parent_x + self.start_rel_x, parent_y + self.start_rel_y)
        self.end_pt = (parent_x + self.end_rel_x, parent_y + self.end_rel_y)

    def draw(self, canvas, module_name):
        if self.cached_route is not None:
            res = self.cached_route
        else:
            res = self.router.route(self.start_pt, self.end_pt)
            
        path = res["path"]
        jumps = res.get("jumps", [])
        
        color = get_config_val("wire", "color", "#c586c0")
        width = float(get_config_val("wire", "width", 2.5))
        
        r = 6  # Arc radius
        
        if not jumps:
            coords = [coord for pt in path for coord in pt]
            canvas.create_line(*coords, fill=color, width=width, tags=(f"wire_{module_name}", "wire"))
        else:
            for i in range(len(path) - 1):
                pt1 = path[i]
                pt2 = path[i+1]
                x1, y1 = pt1
                x2, y2 = pt2
                
                seg_jumps = []
                is_horizontal = abs(y1 - y2) < 0.1
                is_vertical = abs(x1 - x2) < 0.1
                
                for jx, jy in jumps:
                    if is_horizontal:
                        if abs(jy - y1) < 0.1 and min(x1, x2) < jx < max(x1, x2):
                            seg_jumps.append((jx, jy))
                    elif is_vertical:
                        if abs(jx - x1) < 0.1 and min(y1, y2) < jy < max(y1, y2):
                            seg_jumps.append((jx, jy))
                            
                if not seg_jumps:
                    canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags=(f"wire_{module_name}", "wire"))
                    continue
                    
                if is_horizontal:
                    reverse_sort = (x1 > x2)
                    seg_jumps.sort(key=lambda p: p[0], reverse=reverse_sort)
                else:
                    reverse_sort = (y1 > y2)
                    seg_jumps.sort(key=lambda p: p[1], reverse=reverse_sort)
                    
                curr_x, curr_y = x1, y1
                for jx, jy in seg_jumps:
                    if is_horizontal:
                        dx = 1 if x2 > x1 else -1
                        canvas.create_line(curr_x, curr_y, jx - dx * r, jy, fill=color, width=width, tags=(f"wire_{module_name}", "wire"))
                        canvas.create_arc(jx - r, jy - r, jx + r, jy + r, start=0, extent=180, style=tk.ARC, outline=color, width=width, tags=(f"wire_{module_name}", "wire"))
                        curr_x, curr_y = jx + dx * r, jy
                    elif is_vertical:
                        dy = 1 if y2 > y1 else -1
                        canvas.create_line(curr_x, curr_y, jx, jy - dy * r, fill=color, width=width, tags=(f"wire_{module_name}", "wire"))
                        canvas.create_arc(jx - r, jy - r, jx + r, jy + r, start=-90, extent=180, style=tk.ARC, outline=color, width=width, tags=(f"wire_{module_name}", "wire"))
                        curr_x, curr_y = jx, jy + dy * r
                        
                canvas.create_line(curr_x, curr_y, x2, y2, fill=color, width=width, tags=(f"wire_{module_name}", "wire"))
        
        if self.name:
            if not jumps:
                mid_x = (self.start_pt[0] + self.end_pt[0]) / 2
                mid_y = (self.start_pt[1] + self.end_pt[1]) / 2
            else:
                mid_idx = len(path) // 2
                mid_x = path[mid_idx][0]
                mid_y = path[mid_idx][1]
            canvas.create_text(mid_x, mid_y - 10, text=self.name, fill="#aaaaaa", font=("Segoe UI", 8), tags=(f"wire_{module_name}", "wire", "wire_name"))


# Visual representation of an intermediate logical net/node junction on the canvas.
class CanvasNet(CanvasComponent):
    def __init__(self, name, rel_x, rel_y):
        self.name = name
        self.rel_x = rel_x
        self.rel_y = rel_y
        self.abs_x = 0
        self.abs_y = 0

    def update_position(self, parent_x, parent_y):
        self.abs_x = parent_x + self.rel_x
        self.abs_y = parent_y + self.rel_y

    def draw(self, canvas, module_name):
        r = 3
        color = "#aaaaaa"
        canvas.create_oval(self.abs_x - r, self.abs_y - r, self.abs_x + r, self.abs_y + r, 
                           fill=color, outline=color, tags=(f"net_{module_name}_{self.name}", "net"))
        canvas.create_text(self.abs_x, self.abs_y - 10, text=self.name, fill=color, font=("Segoe UI", 8), tags=(f"net_{module_name}_{self.name}", "net"))

# Composite class representing a module block.
# Composes children (ports, elements, nets, submodules, and wires) and handles layout calculations.
class CanvasModule(CanvasComponent):
    def __init__(self, name, x, y, width, height, bg_color="#2d2d30", border_color="#555", parent=None):
        self.name = name
        self.display_name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.border_color = border_color
        
        self.rel_x = 0
        self.rel_y = 0
        self.components = []
        self.ports = {}
        self.logical_mod = None
        self.parent = parent

    def add_port(self, port: CanvasPort):
        port.parent = self
        self.components.append(port)
        self.ports[port.name] = port

    def update_position(self, parent_x, parent_y):
        self.x = parent_x + self.rel_x
        self.y = parent_y + self.rel_y
        self.update_positions()


    def update_positions(self):
        for c in self.components:
            if hasattr(c, "update_position"):
                c.update_position(self.x, self.y)

    def update_layout(self, logical_mod):
        self.logical_mod = logical_mod
        self.name = logical_mod.name
        if hasattr(logical_mod, "module_type"):
            self.display_name = f"{logical_mod.name}({logical_mod.module_type})"
        else:
            self.display_name = logical_mod.name
        self.components = []
        self.ports = {}
        
        # 1. Separate ports
        logical_ports = logical_mod.get_ports()
        inputs = [p for p in logical_ports if p.direction == "input"]
        outputs = [p for p in logical_ports if p.direction == "output"]
        
        # 2. Extract internal components
        logical_elements = logical_mod.get_elements()
        non_assign_elements = [el for el in logical_elements if el.op_type != "assign"]
        submodules = logical_mod.get_instances()
        
        total_internals = len(non_assign_elements) + len(submodules)
        
        elements_map = {}
        submodules_map = {}
        
        # 3. Dynamic Size Calculation
        is_submodule = self.parent is not None
        min_h = get_config_px("submodule" if is_submodule else "module", "min_height", 70 if is_submodule else 150)
        max_ports = max(len(inputs), len(outputs))
        ports_h = max_ports * 45 + 50
        
        internals_h = sum(100 if type(item).__name__ == "ModuleInstance" else 50 for item in (non_assign_elements + submodules)) + 60
        internals_w = sum(140 if type(item).__name__ == "ModuleInstance" else 60 for item in (non_assign_elements + submodules)) + 100
        
        req_height = max(min_h, ports_h) if is_submodule else max(min_h, ports_h, internals_h)
        req_width = self.width if is_submodule else max(self.width, internals_w)
        
        if hasattr(self, "custom_height") and self.custom_height > req_height:
            self.height = self.custom_height
        else:
            self.height = req_height
            
        if hasattr(self, "custom_width") and self.custom_width > req_width:
            self.width = self.custom_width
        else:
            self.width = req_width

        # 4. Position input ports vertically on left edge
        num_inputs = len(inputs)
        for i, p in enumerate(inputs):
            rel_x = -self.width / 2
            if num_inputs == 1:
                rel_y = 0
            else:
                rel_y = -self.height / 3 + i * (2 * self.height / 3) / (num_inputs - 1)
            port = CanvasPort(p.name, p.direction, rel_x, rel_y)
            self.add_port(port)
            
        # 5. Position output ports vertically on right edge
        num_outputs = len(outputs)
        for j, p in enumerate(outputs):
            rel_x = self.width / 2
            if num_outputs == 1:
                rel_y = 0
            else:
                rel_y = -self.height / 3 + j * (2 * self.height / 3) / (num_outputs - 1)
            port = CanvasPort(p.name, p.direction, rel_x, rel_y)
            self.add_port(port)

        # Distribute internal components horizontally in the center
        for idx, item in enumerate(non_assign_elements + submodules):
            if total_internals == 1:
                rel_x = 0
            else:
                rel_x = -self.width / 3 + idx * (2 * self.width / 3) / (total_internals - 1)
            rel_y = 0
                
            if isinstance(item, Element):
                canvas_el = CanvasElement(item.op_type, rel_x, rel_y, item.inputs, item.output)
                self.components.append(canvas_el)
                elements_map[item.output] = canvas_el
            else:
                # Nested module: load styling configurations from config.yaml
                sub_width = get_config_px("submodule", "width", 120)
                sub_height = get_config_px("submodule", "height", 70)
                sub_bg = get_config_val("submodule", "background_color", "#3a3a3d")
                sub_border = get_config_val("submodule", "border_color", "#666")
                
                sub_view = CanvasModule(item.name, 0, 0, sub_width, sub_height, sub_bg, sub_border, parent=self)
                
                # Check for custom layout state
                state_key = f"{self.name}.{item.name}"
                if hasattr(self, "app_state") and state_key in self.app_state:
                    state = self.app_state[state_key]
                    sub_view.rel_x = state.get('rel_x', rel_x)
                    sub_view.rel_y = state.get('rel_y', rel_y)
                    sub_view.custom_width = state.get('width', sub_width)
                    sub_view.custom_height = state.get('height', sub_height)
                else:
                    sub_view.rel_x = rel_x
                    sub_view.rel_y = rel_y
                    
                sub_view.app_state = getattr(self, "app_state", {})
                sub_view.update_layout(item)
                self.components.append(sub_view)
                submodules_map[item.name] = sub_view
                
        # Calculate absolute positions
        self.update_positions()
        
        

        # Find intermediate nets (Option A: explicit, Option B: direct)
        net_style = get_config_val("wire", "net_style", "direct")
        
        intermediate_nets = set()
        if net_style == "explicit":
            all_wire_ends = set()
            for w in logical_mod.get_wires():
                all_wire_ends.add(w.source)
                all_wire_ends.add(w.target)
                
            known = set()
            for p in self.ports: known.add(p)
            for el in logical_elements: known.add(el.output)
            for inst in logical_mod.get_instances():
                if inst.name in submodules_map:
                    for p_name in submodules_map[inst.name].ports:
                        known.add(f"{inst.name}.{p_name}")
                        
            declared_wires = set(getattr(logical_mod, "declared_wires", []))
            intermediate_nets = (all_wire_ends - known) & declared_wires

        net_views = {}
        num_nets = len(intermediate_nets)
        for idx, net_name in enumerate(sorted(list(intermediate_nets))):
            rel_x = self.width / 4
            if num_nets == 1:
                rel_y = 0
            else:
                rel_y = -self.height / 3 + idx * (2 * self.height / 3) / (num_nets - 1)
                
            c_net = CanvasNet(net_name, rel_x, rel_y)
            self.components.append(c_net)
            net_views[net_name] = c_net

        # Calculate absolute positions again for nets
        self.update_positions()
        # Coordinate resolver helper for drawing wires
        def resolve_source_coord(source_name):
            if not source_name: return None
            # If it's a module input port
            if source_name in self.ports and self.ports[source_name].direction == "input":
                port = self.ports[source_name]
                return (port.abs_x, port.abs_y)
                
            # If it's the output of a logic element
            if source_name in elements_map:
                el = elements_map[source_name]
                return (el.abs_x + 30, el.abs_y)
            for out_name, el in elements_map.items():
                if source_name == f"{el.op_type}_{out_name}":
                    return (el.abs_x + 30, el.abs_y)
                
            # If driven by a simple assign element
            for el in logical_elements:
                if el.op_type == "assign" and el.output == source_name:
                    return resolve_source_coord(el.inputs[0])
                    
            # If it's connected to an instance output port
            for instance in logical_mod.get_instances():
                for port_name, signal in instance.connections.items():
                    if signal == source_name:
                        sub_view = submodules_map.get(instance.name)
                        if sub_view and port_name in sub_view.ports and sub_view.ports[port_name].direction == "output":
                            port = sub_view.ports[port_name]
                            return (port.abs_x, port.abs_y)
                            
            # If it's an output port of a nested submodule via UI hierarchical reference
            if "." in source_name:
                parts = source_name.split(".", 1)
                if len(parts) == 2:
                    sub_name, port_name = parts
                    if sub_name in submodules_map:
                        sub_view = submodules_map[sub_name]
                        if port_name in sub_view.ports and sub_view.ports[port_name].direction == "output":
                            port = sub_view.ports[port_name]
                            return (port.abs_x, port.abs_y)
            else:
                # Fallback backward compatibility
                for sub_name, sub_view in submodules_map.items():
                    if source_name in sub_view.ports and sub_view.ports[source_name].direction == "output":
                        port = sub_view.ports[source_name]
                        return (port.abs_x, port.abs_y)
            
            # Explicit net view
            if source_name in net_views:
                return (net_views[source_name].abs_x, net_views[source_name].abs_y)

            # Option B: Direct routing (or fallback for implicit nets in explicit mode)
            if net_style == "direct" or source_name not in net_views:
                for w in logical_mod.get_wires():
                    if w.target == source_name:
                        res = resolve_source_coord(w.source)
                        if res: return res
                        
            # Fallback to any port if exists
            if source_name in self.ports:
                port = self.ports[source_name]
                return (port.abs_x, port.abs_y)
                
            return None


        # 5. Route wires to elements
        for el in non_assign_elements:
            canvas_el = elements_map[el.output]
            for in_sig in el.inputs:
                start_pt = resolve_source_coord(in_sig)
                if start_pt:
                    end_pt = (canvas_el.abs_x - 30, canvas_el.abs_y)
                    is_declared = in_sig in getattr(self.logical_mod, "declared_wires", [])
                    label_name = in_sig if is_declared else None
                    self.components.append(CanvasWire(start_pt, end_pt, self.x, self.y, name=label_name))
                    
        # 6. Route wires to submodule inputs
        for sub_name, sub_view in submodules_map.items():
            logical_instance = next((c for c in logical_mod.get_instances() if c.name == sub_name), None)
            
            for port_name, port_obj in sub_view.ports.items():
                if port_obj.direction == "input":
                    start_pt = None
                    
                    # 1. From instantiation connections
                    if logical_instance and port_name in logical_instance.connections:
                        signal = logical_instance.connections[port_name]
                        start_pt = resolve_source_coord(signal)
                        
                    # 2. From backward-compatible / UI-generated assign statements
                    if not start_pt:
                        for el in logical_elements:
                            # Match parent assignment targeting the submodule port specifically
                            if el.op_type == "assign" and el.output == f"{sub_name}.{port_name}":
                                start_pt = resolve_source_coord(el.inputs[0])
                                break
                                
                    if start_pt:
                        end_pt = (port_obj.abs_x, port_obj.abs_y)
                        signal_name = signal if 'signal' in locals() else None
                        is_declared = signal_name in getattr(self.logical_mod, "declared_wires", [])
                        label_name = signal_name if is_declared else None
                        self.components.append(CanvasWire(start_pt, end_pt, self.x, self.y, name=label_name))
                        
        # 7. Route wires from elements/submodules/inputs to module outputs and intermediate nets
        logical_wires = logical_mod.get_wires()
        for w in logical_wires:
            start_pt = resolve_source_coord(w.source)
            end_pt = None
            
            if w.target in self.ports and self.ports[w.target].direction == "output":
                port = self.ports[w.target]
                end_pt = (port.abs_x, port.abs_y)
            elif w.target in net_views:
                c_net = net_views[w.target]
                end_pt = (c_net.abs_x, c_net.abs_y)
                
            if start_pt and end_pt:
                is_declared = w.source in getattr(self.logical_mod, "declared_wires", [])
                label_name = w.source if is_declared else None
                self.components.append(CanvasWire(start_pt, end_pt, self.x, self.y, name=label_name))

    def draw(self, canvas, module_name=None):
        half_w = self.width / 2
        half_h = self.height / 2
        
        # Draw block rectangle (using configured styling)
        canvas.create_rectangle(self.x - half_w, self.y - half_h, 
                               self.x + half_w, self.y + half_h, 
                               fill=self.bg_color, outline=self.border_color, width=2, tags=("block", f"mod_{self.name}"))
        
        # Draw module name label at the top inside the block
        canvas.create_text(self.x, self.y - half_h + 15, text=self.display_name, fill="white", tags=("block", f"mod_{self.name}"))
        
        # Draw resize handle for both root and submodules
        rx = self.x + half_w
        ry = self.y + half_h
        canvas.create_polygon(rx - 12, ry, rx, ry, rx, ry - 12, fill="#777", outline="#777", tags=("block", f"mod_{self.name}", "resize_handle"))
        
        # Update and draw children (ports, elements, submodules & wires)
        self.update_positions()
        
        # Pre-compute routes for all wires in this module to find intersections
        existing_paths = []
        for c in self.components:
            if isinstance(c, CanvasWire):
                res = c.router.route(c.start_pt, c.end_pt, existing_paths)
                c.cached_route = res
                existing_paths.append(res["path"])
                
        for c in self.components:
            if isinstance(c, CanvasPort):
                c.draw(canvas, self.name)
            elif isinstance(c, CanvasNet):
                c.draw(canvas, self.name)
            elif isinstance(c, CanvasWire):
                c.draw(canvas, self.name)
            elif isinstance(c, CanvasElement):
                c.draw(canvas, self.name)
            elif isinstance(c, CanvasModule):
                # Recursively draw inner module
                c.draw(canvas, self.name)

# Main GUI Editor application orchestrating bidirectional text/diagram synchronization.
class HDLEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bidirectional HDL & Diagram Editor")
        self.geometry("1000x600")

        # --- Load Configuration (Config sync with display.py) ---
        self.bg_color = get_config_val("module", "background_color", "#2d2d30")
        self.border_color = get_config_val("module", "border_color", "#555")
        
        self.block_width = get_config_px("module", "width", 250)
        self.block_height = get_config_px("module", "min_height", 150)

        # --- Application State (The "Source of Truth") ---
        # active_modules: List[VerilogModule] logical AST structures loaded from the text editor
        self.active_modules = []
        # error_detector: utility to check for syntax errors dynamically as the user types
        self.error_detector = VerilogSyntaxErrorDetector()
        # app_state: dictionary holding coordinates/dimensions for module blocks to preserve them across re-renders
        self.app_state = {}
        
        # module_views: List[CanvasModule] representing the visual blocks drawn on the canvas
        self.module_views = []
        
        # Load init.v default code
        try:
            import os
            init_v_paths = [os.path.join(os.path.dirname(__file__), "init.v"), "src/werilog/editor/init.v", "init.v"]
            init_v_path = None
            for p in init_v_paths:
                if os.path.exists(p):
                    init_v_path = p
                    break
            if not init_v_path:
                raise FileNotFoundError("Could not find init.v")
            with open(init_v_path, "r") as f:
                code = f.read()
            self.active_modules = extract_verilog(code)
            for i, mod in enumerate(self.active_modules):
                mv = CanvasModule(mod.name, 250, 150 + i * 400, self.block_width, self.block_height, 
                                  self.bg_color, self.border_color)
                mv.app_state = self.app_state
                mv.update_layout(mod)
                self.module_views.append(mv)
        except Exception as e:
            print(f"Error loading init.v: {e}")
            default_mod = VerilogModule("top_module")
            default_mod.add(Port("in", "input"))
            default_mod.add(Port("out", "output"))
            self.active_modules.append(default_mod)
            mv = CanvasModule("top_module", 225, 150, self.block_width, self.block_height, 
                              self.bg_color, self.border_color)
            mv.app_state = self.app_state
            mv.update_layout(default_mod)
            self.module_views.append(mv)
        
        # Interaction state
        self.drag_data = {"x": 0, "y": 0, "item": None, "module_view": None}
        self.wiring = False
        self.temp_wire = None

        # --- UI Layout ---
        self.toolbar_frame = tk.Frame(self, bg="#252526")
        self.toolbar_frame.pack(fill=tk.X, side=tk.TOP)
        
        self.export_btn = tk.Button(self.toolbar_frame, text="Export SVG", command=self.export_svg)
        self.export_btn.pack(side=tk.RIGHT, padx=5, pady=2)
        
        # Error Panel Frame at the bottom
        self.error_frame = tk.Frame(self, bg="#252526")
        self.error_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.error_label = tk.Label(self.error_frame, text="Syntax Log", bg="#252526", fg="#d4d4d4", font=("Segoe UI", 9, "bold"), anchor="w")
        self.error_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.error_panel = tk.Text(self.error_frame, height=4, bg="#1e1e1e", fg="#f44336",
                                   font=("Courier New", 10), insertbackground="white", state=tk.DISABLED)
        self.error_panel.pack(fill=tk.X, padx=5, pady=2)

        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Left Panel: Diagram Canvas with Scrollbar
        self.canvas_frame = tk.Frame(self.paned_window, bg="#1e1e1e")
        self.paned_window.add(self.canvas_frame)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#1e1e1e", width=500)
        
        self.vbar = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.hbar = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.config(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set, scrollregion=(-2000, -2000, 4000, 4000))
        
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right Panel: Text Editor
        self.text_editor = tk.Text(self.paned_window, width=50, bg="#2d2d2d", fg="#d4d4d4", 
                                   font=("Courier New", 12), insertbackground="white")
        self.paned_window.add(self.text_editor)

        # Setup Agent for Suggestions
        self.agent = VerilogAgent()
        self.suggestion_active = False
        self.debounce_timer = None
        self.text_editor.tag_config("suggestion", foreground="#6a9955")

        # --- Event Bindings ---
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_hover)
        self.text_editor.bind("<KeyRelease>", self.on_text_change)
        self.text_editor.bind("<Tab>", self.on_tab)
        self.text_editor.bind("<Escape>", self.on_escape)
        self.text_editor.bind("<Button-1>", self.on_click_editor)

        self.last_hovered_handle = None
        # Initialize
        self.update_hdl_from_state()
        self.on_text_change(None)
        self.draw_diagram()

    # --- Drawing Logic (Diagram View) ---
    def draw_diagram(self):
        self.canvas.delete("all")
        self.last_hovered_handle = None
        
        # Draw all active module views
        for mv in self.module_views:
            mv.draw(self.canvas)

        # Configure scrollregion based on content bounds
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    # --- Canvas Interaction Logic ---
    def save_layout_state(self, mv):
        if mv.parent:
            state_key = f"{mv.parent.name}.{mv.name}"
            self.app_state[state_key] = {
                'rel_x': mv.rel_x,
                'rel_y': mv.rel_y,
                'width': mv.width,
                'height': mv.height
            }

    def re_layout(self):
        for root_mv in self.module_views:
            root_mv.update_positions()
        self.draw_diagram()

    def on_hover(self, event):
        if self.drag_data.get("item"): return
        
        item = self.canvas.find_withtag("current")
        if item:
            tags = self.canvas.gettags(item[0])
            if "resize_handle" in tags:
                self.canvas.config(cursor="bottom_right_corner")
                if self.last_hovered_handle != item[0]:
                    if self.last_hovered_handle:
                        self.canvas.itemconfig(self.last_hovered_handle, fill="#777", outline="#777")
                    self.canvas.itemconfig(item[0], fill="#ffcc00", outline="#ffcc00")
                    self.last_hovered_handle = item[0]
                return
                
        self.canvas.config(cursor="")
        if self.last_hovered_handle:
            self.canvas.itemconfig(self.last_hovered_handle, fill="#777", outline="#777")
            self.last_hovered_handle = None

    def on_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        item = self.canvas.find_withtag("current")
        if not item: return
        tags = self.canvas.gettags(item[0])

        target_mod = None
        for mv in self.module_views:
            # Check submodule tags first
            for c in mv.components:
                if isinstance(c, CanvasModule):
                    if f"mod_{c.name}" in tags or any(f"port_{c.name}_{p_name}" in tags for p_name in c.ports):
                        target_mod = c
                        break
            if target_mod: break
            # Check root module tags
            if f"mod_{mv.name}" in tags or any(f"port_{mv.name}_{p_name}" in tags for p_name in mv.ports) or any(t == f"element_{mv.name}" or t == f"wire_{mv.name}" for t in tags):
                target_mod = mv
                break
                
        if not target_mod:
            return

        if "block" in tags:
            edge_tol = 15
            is_right_edge = abs(cx - (target_mod.x + target_mod.width/2)) < edge_tol
            is_bottom_edge = abs(cy - (target_mod.y + target_mod.height/2)) < edge_tol
            
            if is_right_edge or is_bottom_edge:
                self.drag_data["item"] = "resize_block"
            else:
                self.drag_data["item"] = "block"
                
            self.drag_data["module_view"] = target_mod
            self.drag_data["x"] = cx
            self.drag_data["y"] = cy
        else:
            # Check if port is clicked
            root_mod = target_mod.parent if target_mod.parent else target_mod
            for port_name in target_mod.ports:
                if f"port_{target_mod.name}_{port_name}" in tags:
                    self.wiring = True
                    self.drag_data["module_view"] = root_mod
                    if target_mod.parent:
                        self.drag_data["start_port"] = f"{target_mod.name}.{port_name}"
                    else:
                        self.drag_data["start_port"] = port_name
                    port_obj = target_mod.ports[port_name]
                    self.drag_data["start_x"] = port_obj.abs_x
                    self.drag_data["start_y"] = port_obj.abs_y
                    break

    def on_drag(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        mv = self.drag_data.get("module_view")
        
        if self.drag_data.get("item") == "resize_block" and mv:
            dx = cx - self.drag_data["x"]
            dy = cy - self.drag_data["y"]
            mv.width += dx
            mv.height += dy
            if mv.width < 50: mv.width = 50
            if mv.height < 50: mv.height = 50
            mv.custom_width = mv.width
            mv.custom_height = mv.height
            self.save_layout_state(mv)
            
            parent_mod = mv.parent
            if parent_mod:
                parent_mod.update_layout(parent_mod.logical_mod)
                for c in parent_mod.components:
                    if isinstance(c, CanvasModule) and c.name == mv.name:
                        self.drag_data["module_view"] = c
                        break
            else:
                mv.update_layout(mv.logical_mod)
                        
            self.drag_data["x"] = cx
            self.drag_data["y"] = cy
            self.re_layout()
            
        elif self.drag_data.get("item") == "block" and mv:
            dx = cx - self.drag_data["x"]
            dy = cy - self.drag_data["y"]
            if mv.parent:
                mv.rel_x += dx
                mv.rel_y += dy
                self.save_layout_state(mv)
                parent_mod = mv.parent
                parent_mod.update_layout(parent_mod.logical_mod)
                for c in parent_mod.components:
                    if isinstance(c, CanvasModule) and c.name == mv.name:
                        self.drag_data["module_view"] = c
                        break
            else:
                mv.x += dx
                mv.y += dy
            self.drag_data["x"] = cx
            self.drag_data["y"] = cy
            self.re_layout()
            
        elif self.wiring:
            self.canvas.delete("temp_wire")
            # Route the temporary wire directly using StraightWireStrategy
            router = StraightWireStrategy()
            path = router.route((self.drag_data["start_x"], self.drag_data["start_y"]), (cx, cy))
            coords = [coord for pt in path for coord in pt]
            self.temp_wire = self.canvas.create_line(
                *coords, fill="#ffcc00", width=2, tags="temp_wire"
            )

    def on_release(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        mv = self.drag_data.get("module_view")
        self.drag_data["item"] = None
        self.drag_data["module_view"] = None
        
        if self.wiring and mv:
            self.canvas.delete("temp_wire")
            self.wiring = False
            
            items = self.canvas.find_overlapping(cx-1, cy-1, cx+1, cy+1)
            
            target_port = None
            for item in items:
                tags = self.canvas.gettags(item)
                # Check root ports
                for port_name in mv.ports:
                    if f"port_{mv.name}_{port_name}" in tags:
                        target_port = port_name
                        break
                if target_port: break
                
                # Check submodule ports
                for c in mv.components:
                    if isinstance(c, CanvasModule):
                        for port_name in c.ports:
                            if f"port_{c.name}_{port_name}" in tags:
                                target_port = f"{c.name}.{port_name}"
                                break
                    if target_port: break
                if target_port: break
            
            # Connection logic (only wire if both exist in same module)
            if target_port and target_port != self.drag_data["start_port"]:
                logical_mod = mv.logical_mod
                if logical_mod:
                    # Clear existing assign elements and wires matching target_port to overwrite connection
                    logical_mod.components = [
                        c for c in logical_mod.components
                        if not (isinstance(c, Element) and c.op_type == "assign" and c.output == target_port)
                        and not (isinstance(c, Wire) and c.target == target_port)
                    ]
                    # Add assignment
                    start_port = self.drag_data["start_port"]
                    start_is_inst = "." in start_port
                    target_is_inst = "." in target_port
                    
                    if start_is_inst or target_is_inst:
                        if not start_is_inst:
                            wire_name = start_port
                        elif not target_is_inst:
                            wire_name = target_port
                        else:
                            wire_name = f"wire_{start_port.replace('.', '_')}"
                            
                        if start_is_inst:
                            i_name, p_name = start_port.split(".", 1)
                            for inst in logical_mod.get_instances():
                                if inst.name == i_name:
                                    inst.connections[p_name] = wire_name
                        if target_is_inst:
                            i_name, p_name = target_port.split(".", 1)
                            for inst in logical_mod.get_instances():
                                if inst.name == i_name:
                                    inst.connections[p_name] = wire_name
                    else:
                        logical_mod.add(Element("assign", [start_port], target_port))
                        
                    logical_mod.add(Wire(target_port, start_port))
                    
                    # Update layout in the visual module view so the wire stays displayed
                    mv.update_layout(logical_mod)
                    
                    self.update_hdl_from_state()
                    self.draw_diagram()

    def export_svg(self):
        try:
            import canvasvg
            filename = "diagram_export.svg"
            canvasvg.saveall(filename, self.canvas)
            
            self.error_panel.config(state=tk.NORMAL)
            self.error_panel.delete("1.0", tk.END)
            self.error_panel.config(fg="#4ec9b0")
            self.error_panel.insert(tk.END, f"Successfully exported diagram to {filename}")
            self.error_panel.config(state=tk.DISABLED)
        except Exception as e:
            self.error_panel.config(state=tk.NORMAL)
            self.error_panel.delete("1.0", tk.END)
            self.error_panel.config(fg="#f44336")
            self.error_panel.insert(tk.END, f"SVG Export failed: {e}")
            self.error_panel.config(state=tk.DISABLED)

    # --- Suggestion Logic ---
    def schedule_suggestion(self):
        if self.debounce_timer:
            self.after_cancel(self.debounce_timer)
        self.debounce_timer = self.after(500, self.fetch_suggestion_async)

    def fetch_suggestion_async(self):
        cursor_pos = self.text_editor.index(tk.INSERT)
        prefix = self.text_editor.get("1.0", cursor_pos)
        full_text = self.text_editor.get("1.0", tk.END)
        
        # Calculate current syntax errors
        errors = self.error_detector.check_syntax(full_text)
        
        def task():
            suggestion = self.agent.suggest_completion(prefix, errors=errors)
            if suggestion:
                self.after(0, lambda: self.show_suggestion(suggestion, cursor_pos))
                
        threading.Thread(target=task, daemon=True).start()

    def show_suggestion(self, suggestion, cursor_pos):
        if self.suggestion_active or self.text_editor.index(tk.INSERT) != cursor_pos:
            return
        
        self.suggestion_active = True
        self.text_editor.insert(cursor_pos, suggestion, "suggestion")
        self.text_editor.mark_set(tk.INSERT, cursor_pos)

    def on_tab(self, event):
        if self.suggestion_active:
            self.accept_suggestion()
            return "break"
            
    def on_escape(self, event):
        if self.suggestion_active:
            self.reject_suggestion()
            return "break"
            
    def on_click_editor(self, event):
        if self.suggestion_active:
            self.reject_suggestion()

    def accept_suggestion(self):
        self.suggestion_active = False
        ranges = self.text_editor.tag_ranges("suggestion")
        if ranges:
            start = ranges[0]
            end = ranges[1]
            self.text_editor.tag_remove("suggestion", start, end)
            self.text_editor.mark_set(tk.INSERT, end)
            self.on_text_change(None)

    def reject_suggestion(self):
        self.suggestion_active = False
        ranges = self.text_editor.tag_ranges("suggestion")
        if ranges:
            self.text_editor.delete(ranges[0], ranges[1])

    # --- Synchronization Logic ---
    def update_hdl_from_state(self):
        """Generates HDL text based on visual state."""
        if not self.active_modules:
            code = "/* No modules defined */"
        else:
            code_blocks = []
            for mod in self.active_modules:
                code_blocks.append(mod.to_verilog())
            code = "\n\n".join(code_blocks)

        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert(tk.END, code)

    def on_text_change(self, event):
        """Parses HDL text to update visual state."""
        if event and getattr(event, "keysym", None) in ("Tab", "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Up", "Down", "Left", "Right"):
            pass
        elif self.suggestion_active:
            self.reject_suggestion()
            
        if event and getattr(event, "char", ""):
            self.schedule_suggestion()

        text = self.text_editor.get("1.0", tk.END)

        # Run syntax error detector
        errors = self.error_detector.check_syntax(text)
        
        # Update error panel
        self.error_panel.config(state=tk.NORMAL)
        self.error_panel.delete("1.0", tk.END)
        if errors:
            self.error_panel.config(fg="#f44336")  # Red for errors
            error_text = "\n".join(str(e) for e in errors)
            self.error_panel.insert(tk.END, error_text)
        else:
            self.error_panel.config(fg="#4ec9b0")  # Teal/green for success
            self.error_panel.insert(tk.END, "No syntax errors detected.")
        self.error_panel.config(state=tk.DISABLED)

        # Parse modularly using extract_verilog
        try:
            modules = extract_verilog(text)
        except Exception:
            modules = []
            
        self.active_modules = modules
        
        # Collect logical warnings from modules and append to syntax log
        all_warnings = []
        for mod in modules:
            all_warnings.extend(getattr(mod, "warnings", []))
            
        if all_warnings:
            self.error_panel.config(state=tk.NORMAL)
            if not errors:
                self.error_panel.delete("1.0", tk.END)
                self.error_panel.config(fg="#ffcc00") # Yellow/Orange for warnings
            else:
                self.error_panel.insert(tk.END, "\n")
            
            warn_text = "\n".join(all_warnings)
            self.error_panel.insert(tk.END, warn_text)
            self.error_panel.config(state=tk.DISABLED)
        
        # Sync module coordinates and re-layout
        new_module_views = []
        
        # Start placing new modules below the lowest existing module
        if self.module_views:
            current_y = max(mv.y + mv.height / 2 for mv in self.module_views) + 50
        else:
            current_y = 120
        
        for mod in self.active_modules:
            existing_view = next((mv for mv in self.module_views if mv.name == mod.name), None)
            
            if existing_view:
                existing_view.update_layout(mod)
                existing_view.update_positions()
                new_module_views.append(existing_view)
            else:
                mv = CanvasModule(mod.name, 225, 0, self.block_width, self.block_height, 
                                  self.bg_color, self.border_color)
                mv.app_state = self.app_state
                mv.update_layout(mod)
                mv.y = current_y + mv.height / 2
                mv.update_positions()
                new_module_views.append(mv)
                current_y += mv.height + 50
                
        self.module_views = new_module_views
        self.draw_diagram()



if __name__ == "__main__":
    app = HDLEditorApp()
    app.mainloop()
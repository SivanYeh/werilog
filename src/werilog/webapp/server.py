from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os
import tempfile
import shutil

from werilog.editor import extractverilog
from werilog.editor import draw_strategy
from werilog.agent.core import VerilogAgent
from werilog.editor.error_detector import VerilogSyntaxErrorDetector
from werilog.agent.diagram_analyzer import DiagramAnalyzer
from werilog.agent.data_structure_to_verilog import ds_string_to_verilog
import traceback

app = FastAPI(title="Verilog WebGL Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse

class ParseRequest(BaseModel):
    code: str
    positions: dict = {}

class SuggestRequest(BaseModel):
    prefix: str
    errors: list = []

agent = VerilogAgent()
error_detector = VerilogSyntaxErrorDetector()

def clean_sig_name(name):
    if not name:
        return ""
    return name.split('.')[-1]

@app.post("/api/import_png")
async def import_png(file: UploadFile = File(...)):
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        with DiagramAnalyzer() as analyzer:
            ds = analyzer.call_agent(
                image_path=tmp_path,
                max_new_tokens=8192
            )
            
        verilog_code = ds_string_to_verilog(ds)
        
        # clean up
        os.remove(tmp_path)
        
        return {"verilog_code": verilog_code}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/api/parse")
def parse_verilog(req: ParseRequest):
    code = req.code
    
    # 1. Syntax Errors
    errors_objs = error_detector.check_syntax(code)
    errors = [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in errors_objs]
    
    # 2. Extract AST
    modules_list = []
    if "module" in code and "endmodule" in code:
        try:
            extracted = extractverilog.extract_verilog(code)
            if extracted:
                modules_list = [m.to_dict() for m in extracted]
        except Exception as e:
            print(f"Error parsing AST: {e}")
            traceback.print_exc()

    # 3. Compute Layout & Routing
    layout_data = []
    
    for i, module in enumerate(modules_list):
        ports = module.get("ports", [])
        inputs = [p for p in ports if p.get("direction") == "input"]
        outputs = [p for p in ports if p.get("direction") == "output"]
        elements = module.get("elements", [])
        wires = module.get("wires", [])
        
        num_inputs = len(inputs)
        num_outputs = len(outputs)
        max_ports = max(num_inputs, num_outputs)
        
        mod_w = 250
        min_h = 150
        mod_h = max(min_h, max_ports * 45 + 50)
        
        mod_name = module.get("name", "Unknown")
        
        if mod_name in req.positions:
            mod_x = req.positions[mod_name].get("x", 200 + i * 350)
            mod_y = req.positions[mod_name].get("y", 100 + i * 50)
            mod_w = req.positions[mod_name].get("w", mod_w)
            mod_h = req.positions[mod_name].get("h", mod_h)
        else:
            mod_x = 200 + i * 350
            mod_y = 100 + (i % 3) * 50
        

        
        port_coords = {}
        rendered_ports = []
        
        # Input Ports
        for i, port in enumerate(inputs):
            px = mod_x
            py = mod_y + mod_h / 2 if num_inputs == 1 else mod_y + 40 + i * (mod_h - 80) / (num_inputs - 1)
            p_name = clean_sig_name(port["name"])
            port_coords[p_name] = (px, py)
            rendered_ports.append({"name": p_name, "direction": "input", "x": px, "y": py})
            
        # Output Ports
        for j, port in enumerate(outputs):
            px = mod_x + mod_w
            py = mod_y + mod_h / 2 if num_outputs == 1 else mod_y + 40 + j * (mod_h - 80) / (num_outputs - 1)
            p_name = clean_sig_name(port["name"])
            port_coords[p_name] = (px, py)
            rendered_ports.append({"name": p_name, "direction": "output", "x": px, "y": py})
            
        # Elements
        el_coords = {}
        rendered_elements = []
        non_assign_elements = [el for el in elements if el.get("op") != "assign"]
        
        # Instances
        instances = module.get("instances", [])
        rendered_instances = []
        
        num_internals = len(non_assign_elements) + len(instances)
        
        # We divide the horizontal space for elements and instances
        # Elements are small, instances are larger.
        for k, el in enumerate(non_assign_elements):
            ex = mod_x + mod_w / 3
            ey = mod_y + mod_h / 2 if num_internals == 1 else mod_y + 40 + k * (mod_h - 80) / (num_internals - 1)
            el_out = clean_sig_name(el.get("out"))
            el_coords[el_out] = (ex, ey)
            rendered_elements.append({"op": el.get("op"), "out": el_out, "x": ex, "y": ey})

        for j, inst in enumerate(instances):
            inst_name = inst.get("name")
            inst_type = inst.get("module_type")
            idx = len(non_assign_elements) + j
            
            # Position
            ix = mod_x + (mod_w * 2 / 3)
            iy = mod_y + mod_h / 2 if num_internals == 1 else mod_y + 40 + idx * (mod_h - 80) / (num_internals - 1)
            
            # Sizes
            iw = 120
            ih = 70
            
            # Custom position if exists
            inst_key = f"{mod_name}.{inst_name}"
            if inst_key in req.positions:
                ix = mod_x + req.positions[inst_key].get("x", ix - mod_x)
                iy = mod_y + req.positions[inst_key].get("y", iy - mod_y)
                iw = req.positions[inst_key].get("w", iw)
                ih = req.positions[inst_key].get("h", ih)
                
            connections = inst.get("connections", {})
            inst_ports = []
            
            # Since we don't parse the submodule itself right here, we just guess direction based on standard ports 
            connections = inst.get('connections', {})
            
            # Use real port directions mapped by extractverilog's linking pass
            linked_ports = {p.get("name"): p.get("direction") for p in inst.get('ports', [])}
            
            p_idx = 0

            # We should render ALL ports defined in the module blueprint, not just the connected ones.
            # If linked_ports is available, use it. Otherwise, fallback to connections.
            ports_to_render = []
            if linked_ports:
                for p_name in linked_ports.keys():
                    ports_to_render.append((p_name, connections.get(p_name, "")))
            else:
                for p_name, sig_name in connections.items():
                    ports_to_render.append((p_name, sig_name))
            
            p_idx = 0
            for port_name, sig_name in ports_to_render:
                p_name = clean_sig_name(port_name)
                s_name = clean_sig_name(sig_name)
                
                direction = linked_ports.get(p_name, "input")
                
                port_x = ix if direction == "input" else ix + iw
                port_y = iy + 20 + p_idx * 20
                p_idx += 1
                
                inst_ports.append({
                    "name": p_name,
                    "signal": s_name,
                    "direction": direction,
                    "x": port_x,
                    "y": port_y
                })
                
                el_coords[f"{inst_name}.{p_name}"] = (port_x, port_y)
                
            # Do not auto-expand parent module to fit instances
            # Let the user manually control the parent module's size
                
            rendered_instances.append({
                "name": inst_name,
                "type": inst_type,
                "box": {"x": ix, "y": iy, "w": iw, "h": ih},
                "ports": inst_ports
            })

        # Routing
        drawn_paths = []
        routed_wires = []
        
        def resolve_source_coord(wire_source):
            if not wire_source:
                return None
            clean_src = clean_sig_name(wire_source)
            if clean_src in port_coords and any(p["name"] == clean_src and p["direction"] == "input" for p in ports):
                return port_coords[clean_src]
            
            # Check instances
            for inst in rendered_instances:
                for p in inst["ports"]:
                    if p["signal"] == clean_src and p["direction"] == "output":
                        return (p["x"], p["y"])
                        
            for el in elements:
                el_out_name = clean_sig_name(el.get("out"))
                el_op = el.get("op")
                if clean_src == f"{el_op}_{el_out_name}" or clean_src == el_out_name:
                    if el_op == "assign":
                        in_sig = clean_sig_name(el.get("in")[0])
                        return resolve_source_coord(in_sig)
                    else:
                        return el_coords.get(el_out_name)
                        
            # Check instances input signals as well if they act as passthrough?
            for inst in rendered_instances:
                for p in inst["ports"]:
                    if p["signal"] == clean_src:
                        return (p["x"], p["y"])
                        
            return port_coords.get(clean_src, None)

        router = draw_strategy.JumpWireStrategy(draw_strategy.SquareWireStrategy())
        
        # Route elements in
        for el in non_assign_elements:
            el_out = clean_sig_name(el.get("out"))
            ex, ey = el_coords[el_out]
            for in_sig in el.get("in", []):
                start_pt = resolve_source_coord(in_sig)
                if start_pt:
                    res = router.route(start_pt, (ex - 30, ey), drawn_paths)
                    drawn_paths.append(res["path"])
                    routed_wires.append(res)
                    
        # Route instances in
        for inst in rendered_instances:
            for p in inst["ports"]:
                if p["direction"] == "input":
                    start_pt = resolve_source_coord(p["signal"])
                    if start_pt:
                        # Only route if it's not routing to itself (which happens if it can't find source)
                        if start_pt != (p["x"], p["y"]):
                            res = router.route(start_pt, (p["x"], p["y"]), drawn_paths)
                            drawn_paths.append(res["path"])
                            routed_wires.append(res)
                    
        # Route explicitly declared wires
        for wire in wires:
            target = clean_sig_name(wire.get("target"))
            source = clean_sig_name(wire.get("source"))
            end_pt = port_coords.get(target)
            
            if end_pt:
                start_pt = resolve_source_coord(source)
                if start_pt and start_pt != end_pt:
                    res = router.route(start_pt, end_pt, drawn_paths)
                    drawn_paths.append(res["path"])
                    routed_wires.append(res)
                    
        # Route parent outputs out
        for out_port in outputs:
            end_pt = port_coords.get(clean_sig_name(out_port["name"]))
            start_pt = resolve_source_coord(out_port["name"])
            if start_pt and end_pt and start_pt != end_pt:
                res = router.route(start_pt, end_pt, drawn_paths)
                drawn_paths.append(res["path"])
                routed_wires.append(res)
                
        layout_data.append({
            "name": module.get("name", "Unknown"),
            "box": {"x": mod_x, "y": mod_y, "w": mod_w, "h": mod_h},
            "ports": rendered_ports,
            "elements": rendered_elements,
            "instances": rendered_instances,
            "routed_wires": routed_wires
        })
        
    return {
        "errors": errors,
        "layout": layout_data
    }

@app.post("/api/suggest")
def suggest_code(req: SuggestRequest):
    try:
        formatted_errors = []
        for e in req.errors:
            if isinstance(e, dict):
                formatted_errors.append(f"Line {e.get('line_number', '?')}: [{e.get('severity', 'ERROR').upper()}] {e.get('message', 'Unknown error')}")
            else:
                formatted_errors.append(str(e))
                
        suggestion = agent.suggest_completion(req.prefix, errors=formatted_errors)
        return {"suggestion": suggestion}
    except Exception as e:
        return {"suggestion": None, "error": str(e)}

@app.get("/")
def read_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


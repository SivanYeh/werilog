import re
import json
import copy
from abc import ABC, abstractmethod

# --- Component Pattern (Composition) ---
# This implements the Composite design pattern.
# 'Component' is the abstract base class for all logical netlist entities
# (e.g., ports, wires, gates, submodule instances, and modules themselves).
class Component(ABC):
    @abstractmethod
    def to_dict(self):
        pass

    @abstractmethod
    def to_verilog(self):
        pass

# Represents a physical port of a Verilog module (input, output, or bidirectional).
class Port(Component):
    def __init__(self, name, direction, vector=None, parent=None):
        self.name = name
        self.direction = direction
        self.vector = vector
        self.parent = parent

    def to_dict(self):
        return {
            "type": "port",
            "name": self.name,
            "direction": self.direction,
            "vector": self.vector
        }

    def to_verilog(self):
        vector_str = f" [{self.vector}]" if self.vector else ""
        return f"{self.direction}{vector_str} {self.name}"

# Represents a logical wire/connection in the module's netlist.
# It links a 'source' signal to a 'target' destination.
class Wire(Component):
    def __init__(self, target, source, parent=None):
        self.target = target
        self.source = source
        self.parent = parent
        
    def to_dict(self):
        return {
            "type": "wire",
            "target": self.target,
            "source": self.source
        }

    def to_verilog(self):
        return ""

# Represents a logical gate or functional block (e.g., XOR gate, AND gate, inverter (~), MUX, or assign statement).
class Element(Component):
    def __init__(self, op_type, inputs, output, parent=None):
        self.op_type = op_type
        self.inputs = inputs
        self.output = output
        self.parent = parent

    def to_dict(self):
        d = {
            "type": "element",
            "op": self.op_type,
            "in": self.inputs,
            "out": self.output
        }
        # TODO add more SVG mappings for different op types
        if self.op_type == "~" or self.op_type == "not":
            d["svg"] = "svgs/NOT-gate.svg"
        return d

    def to_verilog(self):
        # TODO Maybe we can have extend class instead of if-else if we want to support more complex elements. But for now we can just use if-else for the prototype.
        if self.op_type == "assign":
            return f"assign {self.output} = {self.inputs[0]};"
        elif self.op_type == "mux":
            return f"assign {self.output} = {self.inputs[0]} ? {self.inputs[1]} : {self.inputs[2]};"
        elif self.op_type == "xor":
            return f"assign {self.output} = {' ^ '.join(self.inputs)};"
        elif self.op_type == "logic_expr":
            return f"assign {self.output} = {self.inputs[0]};"
        elif self.op_type == "~" or self.op_type == "not":
            return f"assign {self.output} = ~{self.inputs[0]};"
        else:
            return f"assign {self.output} = {self.op_type}({', '.join(self.inputs)});"

# Represents an instantiation of a submodule within a parent module.
# connections maps port names to parent signals (e.g., .clk(system_clock)).
class ModuleInstance(Component):
    def __init__(self, module_type, name, connections=None, parent=None):
        self.module_type = module_type
        self.name = name
        self.connections = connections or {}
        self.parent = parent
        self.ports = []
        
    def get_ports(self): return self.ports
    def get_elements(self): return []
    def get_submodules(self): return []
    def get_instances(self): return []
    def get_wires(self): return []

    def to_dict(self):
        return {
            "type": "instance",
            "module_type": self.module_type,
            "name": self.name,
            "connections": self.connections
        }

    def to_verilog(self):
        if not self.connections:
            return f"{self.module_type} {self.name} ();"
        conns = []
        for port, sig in self.connections.items():
            conns.append(f".{port}({sig})")
        conn_str = ",\n        ".join(conns)
        return f"{self.module_type} {self.name} (\n        {conn_str}\n    );"

# Represents a full Verilog module (module ... endmodule).
# It serves as a composite node, holding ports, logic elements, wires, and submodule instances.
class VerilogModule(Component):
    def __init__(self, name, parent=None):
        self.name = name
        self.components = []
        self.declared_wires = []
        self.warnings = []
        self.parent = parent

    def add(self, component: Component):
        if hasattr(component, "parent"):
            component.parent = self
        self.components.append(component)

    def get_ports(self):
        return [c for c in self.components if isinstance(c, Port)]

    def get_elements(self):
        return [c for c in self.components if isinstance(c, Element)]

    def get_wires(self):
        return [c for c in self.components if isinstance(c, Wire)]

    def get_submodules(self):
        return [c for c in self.components if isinstance(c, VerilogModule)]

    def get_instances(self):
        return [c for c in self.components if isinstance(c, ModuleInstance)]

    def to_dict(self):
        return {
            "type": "module",
            "name": self.name,
            "ports": [p.to_dict() for p in self.get_ports()],
            "elements": [e.to_dict() for e in self.get_elements()],
            "wires": [w.to_dict() for w in self.get_wires()],
            "submodules": [m.to_dict() for m in self.get_submodules()],
            "instances": [i.to_dict() for i in self.get_instances()],
            "declared_wires": self.declared_wires
        }

    def to_verilog(self):
        ports = self.get_ports()
        elements = self.get_elements()
        submodules = self.get_submodules()
        instances = self.get_instances()
        
        ports_str = [p.to_verilog() for p in ports]
        ports_decl = ",\n    ".join(ports_str)
        
        code = f"module {self.name} (\n    {ports_decl}\n);\n"
        
        body_elements = [el.to_verilog() for el in elements if el.to_verilog()]
        if body_elements:
            code += "\n    " + "\n    ".join(body_elements) + "\n"
            
        if instances:
            for inst in instances:
                inst_code = inst.to_verilog()
                indented_inst = "\n".join("    " + line for line in inst_code.split("\n"))
                code += "\n" + indented_inst + "\n"
        
        if submodules:
            for sub in submodules:
                sub_code = sub.to_verilog()
                indented_sub = "\n".join("    " + line for line in sub_code.split("\n"))
                code += "\n" + indented_sub + "\n"
            
        if not body_elements and not submodules and not instances:
            code += "\n"
            
        code += "\nendmodule"
        return code

    
# --- Factory Method Pattern ---
# ElementFactory instantiates the correct logical 'Element' representation
# based on the parsed assignment expression (e.g., ternary operator (?) maps to a 'mux' element).
class ElementFactory:
    @staticmethod
    def create_element_from_assign(target, expr):
        expr = expr.strip().strip(';')
        
        # Mux pattern: sel ? b : a
        mux_match = re.match(r'(.+?)\s*\?\s*(.+?)\s*:\s*(.+)', expr)
        if mux_match:
            return Element("mux", [mux_match.group(1).strip(), mux_match.group(2).strip(), mux_match.group(3).strip()], target)
            
        # Basic logic gates (simplified parser for prototype)
        # This is a very rudimentary parser, a real one would use an AST
        if '^' in expr and not ('&' in expr or '|' in expr):
            parts = [p.strip(' ()') for p in expr.split('^')]
            return Element("xor", parts, target)
            
        if '&' in expr and not ('|' in expr or '^' in expr):
            parts = [p.strip(' ()') for p in expr.split('&')]
            return Element("&", parts, target)
        if '|' in expr and not ('&' in expr or '^' in expr):
            parts = [p.strip(' ()') for p in expr.split('|')]
            return Element("|", parts, target)
        
        if '&' in expr or '|' in expr or '^' in expr:
            # For complex mixed logic, use a generic element but try to extract variable names
            # Extract all word characters as potential inputs
            parts = [p for p in re.findall(r'[a-zA-Z_]\w*', expr)]
            return Element("logic_expr", parts, target)

        if expr.startswith('~'):
            return Element("~", [expr[1:].strip(' ()')], target)

        # Simple assignment
        return Element("assign", [expr], target)

def parse_ports(ports_text, module_obj):
    lines = ports_text.split('\n')
    for line in lines:
        line = line.strip().rstrip(',').rstrip(')')
        if not line: continue
        pattern = r'^\s*(?P<direction>input|output)\s+(?P<type>wire|reg)?\s*(?:\[(?P<vector>[^\]]+)\])?\s*(?P<name>\w+)'
        match = re.match(pattern, line)
        if match:
            data = match.groupdict()
            module_obj.add(Port(data['name'], data['direction'], data['vector']))

def parse_body(body_text, module_obj):
    # Find declared wires
    wire_matches = re.finditer(r'\bwire\s+(?:\[[^\]]+\]\s+)?([a-zA-Z_]\w*)\s*;', body_text)
    for match in wire_matches:
        module_obj.declared_wires.append(match.group(1))

    # Find all assign statements
    assign_matches = re.finditer(r'\bassign\s+([\w.]+)\s*=\s*(.*?);', body_text, re.DOTALL)
    for match in assign_matches:
        target = match.group(1)
        expr = match.group(2)
        element = ElementFactory.create_element_from_assign(target, expr)
        module_obj.add(element)
        # For assign, the source of the wire is the input expression
        source = element.inputs[0] if element.op_type == "assign" else f"{element.op_type}_{target}"
        module_obj.add(Wire(target, source))
        
    # Find instantiations like: ModuleType InstanceName (.port(sig), .port2(sig2));
    inst_matches = re.finditer(r'\b([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*;', body_text, re.DOTALL)
    keywords = {"module", "endmodule", "assign", "wire", "reg", "input", "output", "inout", "always", "initial"}
    for match in inst_matches:
        mod_type = match.group(1)
        if mod_type in keywords:
            continue
        inst_name = match.group(2)
        ports_text = match.group(3)
        
        connections = {}
        port_matches = re.finditer(r'\.\s*([A-Za-z_]\w*)\s*\(\s*([A-Za-z0-9_.]*)\s*\)', ports_text)
        for p_match in port_matches:
            connections[p_match.group(1)] = p_match.group(2)
            
        module_obj.add(ModuleInstance(mod_type, inst_name, connections))

def strip_comments(text):
    # remove block comments /* ... */
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # remove line comments // ...
    text = re.sub(r'//.*?\n', '\n', text)
    return text

def remove_nested_modules(text):
    while True:
        match = re.search(r'\bmodule\b.*?\bendmodule\b', text, re.DOTALL)
        if not match:
            break
        text = text[:match.start()] + text[match.end():]
    return text

# Main orchestration function that parses Verilog source text.
# It extracts module declarations, processes ports and wires, matches assignments,
# links submodule ports to parent wires, and returns a list of root-level VerilogModule ASTs.
def extract_verilog(verilog_text):
    text = strip_comments(verilog_text)
    
    matches = list(re.finditer(r'\b(module|endmodule)\b', text))
    
    stack = []
    root_modules = []
    
    for m in matches:
        keyword = m.group(1)
        start_idx = m.start()
        
        if keyword == 'module':
            header_match = re.match(r'module\s+(\w+)\s*(?:\((.*?)\))?\s*;', text[start_idx:], re.DOTALL)
            if header_match:
                name = header_match.group(1)
                ports_text = header_match.group(2) or ""
                mod = VerilogModule(name)
                parse_ports(ports_text, mod)
                
                body_start = start_idx + header_match.end()
                stack.append((mod, body_start))
            else:
                stack.append((None, start_idx))
        elif keyword == 'endmodule':
            if stack:
                mod, body_start = stack.pop()
                if mod:
                    body_text = text[body_start:start_idx]
                    
                    # Remove any nested module strings from the body text of mod
                    # so that top-level module parser doesn't extract its submodules' assignments
                    clean_body_text = remove_nested_modules(body_text)
                    parse_body(clean_body_text, mod)
                    
                    if stack and stack[-1][0]:
                        stack[-1][0].add(mod)
                    else:
                        root_modules.append(mod)
                        
    # Linking pass to populate ports of ModuleInstances
    module_map = {m.name: m for m in root_modules}
    for m in root_modules:
        for inst in m.get_instances():
            if inst.module_type in module_map:
                inst.ports = copy.deepcopy(module_map[inst.module_type].get_ports())
                matched_ports = set()
                for p in inst.ports: 
                    p.parent = inst
                    if p.name in inst.connections:
                        matched_ports.add(p.name)
                        net_name = inst.connections[p.name]
                        # Based on port direction, determine wire target and source
                        if p.direction == "input":
                            m.add(Wire(target=f"{inst.name}.{p.name}", source=net_name))
                        elif p.direction == "output":
                            m.add(Wire(target=net_name, source=f"{inst.name}.{p.name}"))
                            
                # Check for mismatched ports and generate warnings
                unmatched_conns = [k for k in inst.connections.keys() if k not in matched_ports]
                if unmatched_conns:
                    for k in unmatched_conns:
                        m.warnings.append(f"Warning: Port '.{k}' not found in module '{inst.module_type}' (instantiated as '{inst.name}').")
                        
    return root_modules

if __name__ == "__main__":
    verilog_file_path = "verilog/p02_flat.v"
    try:
        with open(verilog_file_path, "r") as f:
            verilog_text = f.read()
            
        modules = extract_verilog(verilog_text)
        
        output_file = "output.json"
        with open(output_file, "w") as f:
            json.dump([m.to_dict() for m in modules], f, indent=4)
        print(f"Successfully extracted {len(modules)} modules to {output_file}")
    except FileNotFoundError:
        print(f"File {verilog_file_path} not found.")
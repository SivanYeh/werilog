import re

class ValidationError:
    def __init__(self, message: str, line_number: int, severity: str = "error"):
        self.message = message
        self.line_number = line_number
        self.severity = severity

    def to_dict(self):
        return {
            "message": self.message,
            "line_number": self.line_number,
            "severity": self.severity
        }
        
    def __str__(self):
        return f"Line {self.line_number}: [{self.severity.upper()}] {self.message}"

class NestedModuleError(ValidationError):
    def __init__(self, mod_name: str, parent_name: str, line_number: int):
        super().__init__(
            f"Nested module declaration is not allowed. Module '{mod_name}' is declared inside '{parent_name}'.",
            line_number
        )

class DuplicateModuleError(ValidationError):
    def __init__(self, mod_name: str, line_number: int):
        super().__init__(
            f"Duplicate module definition for '{mod_name}'.",
            line_number
        )

class DuplicatePortError(ValidationError):
    def __init__(self, port_name: str, mod_name: str, line_number: int):
        super().__init__(
            f"Duplicate port name '{port_name}' in module '{mod_name}' declaration.",
            line_number
        )

class InputAssignmentError(ValidationError):
    def __init__(self, assigned_var: str, mod_name: str, line_number: int):
        super().__init__(
            f"Cannot assign to input port '{assigned_var}' inside module '{mod_name}'.",
            line_number
        )

class UnclosedModuleError(ValidationError):
    def __init__(self, mod_name: str, line_number: int):
        super().__init__(
            f"Module '{mod_name}' is declared but not closed with 'endmodule'.",
            line_number
        )

class MismatchedEndmoduleError(ValidationError):
    def __init__(self, line_number: int):
        super().__init__(
            "Found 'endmodule' without a matching 'module' declaration.",
            line_number
        )

class UndeclaredWireError(ValidationError):
    def __init__(self, wire_name: str, mod_name: str, line_number: int):
        super().__init__(
            f"Undeclared identifier '{wire_name}' used in module '{mod_name}'.",
            line_number
        )


class VerilogSyntaxErrorDetector:
    def __init__(self):
        pass

    def check_syntax(self, code_text: str) -> list[ValidationError]:
        errors = []
        
        # 1. Strip comments but preserve newlines to keep line numbers accurate
        # Replace block comments with the same number of newlines they span
        def strip_block_comments(match):
            return '\n' * match.group(0).count('\n')
            
        clean_text = re.sub(r'/\*.*?\*/', strip_block_comments, code_text, flags=re.DOTALL)
        # Line comments: remove comment text but keep the trailing newline
        clean_text = re.sub(r'//[^\n]*', '', clean_text)
        
        # Find all occurrences of module/endmodule declarations
        matches = list(re.finditer(r'\b(module|endmodule)\b', clean_text))
        
        module_stack = []  # Elements: (module_name, start_index)
        defined_modules = set()
        
        for m in matches:
            keyword = m.group(1)
            idx = m.start()
            line_no = clean_text[:idx].count('\n') + 1
            
            if keyword == 'module':
                # Try to extract the module name
                header_match = re.match(r'module\s+(\w+)', clean_text[idx:])
                mod_name = header_match.group(1) if header_match else "unknown"
                
                # Check for nesting
                if len(module_stack) > 0:
                    parent_name = module_stack[-1][0]
                    errors.append(NestedModuleError(mod_name, parent_name, line_no))
                
                # Check for duplicate module names
                if mod_name != "unknown":
                    if mod_name in defined_modules:
                        errors.append(DuplicateModuleError(mod_name, line_no))
                    else:
                        defined_modules.add(mod_name)
                
                module_stack.append((mod_name, idx))
                
                # Perform basic validation of the module ports
                semi_match = re.search(r';', clean_text[idx:])
                if semi_match:
                    header_text = clean_text[idx:idx + semi_match.start()]
                    # Extract port names
                    ports_match = re.search(r'\((.*?)\)', header_text, re.DOTALL)
                    if ports_match:
                        ports_start = ports_match.start(1)
                        ports_content = ports_match.group(1)
                        ports_list_raw = ports_content.split(',')
                        
                        current_offset = ports_start
                        port_names = []
                        for port_decl in ports_list_raw:
                            decl_stripped = port_decl.strip()
                            if decl_stripped:
                                decl_start_local = port_decl.find(decl_stripped)
                                actual_offset = current_offset + decl_start_local
                                port_line = clean_text[:idx + actual_offset].count('\n') + 1
                                
                                words = re.findall(r'\b\w+\b', decl_stripped)
                                if words:
                                    port_name = words[-1]
                                    if port_name in port_names:
                                        errors.append(DuplicatePortError(port_name, mod_name, port_line))
                                    else:
                                        port_names.append(port_name)
                            current_offset += len(port_decl) + 1
            
            elif keyword == 'endmodule':
                if not module_stack:
                    errors.append(MismatchedEndmoduleError(line_no))
                else:
                    mod_name, start_idx = module_stack.pop()
                    
                    # Validate the body of the module that just ended
                    body_text = clean_text[start_idx:idx]
                    
                    # Parse declared input ports to prevent inputs being assignment targets
                    declared_signals = set()
                    input_ports = set()
                    semi_match = re.search(r';', body_text)
                    if semi_match:
                        header_text = body_text[:semi_match.start()]
                        ports_text = re.search(r'\((.*?)\)', header_text, re.DOTALL)
                        if ports_text:
                            for port_line in ports_text.group(1).split(','):
                                port_line = port_line.strip()
                                words = re.findall(r'\b\w+\b', port_line)
                                if words:
                                    declared_signals.add(words[-1])
                                    if 'input' in words:
                                        input_ports.add(words[-1])
                                        
                    # Find wire/reg declarations
                    wire_matches = re.finditer(r'\b(?:wire|reg)\s+([a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)\s*;', body_text)
                    for wm in wire_matches:
                        for sig in wm.group(1).split(','):
                            declared_signals.add(sig.strip())
                                        
                    # Track assignments for InputAssignmentError and UndeclaredWireError
                    assign_matches = re.finditer(r'\bassign\s+(\w+)\s*=\s*(.*?);', body_text, re.DOTALL)
                    for am in assign_matches:
                        assigned_var = am.group(1)
                        assign_line = clean_text[:start_idx + am.start()].count('\n') + 1
                        if assigned_var in input_ports:
                            errors.append(InputAssignmentError(assigned_var, mod_name, assign_line))
                        if assigned_var not in declared_signals:
                            errors.append(UndeclaredWireError(assigned_var, mod_name, assign_line))
                            
                        # Check rhs for undeclared identifiers
                        for match in re.finditer(r"\d+'[bBoOdDqQhH][0-9a-fA-F_xzXZ]+|[a-zA-Z_]\w*", am.group(2)):
                            token = match.group(0)
                            if (token[0].isalpha() or token[0] == '_') and token not in declared_signals:
                                errors.append(UndeclaredWireError(token, mod_name, assign_line))

                    # Check instance connections for undeclared wires
                    inst_matches = re.finditer(r'\b([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*;', body_text, re.DOTALL)
                    for im in inst_matches:
                        ports_txt = im.group(3)
                        inst_line = clean_text[:start_idx + im.start()].count('\n') + 1
                        conn_matches = re.finditer(r'\.\s*[A-Za-z_]\w*\s*\(\s*([A-Za-z0-9_.]*)\s*\)', ports_txt)
                        for cm in conn_matches:
                            sig = cm.group(1).strip()
                            if sig:
                                for match in re.finditer(r"\d+'[bBoOdDqQhH][0-9a-fA-F_xzXZ]+|[a-zA-Z_]\w*", sig):
                                    token = match.group(0)
                                    if (token[0].isalpha() or token[0] == '_') and token not in declared_signals:
                                        errors.append(UndeclaredWireError(token, mod_name, inst_line))
                            
        # Unclosed modules
        for mod_name, start_idx in module_stack:
            line_no = clean_text[:start_idx].count('\n') + 1
            errors.append(UnclosedModuleError(mod_name, line_no))
            
        return errors

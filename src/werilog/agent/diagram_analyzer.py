import json
import re
from typing import Any
import base64
import os
import torch
import gc
from io import BytesIO
from PIL import Image
from transformers import pipeline
from collections import defaultdict
import yaml


def sanitize_name(name: str) -> str:
    """
    Convert visual labels into safe YAML/module identifiers.
    Example: "Top-module" -> "Top_module"
    """
    name = name.strip()
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


class DSU:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        self.parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        self.parent[self.find(b)] = self.find(a)


def visual_json_to_module_dict(
    data: dict[str, Any],
    *,
    expand_internal_output_aliases: bool = True,
) -> dict[str, Any]:

    elements = data.get("elements", [])
    connections = data.get("connections", [])

    by_id: dict[str, dict[str, Any]] = {
        element["id"]: element
        for element in elements
    }

    modules: dict[str, dict[str, Any]] = {
        element["id"]: element
        for element in elements
        if element.get("type") == "module"
    }

    ports: dict[str, dict[str, Any]] = {
        element["id"]: element
        for element in elements
        if element.get("type") in {"input", "output"}
    }

    if not modules:
        raise ValueError("No module elements found.")

    roots = [
        module_id
        for module_id, module in modules.items()
        if module.get("parent") is None
    ]

    if len(roots) != 1:
        raise ValueError(f"Expected exactly one root module, found {len(roots)}: {roots}")

    root_id = roots[0]

    children_modules: dict[str | None, list[str]] = defaultdict(list)
    child_ports: dict[str, list[str]] = defaultdict(list)

    element_order = {
        element["id"]: index
        for index, element in enumerate(elements)
    }

    for module_id, module in modules.items():
        children_modules[module.get("parent")].append(module_id)

    for port_id, port in ports.items():
        parent = port.get("parent")
        if parent not in modules:
            raise ValueError(f"Port {port_id!r} has invalid parent {parent!r}")
        child_ports[parent].append(port_id)

    for ids in children_modules.values():
        ids.sort(key=lambda x: element_order[x])

    for ids in child_ports.values():
        ids.sort(key=lambda x: element_order[x])

    module_name: dict[str, str] = {
        module_id: sanitize_name(module.get("label") or module_id)
        for module_id, module in modules.items()
    }

    def port_name(port_id: str) -> str:
        port = ports[port_id]
        label = port.get("label")
        if not label:
            raise ValueError(f"Port {port_id!r} has no label.")
        return sanitize_name(label)

    def qualified_port(port_id: str) -> str:
        port = ports[port_id]
        owner_id = port["parent"]
        return f"{module_name[owner_id]}.{port_name(port_id)}"

    def module_ancestors(module_id: str) -> list[str]:
        result = []
        current: str | None = module_id

        while current is not None:
            result.append(current)
            current = modules[current].get("parent")

        return result

    def lca_module(module_a: str, module_b: str) -> str:
        ancestors_a = module_ancestors(module_a)
        ancestors_b = set(module_ancestors(module_b))

        for ancestor in ancestors_a:
            if ancestor in ancestors_b:
                return ancestor

        raise ValueError(f"No common ancestor for modules {module_a!r} and {module_b!r}")

    # Build internal same-module port groups.
    # Example:
    #   Mod2.in2 -> Mod2.out3 -> Mod2.out4
    # becomes one internal group:
    #   in:  [Mod2.in2]
    #   out: [Mod2.out3, Mod2.out4]
    internal_dsu_by_module: dict[str, DSU] = {
        module_id: DSU()
        for module_id in modules
    }

    for module_id, port_ids in child_ports.items():
        for port_id in port_ids:
            internal_dsu_by_module[module_id].add(port_id)

    for conn in connections:
        source_id = conn.get("source")
        target_id = conn.get("target")

        if source_id not in ports or target_id not in ports:
            continue

        source_parent = ports[source_id]["parent"]
        target_parent = ports[target_id]["parent"]

        if source_parent == target_parent:
            internal_dsu_by_module[source_parent].union(source_id, target_id)

    internal_components_by_module: dict[str, dict[str, list[str]]] = {}
    component_of_port: dict[str, list[str]] = {}

    for module_id, dsu in internal_dsu_by_module.items():
        groups: dict[str, list[str]] = defaultdict(list)

        for port_id in child_ports[module_id]:
            root = dsu.find(port_id)
            groups[root].append(port_id)

        sorted_groups: dict[str, list[str]] = {}

        for root, group_ports in groups.items():
            group_ports.sort(key=lambda x: element_order[x])
            sorted_groups[root] = group_ports

            for port_id in group_ports:
                component_of_port[port_id] = group_ports

        internal_components_by_module[module_id] = sorted_groups

    def output_aliases(port_id: str) -> list[str]:
        """
        For an output port, return all output ports in the same internal component.

        Example:
        If Mod2 has internal wire:
            Mod2.in2 -> Mod2.out3, Mod2.out4

        and an external connection starts from Mod2.out4, this can expand to:
            Mod2.out3
            Mod2.out4
        """
        if not expand_internal_output_aliases:
            return [port_id]

        port = ports[port_id]

        if port.get("type") != "output":
            return [port_id]

        group = component_of_port.get(port_id, [port_id])

        aliases = [
            candidate_id
            for candidate_id in group
            if ports[candidate_id].get("type") == "output"
        ]

        return aliases or [port_id]

    external_wires_by_module: dict[str, list[dict[str, list[str]]]] = defaultdict(list)
    seen_external_wires: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()

    for conn in connections:
        source_id = conn.get("source")
        target_id = conn.get("target")

        if source_id not in ports or target_id not in ports:
            continue

        source_parent = ports[source_id]["parent"]
        target_parent = ports[target_id]["parent"]

        # Same-parent port connections become internal wires, not parent-level wires.
        if source_parent == target_parent:
            continue

        owner = lca_module(source_parent, target_parent)

        for expanded_source_id in output_aliases(source_id):
            wire = {
                "type": "wire",
                "in": [qualified_port(expanded_source_id)],
                "out": [qualified_port(target_id)],
            }

            key = (
                owner,
                tuple(wire["in"]),
                tuple(wire["out"]),
            )

            if key not in seen_external_wires:
                seen_external_wires.add(key)
                external_wires_by_module[owner].append(wire)

    def internal_wires_for_module(module_id: str) -> list[dict[str, Any]]:
        wires: list[dict[str, Any]] = []

        for group_ports in internal_components_by_module[module_id].values():
            input_ports = [
                port_id
                for port_id in group_ports
                if ports[port_id].get("type") == "input"
            ]

            output_ports = [
                port_id
                for port_id in group_ports
                if ports[port_id].get("type") == "output"
            ]

            if not input_ports or not output_ports:
                continue

            wires.append(
                {
                    "type": "wire",
                    "in": [qualified_port(port_id) for port_id in input_ports],
                    "out": [qualified_port(port_id) for port_id in output_ports],
                }
            )

        return wires

    def build_module(module_id: str) -> dict[str, Any]:
        input_ports = [
            port_id
            for port_id in child_ports[module_id]
            if ports[port_id].get("type") == "input"
        ]

        output_ports = [
            port_id
            for port_id in child_ports[module_id]
            if ports[port_id].get("type") == "output"
        ]

        module_dict: dict[str, Any] = {
            "type": "module",
            "name": module_name[module_id],
            "in": [port_name(port_id) for port_id in input_ports],
            "out": [port_name(port_id) for port_id in output_ports],
            "op": [],
        }

        # Nested modules first.
        for child_module_id in children_modules.get(module_id, []):
            module_dict["op"].append(build_module(child_module_id))

        # Internal wires inside this module.
        module_dict["op"].extend(internal_wires_for_module(module_id))

        # Wires between child modules / ports owned by different modules.
        module_dict["op"].extend(external_wires_by_module.get(module_id, []))

        return module_dict

    return build_module(root_id)


def visual_json_to_yaml(
    data: dict[str, Any],
    *,
    expand_internal_output_aliases: bool = True,
) -> str:

    module_dict = visual_json_to_module_dict(
        data,
        expand_internal_output_aliases=expand_internal_output_aliases,
    )

    yaml_text = yaml.safe_dump(
        module_dict,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )

    return yaml_text

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        image = Image.open(image_file)
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        base64_encoded_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
    return f"data:image/png;base64,{base64_encoded_data}"


def extract_json_object(text: str) -> dict[str, Any]:

    text = text.strip()

    # Remove markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No complete JSON object found in model output:\n{text}")

    json_text = text[start:end + 1]
    return json.loads(json_text)

def load_file(file_name: str) -> str:
    file = open(file_name, "r")
    content = file.read()
    file.close()
    return content

class DiagramAnalyzer:
    def __init__(self):
        self.pipe = pipeline(
            "image-text-to-text",
            model="OpenGVLab/InternVL3-8B-hf",
            device_map="auto",
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release_agent()

    def release_agent(self):
        if getattr(self, "pipe", None) is not None:
            pipe = self.pipe
            self.pipe = None
            del pipe

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def call_agent(
        self,
        image_path: str,
        max_new_tokens: int = 512,
    ) -> dict[str, Any]:
        
        prompt = load_file(os.path.join(os.path.dirname(__file__), "diagram_analyzer_prompt.txt"))

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": { "url": encode_image(image_path)}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        outputs = self.pipe(
            text=messages,
            max_new_tokens=max_new_tokens,
            return_full_text=False,
        )

        generated_text = outputs[0]["generated_text"]
        visual_elements = extract_json_object(generated_text)
        return visual_json_to_yaml(visual_elements)
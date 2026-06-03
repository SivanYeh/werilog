from pathlib import Path
from typing import Tuple
from lxml import etree
import html
import networkx as nx
from pydantic import BaseModel
from typing import Literal


class OperationYaml(BaseModel):
    type: str
    in_: list[str]
    out: list[str]

    def to_yaml_dict(self):
        return {
            "type": self.type,
            "in": self.in_,
            "out": self.out,
        }


class ModuleYaml(BaseModel):
    type: Literal["module"] = "module"
    name: str
    in_: list[str]
    out: list[str]
    op: list[OperationYaml]

    def to_yaml_dict(self):
        return {
            "type": self.type,
            "name": self.name,
            "in": self.in_,
            "out": self.out,
            "op": [operation.to_yaml_dict() for operation in self.op],
        }

class SemanticNode(BaseModel):
    id: str
    kind: Literal["module", "input", "output", "label", "unknown", "group"]
    name: str
    operation_type: str | None = None
    mx_id: str

class MxGeometry(BaseModel):
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    relative: bool = False


class MxCell(BaseModel):
    id: str
    value: str = ""
    style_raw: str = ""
    style: dict[str, str | bool] = {}

    is_vertex: bool = False
    is_edge: bool = False

    parent: str | None = None
    source: str | None = None
    target: str | None = None

    geometry: MxGeometry | None = None

def parse_style(style: str) -> dict[str, str | bool]:
    result: dict[str, str | bool] = {}

    for item in style.split(";"):
        item = item.strip()
        if not item:
            continue

        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
        else:
            result[item] = True

    return result


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_geometry(cell) -> MxGeometry | None:
    geom = cell.find("mxGeometry")
    if geom is None:
        return None

    return MxGeometry(
        x=parse_float(geom.get("x")),
        y=parse_float(geom.get("y")),
        width=parse_float(geom.get("width")),
        height=parse_float(geom.get("height")),
        relative=geom.get("relative") == "1",
    )

def is_module_boundary(cell: MxCell) -> bool:
    if not cell.is_vertex or cell.geometry is None:
        return False

    style = cell.style
    value = cell.value.strip()

    # Common draw.io containers are rectangles/swimlanes/groups.
    shape = str(style.get("shape", "")).lower()

    if value and cell.geometry.width and cell.geometry.height:
        if cell.geometry.width > 100 and cell.geometry.height > 80:
            if "swimlane" in shape or "rectangle" in shape or shape == "":
                return True

    return False

def is_input_candidate(mx_id: str, graph: nx.DiGraph, cell: MxCell) -> bool:
    return (
        cell.is_vertex
        and graph.in_degree(mx_id) == 0
        and graph.out_degree(mx_id) > 0
        and bool(cell.value.strip())
    )


def is_output_candidate(mx_id: str, graph: nx.DiGraph, cell: MxCell) -> bool:
    return (
        cell.is_vertex
        and graph.in_degree(mx_id) > 0
        and graph.out_degree(mx_id) == 0
        and bool(cell.value.strip())
    )

def is_group(mx_id: str, graph: nx.DiGraph, cell: MxCell) -> bool:
    return(
        cell.is_vertex
        and graph.out_degree(mx_id) > 0
        and cell.style["group"] == True
    )

def classify_nodes(cells: dict[str, MxCell], graph: nx.DiGraph) -> dict[str, SemanticNode]:
    semantic: dict[str, SemanticNode] = {}

    for mx_id, cell in cells.items():
        if not cell.is_vertex:
            continue

        name = cell.value.strip()

        group = cell.style.get("group", False)
        shape = str(cell.style.get("shape", '')).lower()
        text = cell.style.get("text", False)
        if text:
            type = 'label'
        elif group:
            type = 'group'
        elif shape:
            type = shape
        else:
            type = 'rectangle'


        if is_module_boundary(cell):
            semantic[mx_id] = SemanticNode(
                id=name or mx_id,
                kind="module",
                name=name or mx_id,
                mx_id=mx_id,
            )
        elif is_group(mx_id, graph, cell):
            semantic[mx_id] = SemanticNode(
                id=name,
                kind='group',
                name=name,
                mx_id=mx_id
            )
        elif is_input_candidate(mx_id, graph, cell):
            semantic[mx_id] = SemanticNode(
                id=name,
                kind="input",
                name=name,
                mx_id=mx_id,
            )

        elif is_output_candidate(mx_id, graph, cell):
            semantic[mx_id] = SemanticNode(
                id=name,
                kind="output",
                name=name,
                mx_id=mx_id,
            )

        elif name:
            semantic[mx_id] = SemanticNode(
                id=name,
                kind="label",
                name=name,
                mx_id=mx_id,
            )

        else:
            semantic[mx_id] = SemanticNode(
                id=mx_id,
                kind="unknown",
                name=mx_id,
                mx_id=mx_id,
            )

    return semantic

def parse_mx_cells(mx_root) -> dict[str, MxCell]:
    cells: dict[str, MxCell] = {}

    for cell in mx_root.xpath(".//mxCell"):
        cell_id = cell.get("id")
        if cell_id is None:
            continue

        style_raw = cell.get("style", "")

        cells[cell_id] = MxCell(
            id=cell_id,
            value=cell.get("value", ""),
            style_raw=style_raw,
            style=parse_style(style_raw),
            is_vertex=cell.get("vertex") == "1",
            is_edge=cell.get("edge") == "1",
            parent=cell.get("parent"),
            source=cell.get("source"),
            target=cell.get("target"),
            geometry=parse_geometry(cell),
        )

    return cells

def build_raw_graph(cells: dict[str, MxCell]) -> Tuple[nx.DiGraph, nx.DiGraph]:
    graph_el = nx.DiGraph()
    graph_con = nx.DiGraph()

    for cell_id, cell in cells.items():
        if cell.is_vertex:
            graph_el.add_node(
                cell_id,
                value=cell.value,
                style=cell.style,
                geometry=cell.geometry,
                raw=cell,
            )
            graph_con.add_node(
                cell_id,
                value=cell.value,
                raw=cell,
            )

    for cell_id, cell in cells.items():
        if not cell.is_vertex:
            continue
        if cell.parent and cell.parent in graph_el:
            graph_el.add_edge(
                cell.parent,
                cell_id,
                raw=cell
            )
        if cell.is_edge and cell.source and cell.target:
            if cell.source in graph_con and cell.target in graph_con:
                graph_con.add_edge(
                    cell.source,
                    cell.target,
                    id=cell_id,
                    style=cell.style,
                    raw=cell,
                )

    return graph_el, graph_con

def extract_module_name(semantic_nodes: dict[str, SemanticNode]) -> str:
    modules = [
        node for node in semantic_nodes.values()
        if node.kind == "module" and node.name
    ]

    if modules:
        return modules[0].name

    return "UnknownModule"

def build_module_yaml(
    graph: nx.DiGraph,
    semantic_nodes: dict[str, SemanticNode],
) -> ModuleYaml:
    module_name = extract_module_name(semantic_nodes)

    inputs = [
        node.name
        for node in semantic_nodes.values()
        if node.kind == "input"
    ]

    outputs = [
        node.name
        for node in semantic_nodes.values()
        if node.kind == "output"
    ]

    operations: list[OperationYaml] = []

    for mx_id, node in semantic_nodes.items():
        if node.kind != "operation":
            continue

        input_refs = []
        output_refs = []

        for pred in graph.predecessors(mx_id):
            pred_node = semantic_nodes.get(pred)
            if pred_node and pred_node.kind == "input":
                input_refs.append(f"{module_name}.{pred_node.name}")

        for succ in graph.successors(mx_id):
            succ_node = semantic_nodes.get(succ)
            if succ_node and succ_node.kind == "output":
                output_refs.append(f"{module_name}.{succ_node.name}")

        operations.append(
            OperationYaml(
                type=node.operation_type or "unknown",
                in_=input_refs,
                out=output_refs,
            )
        )

    return ModuleYaml(
        name=module_name,
        in_=inputs,
        out=outputs,
        op=operations,
    )

def extract_drawio_model(svg_path: str):
    text = Path(svg_path).read_text(encoding="utf-8", errors="replace")
    root = etree.fromstring(text.encode("utf-8"))

    content = root.attrib.get("content")
    if not content or "mxGraphModel" not in content:
        return None

    mx_xml = html.unescape(content)
    mx_root = etree.fromstring(mx_xml.encode("utf-8"))
    mx_cells = parse_mx_cells(mx_root)
    g_el, g_con = build_raw_graph(mx_cells)

    # print("\n\n")
    # print(g_el.nodes(data=True))
    # print(g_el.edges(data=True))
    # print("\n\n")

    semantic_nodes = classify_nodes(mx_cells, g_el)
    module_yaml = build_module_yaml(g_el, semantic_nodes)

    return module_yaml

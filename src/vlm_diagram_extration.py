import re
from collections import Counter
from typing import Any


INPUT_PATTERNS = [
    re.compile(r"^in[0-9]+$"),
    re.compile(r"^input[0-9]+$"),
]

OUTPUT_PATTERNS = [
    re.compile(r"^out[0-9]+$"),
    re.compile(r"^o[0-9]+$"),
    re.compile(r"^[A-Za-z0-9]+_output$"),
    re.compile(r"^[A-Za-z0-9]+_out$"),
]

MODULE_PATTERNS = [
    re.compile(r"^Mod[A-Za-z0-9]+$"),
    re.compile(r"^Top_[A-Za-z0-9]+$"),
]


def infer_role_from_label(label: str | None) -> str | None:
    if not label:
        return None

    if any(p.match(label) for p in INPUT_PATTERNS):
        return "input_label"

    if any(p.match(label) for p in OUTPUT_PATTERNS):
        return "output_label"

    if any(p.match(label) for p in MODULE_PATTERNS):
        return "module_label"

    return "unknown"


def type_from_role(role: str | None) -> str | None:
    return {
        "input_label": "input",
        "output_label": "output",
        "module_label": "module",
    }.get(role)


def validate_diagram_json(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    elements = data.get("elements", [])

    ids = [e.get("id") for e in elements]
    id_counts = Counter(ids)

    for element_id, count in id_counts.items():
        if count > 1:
            errors.append(f"Duplicate element id: {element_id}")

    labels = [
        e.get("label")
        for e in elements
        if e.get("label") is not None
    ]
    label_counts = Counter(labels)

    for label, count in label_counts.items():
        if count > 1:
            errors.append(f"Duplicate label assigned to multiple elements: {label}")

    id_set = set(ids)

    for e in elements:
        element_id = e.get("id")
        element_type = e.get("type")
        label = e.get("label")
        label_role = e.get("label_role")

        inferred_role = infer_role_from_label(label)
        inferred_type = type_from_role(inferred_role)

        if inferred_role in {"input_label", "output_label", "module_label"}:
            if label_role != inferred_role:
                errors.append(
                    f"{element_id}: label '{label}' implies {inferred_role}, "
                    f"but label_role is {label_role}"
                )

            if element_type != inferred_type:
                errors.append(
                    f"{element_id}: label '{label}' implies type {inferred_type}, "
                    f"but type is {element_type}"
                )

        if element_type == "input" and label_role not in {"input_label", None}:
            errors.append(f"{element_id}: input has invalid label_role {label_role}")

        if element_type == "output" and label_role not in {"output_label", None}:
            errors.append(f"{element_id}: output has invalid label_role {label_role}")

        if element_type == "module" and label_role not in {"module_label", None}:
            errors.append(f"{element_id}: module has invalid label_role {label_role}")

        if element_type == "text" and label_role in {
            "input_label",
            "output_label",
            "module_label",
        }:
            errors.append(
                f"{element_id}: text element must not have semantic label_role {label_role}"
            )

        expected_prefix = {
            "input": "input_",
            "output": "output_",
            "module": "module_",
            "text": "text_",
        }.get(element_type)

        if expected_prefix and not str(element_id).startswith(expected_prefix):
            errors.append(
                f"{element_id}: id prefix does not match type {element_type}"
            )

    for conn in data.get("connections", []):
        conn_id = conn.get("id")

        source = conn.get("source")
        target = conn.get("target")

        if source is not None and source not in id_set:
            errors.append(f"{conn_id}: source '{source}' does not exist")

        if target is not None and target not in id_set:
            errors.append(f"{conn_id}: target '{target}' does not exist")

    return errors
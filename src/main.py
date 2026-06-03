import yaml
import json
import argparse
from pathlib import Path

from svg_parser import ModuleYaml
from client_qwen import ClientQwen
from client_internvl import ClientIntern

from dsu import visual_json_to_yaml


def dump_module_yaml(module: ModuleYaml) -> str:
    return yaml.safe_dump(
        module.to_yaml_dict(),
        sort_keys=False,
        allow_unicode=True,
    )

def load_file(file_name: str) -> str:
    file = open(file_name, "r")
    content = file.read()
    file.close()
    return content

def main() -> int:
    parser = argparse.ArgumentParser(description="Extract JSON graph from module/port diagram image.")
    parser.add_argument("-i", "--image", required=True, type=Path, help="Input PNG/JPEG image path.")
    parser.add_argument("-p", "--prompt", required=True, type=Path, help="Input prompt path.")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON path. Defaults to stdout.")
    args = parser.parse_args()

    ai_agent = ClientIntern();

    visual_elements = ai_agent.chat_json(
        image_path=args.image,
        prompt=load_file(args.prompt),
        max_new_tokens=8192
    )

    print(f"\n----JSON\n\n{json.dumps(visual_elements)}\n\n")

    yaml_text = visual_json_to_yaml(visual_elements)

    # print(f"\n\n---YAML\n\n{yaml_text}\n\n")

    if args.output:
        args.output.write_text(yaml_text + "\n", encoding="utf-8")
    else:
        print(yaml_text)


    return 0

if __name__ == "__main__":
    raise SystemExit(main())
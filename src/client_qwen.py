from transformers import Qwen2_5_VLForConditionalGeneration, AutoTokenizer, AutoProcessor, AutoModelForImageTextToText
from qwen_vl_utils import process_vision_info
import torch
from typing import Any
import json

from vlm_diagram_extration import validate_diagram_json

def extract_json_from_model_output(model_output: str | list[str]) -> dict[str, Any]:
    """
    Extract a valid JSON object from a VLM/LLM response.

    Handles:
    - list[str] responses
    - Markdown fenced blocks: ```json ... ```
    - text before/after the JSON object

    Raises ValueError if no complete valid JSON object is found.
    """

    if isinstance(model_output, list):
        text = "\n".join(model_output)
    else:
        text = model_output

    text = text.strip()

    # Remove common markdown fences
    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    # Find the first complete JSON object using brace matching
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output.")

    depth = 0
    in_string = False
    escape = False
    end = None

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise ValueError(
            "The model output does not contain a complete JSON object. "
            "The response was probably truncated."
        )

    json_text = text[start:end]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON extracted from model output: {e}") from e


class ClientQwen:

    def __init__(self):

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = AutoModelForImageTextToText.from_pretrained(
            "Qwen/Qwen2.5-VL-7B-Instruct",
            torch_dtype=torch.bfloat16,
        ).to(self.device).eval()

        self.processor = AutoProcessor.from_pretrained(
            "Qwen/Qwen2.5-VL-7B-Instruct"
        )

    def chat_json(
            self,
            content: list[dict[str, Any]],
            max_new_tokens: int = 512
    ):
        
        # print(f"\n\n{content}\n\n")

        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]

        # Preparation for inference
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to("cuda")

        # Inference: Generation of the output
        generated_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )

        result = extract_json_from_model_output(output_text)
        errors = validate_diagram_json(result)

        if errors:
            print("Invalid diagram JSON:")
            for error in errors:
                print("-", error)
        else:
            print("Diagram JSON is valid.")
        
        return result
        

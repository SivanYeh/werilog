import json
import re
from typing import Any

import base64
from pathlib import Path
from io import BytesIO
from PIL import Image

from transformers import pipeline

def encode_image(image_path: Path) -> str:
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


class ClientIntern:
    def __init__(self):
        self.pipe = pipeline(
            "image-text-to-text",
            model="OpenGVLab/InternVL3-8B-hf",
            device_map="auto",
        )

    def chat_json(
        self,
        image_path: Path,
        prompt: str,
        max_new_tokens: int = 512,
    ) -> dict[str, Any]:

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
        return extract_json_object(generated_text)
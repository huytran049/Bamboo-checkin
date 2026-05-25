import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VISION_OCR_WORKER = PROJECT_ROOT / "workers_swift" / "vision_ocr_only.swift"
DEFAULT_MODEL = "business-card"


PROMPT_TEMPLATE = """Extract business card information from the provided OCR text.
The OCR text may be noisy, out of order, or have characters split across lines.
Use context and business card patterns to reconstruct the correct information accurately.

Fields to extract:
- name: The person's full name.
  * Format: "Kanji Name / Romaji Name / ..." (or just one if only one exists).
  * Capture ALL variations found: Kanji, Romaji, Katakana, and Hiragana.
  * ONLY include variations present in the OCR. Do NOT use placeholder names like "KanjiName".
  * LOGICALLY MERGE Kanji characters if they are split across lines.
  * If multiple people are listed, separate each person with a comma.
- company: The company or organization name.
- email: Professional email address (e.g., name@company.com).
  * IMPORTANT: Do NOT put phone numbers or "TEL" strings in the email field.
- title: Job title or position.
- phone: Phone or Mobile number.
- address: Physical address.

Rules:
1. Prioritize accuracy for 'name', 'company', and 'email'.
2. If a field is not found, use an empty string "".
3. If strings are broken by OCR or split across lines, merge them logically.
4. Return ONLY a valid JSON object. No preamble or explanation.

OCR Text:
{ocr_text}

JSON Result:
"""


def run_vision_ocr(image_path: Path) -> str:
    if not VISION_OCR_WORKER.exists():
        raise FileNotFoundError(f"Missing OCR worker: {VISION_OCR_WORKER}")

    result = subprocess.run(
        ["swift", str(VISION_OCR_WORKER), str(image_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Vision OCR failed")

    ocr_text = result.stdout.strip()
    if not ocr_text:
        raise RuntimeError("Vision OCR returned empty text")
    return ocr_text


def call_ollama(model: str, prompt: str, timeout_sec: int) -> str:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")
    req = request.Request(
        "http://localhost:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"Failed to call Ollama: {exc}") from exc

    response_text = payload.get("response", "").strip()
    if not response_text:
        raise RuntimeError(f"Ollama returned no response for model '{model}'")
    return response_text


def clean_llm_output(raw_output: str) -> str:
    cleaned = raw_output.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json") :]
    if cleaned.startswith("```"):
        cleaned = cleaned[len("```") :]
    if cleaned.endswith("```"):
        cleaned = cleaned[: -len("```")]
    return cleaned.strip()


def normalize_fields(raw_output: str, ocr_text: str) -> dict:
    cleaned = clean_llm_output(raw_output)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {
            "name": "",
            "title": "",
            "company": "",
            "email": "",
            "phone": "",
            "address": "",
            "raw_response": cleaned,
        }

    if "name" in data and "full_name" not in data:
        data["full_name"] = data.pop("name")

    data["raw_ocr"] = ocr_text
    for key, value in list(data.items()):
        if isinstance(value, (dict, list)):
            data[key] = json.dumps(value, ensure_ascii=False)
        elif value is None:
            data[key] = ""
        else:
            data[key] = str(value)
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PoC runner for testing a business-card extraction model with the current OCR prompt."
    )
    parser.add_argument("--image", type=Path, help="Path to a business card image")
    parser.add_argument("--ocr-text-file", type=Path, help="Use an existing OCR text file instead of OCRing an image")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model to test. Default: {DEFAULT_MODEL}")
    parser.add_argument("--compare-model", help="Optional second Ollama model to compare against, e.g. qwen:7b")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds for each Ollama request")
    parser.add_argument("--save-json", type=Path, help="Optional path to save the normalized JSON result")
    return parser.parse_args()


def load_ocr_text(args: argparse.Namespace) -> str:
    if args.image:
        return run_vision_ocr(args.image.expanduser().resolve())
    if args.ocr_text_file:
        return args.ocr_text_file.expanduser().resolve().read_text(encoding="utf-8").strip()
    raise SystemExit("Provide either --image or --ocr-text-file")


def run_model(model: str, ocr_text: str, timeout_sec: int) -> tuple[str, dict]:
    prompt = PROMPT_TEMPLATE.format(ocr_text=ocr_text)
    raw_output = call_ollama(model, prompt, timeout_sec)
    normalized = normalize_fields(raw_output, ocr_text)
    return raw_output, normalized


def main() -> int:
    args = parse_args()
    ocr_text = load_ocr_text(args)

    print("=== OCR TEXT START ===")
    print(ocr_text)
    print("=== OCR TEXT END ===\n")

    raw_output, normalized = run_model(args.model, ocr_text, args.timeout)
    print(f"=== MODEL: {args.model} RAW OUTPUT ===")
    print(raw_output)
    print(f"=== MODEL: {args.model} NORMALIZED JSON ===")
    print(json.dumps(normalized, ensure_ascii=False, indent=2))

    if args.compare_model:
        compare_raw, compare_normalized = run_model(args.compare_model, ocr_text, args.timeout)
        print()
        print(f"=== MODEL: {args.compare_model} RAW OUTPUT ===")
        print(compare_raw)
        print(f"=== MODEL: {args.compare_model} NORMALIZED JSON ===")
        print(json.dumps(compare_normalized, ensure_ascii=False, indent=2))

    if args.save_json:
        args.save_json.expanduser().resolve().write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

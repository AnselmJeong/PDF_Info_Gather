from dotenv import load_dotenv
import os
import tomllib  # for Python >= 3.11
from openai import OpenAI
from groq import Groq
from PyPDF2 import PdfReader
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional


load_dotenv()


def load_config(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        config = tomllib.load(f)
    return {
        "system_prompt": config["ai"]["system_prompt"],
        "user_prompt": config["ai"]["user_prompt"],
        "aggregate_prompt": config["ai"]["aggregate_prompt"],
        "deepseek_base_url": config["model"]["deepseek_base_url"],
        "qwen_base_url": config["model"]["qwen_base_url"],
        "deepseek_model_name": config["model"]["deepseek_model_name"],
        "groq_model_name": config["model"]["groq_model_name"],
        "qwen_model_name": config["model"]["qwen_model_name"],
        "openai_model_name": config["model"]["openai_model_name"],
        "temperature": config["model"]["temperature"],
        "cache_dir": Path(config["paths"].get("cache_dir", "cache")),
        "pdf_dir": Path(config["paths"].get("pdf_dir", "documents")),
        "output_dir": Path(config["paths"].get("output_dir", "output")),
    }


config = load_config("config.toml")


# Access settings like:

clients = {
    "deepseek": OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=config["deepseek_base_url"]),
    "groq": Groq(api_key=os.getenv("GROQ_API_KEY")),
    "qwen": OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"), base_url=config["qwen_base_url"]),
    "openai": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
}


def get_file_hash(file_path: Path) -> str:
    """Generate a hash of the file content and modification time."""
    hash_md5 = hashlib.md5()
    hash_md5.update(file_path.read_bytes())
    hash_md5.update(str(file_path.stat().st_mtime).encode())
    return hash_md5.hexdigest()


def get_cache_path(pdf_path: Path, cache_dir: Path) -> Path:
    """Generate cache file path from PDF path."""
    file_hash = get_file_hash(pdf_path)
    cache_filename = f"{pdf_path.stem}_{file_hash}.json"
    return cache_dir / cache_filename


def load_from_cache(pdf_path: Path, cache_dir: Path) -> Optional[str]:
    """Try to load PDF text from cache."""
    cache_path = get_cache_path(pdf_path, cache_dir)

    if not cache_path.exists():
        return None

    try:
        cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
        return cache_data["text"]
    except (json.JSONDecodeError, KeyError):
        return None


def save_to_cache(pdf_path: Path, text: str, cache_dir: Path) -> None:
    """Save extracted text to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = get_cache_path(pdf_path, cache_dir)

    cache_data = {
        "text": text,
        "pdf_path": str(pdf_path),
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "pdf_modified": datetime.fromtimestamp(pdf_path.stat().st_mtime, timezone.utc).isoformat(),
    }

    cache_path.write_text(json.dumps(cache_data, ensure_ascii=False), encoding="utf-8")


def extract_text_from_pdf(pdf_path: Path | str) -> str:
    """Extract text from a PDF file with caching."""
    if isinstance(pdf_path, str):
        pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if not pdf_path.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")
    if not pdf_path.suffix.lower() == ".pdf":
        raise ValueError(f"Provided path is not a PDF file: {pdf_path}")

    # Try to load from cache first
    cache_dir = Path(config["cache_dir"])
    cached_text = load_from_cache(pdf_path, cache_dir)
    if cached_text is not None:
        print(f"Using cached version of {pdf_path.name}")
        return cached_text

    # If not in cache, extract text
    print(f"Extracting text from {pdf_path.name}")
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    # Save to cache
    save_to_cache(pdf_path, text, cache_dir)

    return text


def generate_messages(pdf_path: Path | str, config: dict) -> list[dict]:
    return [
        {"role": "system", "content": config["system_prompt"]},
        {
            "role": "user",
            "content": config["user_prompt"].format(document=extract_text_from_pdf(pdf_path)),
        },
    ]


def query(pdf_path: Path | str, provider: str) -> str:
    client = clients[provider]

    response = client.beta.chat.completions.parse(
        model=config[f"{provider}_model_name"],
        messages=generate_messages(pdf_path, config),
        temperature=config["temperature"],
        response_format={"type": "json_object"},
    )
    # print(response.choices[0].message.content)
    return response.choices[0].message.content

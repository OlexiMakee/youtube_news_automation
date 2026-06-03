"""
Thumbnail OCR Helper for YouTube News Automation.
Extracts text from video thumbnails using local Tesseract OCR, with a fallback
to Gemini Vision when local OCR is unavailable or fails.
"""

import os
import io
import base64
import requests
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

# Ensure environment variables are loaded
from scraper.utils import load_env
load_env()

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com"
DEFAULT_GEMINI_OCR_MODELS = ("gemini-2.5-flash", "gemini-2.0-flash")
_GEMINI_OCR_MODEL_CACHE = None


def download_thumbnail(video_id):
    """
    Downloads the YouTube thumbnail for the given video_id.
    Tries mqdefault first, then hqdefault.
    
    Returns:
        bytes or None: The image bytes, or None if download failed.
    """
    urls = [
        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200 and len(response.content) > 100:
                return response.content
        except Exception as e:
            print(f"[OCR] Error downloading thumbnail from {url}: {e}")
            
    return None


def run_local_ocr(image_bytes):
    """
    Attempts to run local Tesseract OCR on the image bytes.
    
    Returns:
        str: Extracted text if successful, raises Exception if Tesseract fails.
    """
    if not pytesseract:
        raise ImportError("pytesseract package is not installed.")
        
    image = Image.open(io.BytesIO(image_bytes))
    
    # Try Ukrainian + English OCR, fallback to English if the ukr langpack is missing
    try:
        text = pytesseract.image_to_string(image, lang="ukr+eng")
    except Exception as e:
        # Fallback to English only
        try:
            text = pytesseract.image_to_string(image, lang="eng")
        except Exception:
            raise RuntimeError(f"Tesseract OCR failed: {e}")
            
    return text


def _normalize_gemini_model_name(model):
    value = str(model or "").strip()
    if not value:
        return ""
    if value.startswith("models/"):
        value = value[len("models/"):]
    if ":" in value:
        value = value.split(":", 1)[0]
    return value.strip("/")


def _candidate_gemini_ocr_models():
    configured = []
    for env_name in ("GEMINI_OCR_MODEL", "GEMINI_MODEL"):
        raw_value = os.environ.get(env_name, "")
        configured.extend(part.strip() for part in raw_value.split(",") if part.strip())

    candidates = []
    for model in configured + list(DEFAULT_GEMINI_OCR_MODELS):
        normalized = _normalize_gemini_model_name(model)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def _extract_gemini_error_message(response):
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message")
        if message:
            return message
    except Exception:
        pass
    return (getattr(response, "text", "") or "").strip()[:300]


def _parse_gemini_ocr_response(response):
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    if not parts:
        return ""
    return parts[0].get("text", "")


def _model_supports_generate_content(model):
    supported = (
        model.get("supportedGenerationMethods")
        or model.get("supported_actions")
        or model.get("supportedActions")
        or []
    )
    return "generateContent" in supported


def _discover_gemini_ocr_model(api_key):
    url = f"{GEMINI_API_BASE_URL}/v1beta/models"
    try:
        response = requests.get(url, params={"key": api_key, "pageSize": 1000}, timeout=15)
        if response.status_code != 200:
            print(f"[OCR] Gemini model discovery failed with HTTP {response.status_code}: {_extract_gemini_error_message(response)}")
            return ""
        models = response.json().get("models", [])
    except Exception as e:
        print(f"[OCR] Gemini model discovery request failed: {e}")
        return ""

    candidates = [
        _normalize_gemini_model_name(model.get("name") or model.get("baseModelId"))
        for model in models
        if _model_supports_generate_content(model)
    ]
    candidates = [model for model in candidates if model]
    flash_candidates = [model for model in candidates if "flash" in model]
    if flash_candidates:
        return flash_candidates[0]
    return candidates[0] if candidates else ""


def _run_gemini_ocr_request(api_key, model, payload):
    url = f"{GEMINI_API_BASE_URL}/v1beta/models/{model}:generateContent"
    return requests.post(
        url,
        params={"key": api_key},
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=20,
    )


def run_gemini_vision_ocr(image_bytes):
    """
    Attempts to run Gemini Vision OCR on the image bytes.
    
    Returns:
        str: Extracted text.
    """
    global _GEMINI_OCR_MODEL_CACHE

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[OCR] Gemini fallback skipped: GEMINI_API_KEY is not set.")
        return ""
    
    # Encode image bytes to base64
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Extract all visible text/words from this video thumbnail image. Return ONLY the words separated by a single space, nothing else. If there is no text, return empty."
                    },
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": img_b64
                        }
                    }
                ]
            }
        ]
    }
    
    models = []
    if _GEMINI_OCR_MODEL_CACHE:
        models.append(_GEMINI_OCR_MODEL_CACHE)
    for model in _candidate_gemini_ocr_models():
        if model not in models:
            models.append(model)

    last_not_found = False
    for model in models:
        try:
            response = _run_gemini_ocr_request(api_key, model, payload)
        except Exception as e:
            print(f"[OCR] Gemini Vision API request failed for {model}: {e}")
            continue

        if response.status_code == 200:
            try:
                _GEMINI_OCR_MODEL_CACHE = model
                return _parse_gemini_ocr_response(response)
            except Exception:
                print("[OCR] Failed to parse Gemini response.")
                return ""

        message = _extract_gemini_error_message(response)
        print(f"[OCR] Gemini API returned error {response.status_code} for {model}: {message}")
        if response.status_code in {401, 403, 429}:
            return ""
        if response.status_code == 404:
            last_not_found = True

    if last_not_found:
        discovered = _discover_gemini_ocr_model(api_key)
        if discovered and discovered not in models:
            try:
                response = _run_gemini_ocr_request(api_key, discovered, payload)
                if response.status_code == 200:
                    _GEMINI_OCR_MODEL_CACHE = discovered
                    return _parse_gemini_ocr_response(response)
                message = _extract_gemini_error_message(response)
                print(f"[OCR] Gemini API returned error {response.status_code} for discovered model {discovered}: {message}")
            except Exception as e:
                print(f"[OCR] Gemini Vision API request failed for discovered model {discovered}: {e}")
        
    return ""


def clean_text(text):
    """
    Cleans up whitespace and normalizes text extracted from OCR.
    """
    if not text:
        return ""
    # Replace newlines, tabs, multiple spaces with a single space
    words = text.split()
    return " ".join(words)


def extract_thumbnail_text(video_id):
    """
    Main entry point: downloads the thumbnail and runs local OCR with Gemini fallback.
    
    Returns:
        str: Cleaned extracted text, or empty string.
    """
    print(f"[OCR] Running thumbnail text extraction for video: {video_id}")
    image_bytes = download_thumbnail(video_id)
    if not image_bytes:
        print(f"[OCR] Could not download thumbnail for video: {video_id}")
        return ""
        
    # 1. Try local Tesseract OCR
    try:
        raw_text = run_local_ocr(image_bytes)
        text = clean_text(raw_text)
        if text.strip():
            print(f"[OCR] Local Tesseract OCR successfully extracted: '{text}'")
            return text
        else:
            print("[OCR] Local Tesseract OCR returned empty text. Trying Gemini fallback...")
    except Exception as e:
        print(f"[OCR] Local Tesseract OCR failed or not configured: {e}. Trying Gemini fallback...")
        
    # 2. Try Gemini Vision fallback
    raw_text = run_gemini_vision_ocr(image_bytes)
    text = clean_text(raw_text)
    if text.strip():
        print(f"[OCR] Gemini Vision API successfully extracted: '{text}'")
        return text
        
    print("[OCR] Both OCR methods returned no text.")
    return ""

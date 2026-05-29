"""
Thumbnail OCR Helper for YouTube News Automation.
Extracts text from video thumbnails using local Tesseract OCR, with a fallback
to Gemini 1.5 Flash Vision API when local OCR is unavailable or fails.
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
from news_scraper.utils import load_env
load_env()


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


def run_gemini_vision_ocr(image_bytes):
    """
    Attempts to run Gemini 1.5 Flash Vision OCR on the image bytes.
    
    Returns:
        str: Extracted text.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[OCR] Gemini fallback skipped: GEMINI_API_KEY is not set.")
        return ""
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
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
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            print(f"[OCR] Failed to parse Gemini response: {response.text}")
        else:
            print(f"[OCR] Gemini API returned error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[OCR] Gemini Vision API request failed: {e}")
        
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

from typing import Union, Optional
import os
import numpy as np
import cv2 as cv
import fitz  # PyMuPDF
from paddleocr import PaddleOCR

# Cache OCR instances per language to avoid re-initialization overhead
_OCR_CACHE: dict[str, PaddleOCR] = {}


def get_ocr(lang: str = "en") -> PaddleOCR:
    """Return cached PaddleOCR instance with working flags for predict-only flow."""
    if lang not in _OCR_CACHE:
        _OCR_CACHE[lang] = PaddleOCR(
            lang=lang,
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_angle_cls=True,
        )
    return _OCR_CACHE[lang]


def preprocess(IMG: Union[str, np.ndarray]) -> np.ndarray:
    """Grayscale, denoise, upscale min side to 500px, convert back to BGR."""
    if isinstance(IMG, np.ndarray):
        img = IMG.copy()
    else:
        img = cv.imread(IMG)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {IMG}")

    if img.ndim == 3:
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    gray = cv.fastNlMeansDenoising(gray, h=10)
    # Slight contrast boost for printed PDFs
    try:
        gray = cv.equalizeHist(gray)
    except Exception:
        pass

    h, w = gray.shape
    if min(h, w) < 500:
        scale = 500 / min(h, w)
        gray = cv.resize(gray, None, fx=scale, fy=scale, interpolation=cv.INTER_CUBIC)

    bgr = cv.cvtColor(gray, cv.COLOR_GRAY2BGR)
    return bgr


def _predict_texts(img_bgr: np.ndarray, lang: str = "en") -> str:
    """Use PaddleOCR.ocr (stable API) and extract recognized texts into a single string.

    Handles both single-image and batched nested result shapes returned by PaddleOCR.
    """
    ocr = get_ocr(lang)
    processed = preprocess(img_bgr)

    try:
        results = ocr.ocr(processed, cls=True)
    except Exception:
        results = None

    if not results:
        return ""

    texts: list[str] = []

    def parse_lines(lines):
        for item in lines:
            try:
                # Typical structure: [box, (text, score)]
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    second = item[1]
                    if isinstance(second, (list, tuple)) and len(second) >= 1:
                        t = second[0]
                        if isinstance(t, str) and t.strip():
                            texts.append(t.strip())
                    elif isinstance(second, str) and second.strip():
                        texts.append(second.strip())
            except Exception:
                continue

    # Results can be [[...]] or [...]
    if isinstance(results, list) and len(results) == 1 and isinstance(results[0], list):
        parse_lines(results[0])
    elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], list) and (len(results[0]) > 0 and isinstance(results[0][0], (list, tuple))):
        # batched
        for batch in results:
            parse_lines(batch)
    else:
        parse_lines(results)

    return "\n".join(texts)


def image_bytes_to_bgr(data: bytes) -> Optional[np.ndarray]:
    """Decode image bytes to BGR ndarray. Returns None if decode fails."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv.imdecode(arr, cv.IMREAD_COLOR)
    return img if img is not None else None


def extract_from_pdf_bytes(data: bytes, lang: str = "en", zoom: float = 6.0) -> str:
    """Rasterize PDF bytes with PyMuPDF and run _predict_texts per page."""
    doc = fitz.open(stream=data, filetype="pdf")
    all_text: list[str] = []
    try:
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(matrix=mat)
            channels = pix.n
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, channels)

            if channels == 4:
                img_bgr = cv.cvtColor(arr, cv.COLOR_RGBA2BGR)
            elif channels == 3:
                img_bgr = cv.cvtColor(arr, cv.COLOR_RGB2BGR)
            else:
                img_bgr = cv.cvtColor(arr, cv.COLOR_GRAY2BGR)

            page_text = _predict_texts(img_bgr, lang=lang)
            all_text.append(f"--- PAGE {i} ---\n{page_text}")
    finally:
        doc.close()

    return "\n\n".join(all_text)


def process_input(inp: Union[str, bytes], lang: str = "en") -> str:
    """
    Public function used by routes:
    - bytes: try image decode; if fails, assume PDF
    - str path: branch by extension
    Returns extracted text (may be empty string).
    """
    if isinstance(inp, bytes):
        img_bgr = image_bytes_to_bgr(inp)
        if img_bgr is not None:
            return _predict_texts(img_bgr, lang=lang)
        return extract_from_pdf_bytes(inp, lang=lang)

    ext = os.path.splitext(inp)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
        # preprocess inside _predict_texts if path -> read here to ndarray for consistency
        img = cv.imread(inp)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {inp}")
        return _predict_texts(img, lang=lang)
    elif ext == ".pdf":
        with open(inp, "rb") as f:
            data = f.read()
        return extract_from_pdf_bytes(data, lang=lang)
    else:
        raise ValueError("Unsupported file type: " + ext)

# Do not execute OCR at import time; keep this module import-safe for FastAPI.


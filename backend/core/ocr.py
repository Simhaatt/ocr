try:
    from paddleocr import PaddleOCR
except Exception:
    PaddleOCR = None
import os
import cv2 as cv
import numpy as np
import fitz
import cv2 as cv
import numpy as np
from typing import Union
import re

def preprocess(IMG: Union[str, np.ndarray]) -> np.ndarray:
    if isinstance(IMG, np.ndarray):
        img = IMG.copy()
    else:
        img = cv.imread(IMG)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {IMG}")

    # --- process on image already in memory ---
    # convert to gray, denoise, optional upscale, convert back to BGR
    if img.ndim == 3:
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    gray = cv.fastNlMeansDenoising(gray, h=10)
    # 3. If image is too small, upscale it (helps recognition a LOT)
    h, w = gray.shape
    if min(h, w) < 500:
        scale = 500 / min(h, w)
        gray = cv.resize(gray, None, fx=scale, fy=scale, interpolation=cv.INTER_CUBIC)

    # 4. Convert back to BGR (PaddleOCR expects 3 channels)
    bgr = cv.cvtColor(gray, cv.COLOR_GRAY2BGR)

    return bgr


ocr = None

image_path = r"C:\Users\hp\Downloads\Screenshot 2025-12-02 225712.png" # Example path; used for smoke test
# ocr.predict() returns a list of OCRResult objects.
# For a single image, this list usually contains one OCRResult object.
# This OCRResult object then contains the actual recognition data.

#preprocess:


def _get_ocr():
    global ocr
    if ocr is None:
        if PaddleOCR is None:
            raise ImportError("PaddleOCR runtime not available. Please install paddlepaddle and paddleocr.")
        ocr = PaddleOCR(lang='hi', use_textline_orientation=False, use_doc_orientation_classify=False, use_doc_unwarping=False)
    return ocr

def paddleocr(preprocessed_image: Union[str, np.ndarray]) -> str:
    """Run PaddleOCR on an image (path or ndarray) and return concatenated text.

    Uses the stable `ocr()` API from PaddleOCR. Handles typical return formats.
    """
    img = preprocess(preprocessed_image)
    predictor = _get_ocr()

    # Call the standard OCR API. It returns a nested list structure.
    results = predictor.ocr(img, det=True, rec=True, cls=False)

    extracted_texts = []
    if not results:
        print("OCR returned no results.")
        return ""

    # For single image input, results is often a list with one inner list of lines
    # Normalize to a flat list of line entries
    if len(results) == 1 and isinstance(results[0], list):
        lines = results[0]
    else:
        lines = results

    for item in lines:
        # Expected shape per line: [box, (text, score)]
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            rec_part = item[1]
            if isinstance(rec_part, (list, tuple)) and rec_part:
                text = rec_part[0]
                if isinstance(text, str) and text.strip():
                    extracted_texts.append(text.strip())

    return "\n".join(extracted_texts)

def process_input(inp):
    ext = os.path.splitext(inp)[1].lower()
    
    if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
        return paddleocr(inp)
    elif ext == ".pdf":
        doc = fitz.open(inp)
        all_text = []
        for i, page in enumerate(doc, 1):
            print(f"PROCESSING PAGE {i}")
            print('='*50)
            
            mat = fitz.Matrix(4.0,4.0)
            pix = page.get_pixmap(matrix=mat)
            
            channels = pix.n
            arr = np.frombuffer(pix.samples, dtype=np.uint8)
            arr = arr.reshape(pix.height, pix.width, channels)

            if channels == 4:
                img_bgr = cv.cvtColor(arr, cv.COLOR_RGBA2BGR)
            elif channels == 3:
                img_bgr = cv.cvtColor(arr, cv.COLOR_RGB2BGR)
            else:
                img_bgr = cv.cvtColor(arr, cv.COLOR_GRAY2BGR)

            page_text = paddleocr(img_bgr)   # pass ndarray directly
            all_text.append(f"--- PAGE {i} ---\n{page_text}")
        doc.close()
        return "\n\n".join(all_text)
    else:
        raise ValueError("Unsupported file type: " + ext)
        
if __name__ == "__main__":
    print(f"Performing OCR on: {image_path} using ocr.predict() API")
    try:
        print(process_input(image_path))
    except Exception as e:
        print("OCR run failed:", e)

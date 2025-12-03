from paddleocr import PaddleOCR
import os
import cv2 as cv
import numpy as np
import fitz
from typing import Union
import pytesseract


def preprocess(IMG: Union[str, np.ndarray]) -> np.ndarray:
    """Proven preprocessing pipeline: grayscale, denoise, optional upscale, to BGR."""
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
    h, w = gray.shape
    if min(h, w) < 500:
        scale = 500 / min(h, w)
        gray = cv.resize(gray, None, fx=scale, fy=scale, interpolation=cv.INTER_CUBIC)

    bgr = cv.cvtColor(gray, cv.COLOR_GRAY2BGR)
    return bgr


# Default to English; switch to Hindi by changing lang='hi' if needed
ocr = PaddleOCR(lang='en', use_textline_orientation=False, use_doc_orientation_classify=False, use_doc_unwarping=False)


def paddleocr(preprocessed_image: Union[str, np.ndarray]) -> str:
    """Use predict-based logic; fallback to ocr.ocr, then pytesseract if needed."""
    img = preprocess(preprocessed_image)

    texts = []
    try:
        prediction_results = ocr.predict(img)
    except AttributeError:
        prediction_results = None

    if prediction_results:
        for i, res_obj in enumerate(prediction_results):
            item_text = None
            if hasattr(res_obj, 'json') and isinstance(res_obj.json, dict):
                json_data = res_obj.json
                if 'res' in json_data and isinstance(json_data['res'], dict):
                    res_content = json_data['res']
                    if 'rec_texts' in res_content and isinstance(res_content['rec_texts'], list):
                        meaningful = [t for t in res_content['rec_texts'] if isinstance(t, str) and t.strip()]
                        if meaningful:
                            item_text = "\n".join(meaningful)
            if item_text:
                texts.append(item_text)
    else:
        # Fallback to standard API
        try:
            results = ocr.ocr(img, cls=True)
            for line in results or []:
                try:
                    t = line[1][0]
                    if isinstance(t, str) and t.strip():
                        texts.append(t.strip())
                except Exception:
                    continue
        except Exception:
            pass

    if texts:
        return "\n---\n".join(texts)

    # Final fallback: Tesseract OCR
    try:
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        words = []
        for i in range(len(data.get('text', []))):
            w = data['text'][i]
            conf = float(data.get('conf', [0]*len(data['text']))[i])
            if isinstance(w, str) and w.strip() and conf > 60:
                words.append(w.strip())
        return " ".join(words)
    except Exception:
        return ""


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

            mat = fitz.Matrix(4.0, 4.0)
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

            page_text = paddleocr(img_bgr)
            all_text.append(f"--- PAGE {i} ---\n{page_text}")
        doc.close()
        return "\n\n".join(all_text)
    else:
        raise ValueError("Unsupported file type: " + ext)


if __name__ == "__main__":
    try:
        print(process_input(image_path))
    except Exception as e:
        print("OCR run failed:", e)


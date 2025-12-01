from paddleocr import PaddleOCR
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


ocr = PaddleOCR(lang='hi', use_textline_orientation=False, use_doc_orientation_classify=False, use_doc_unwarping=False)

image_path = r"C:\Users\rohit\Downloads\printed_hindi.jpg" # Path to the image file for OCR
# Directory to save visualized OCR results from the predict API


print(f"Performing OCR on: {image_path} using ocr.predict() API")
# ocr.predict() returns a list of OCRResult objects.
# For a single image, this list usually contains one OCRResult object.
# This OCRResult object then contains the actual recognition data.

#preprocess:


def paddleocr(preprocessed_image: Union[str, np.ndarray]) -> str:
    img = preprocess(preprocessed_image)
    prediction_results = ocr.predict(img)

    if prediction_results:
        print("\nOCR Prediction Results:")
        all_extracted_texts = []      
        
        # Iterate through the list of OCRResult objects
        # (typically one item for a single image)
        for i, res_obj in enumerate(prediction_results):
            # Text extraction
            item_text = None
            # Text is found within res_obj.json['res']['rec_texts']
            if hasattr(res_obj, 'json') and isinstance(res_obj.json, dict):
                json_data = res_obj.json
                if 'res' in json_data and isinstance(json_data['res'], dict):
                    res_content = json_data['res']
                    if 'rec_texts' in res_content and isinstance(res_content['rec_texts'], list):
                        # Filter out empty strings and join the meaningful recognized texts
                        meaningful_texts = [text for text in res_content['rec_texts'] if isinstance(text, str) and text.strip()]
                        if meaningful_texts:
                            item_text = "\n".join(meaningful_texts)
                    
            
            if item_text:
                all_extracted_texts.append(item_text)
            else:
                # If text is not extracted, print a warning and the raw result object for debugging
                print(f"Warning: Could not extract text for result item {i+1}.")
                if hasattr(res_obj, 'print'): # Print the raw result object if text extraction failed
                    #print(f"--- Raw result object {i+1} for debugging ---")
                    res_obj.print()
                    #print(f"--- End of raw result object {i+1} ---")

        if all_extracted_texts:
            return "\n---\n".join(all_extracted_texts)
        else:
            return ""


    else: # This corresponds to `if prediction_results:`
        print("OCR (ocr.predict() API) returned no results or an empty result (initial check).")

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
        
print(process_input(image_path))

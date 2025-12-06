from typing import Union, Optional, List
import os
import numpy as np
import cv2 as cv
import re
import fitz  # PyMuPDF
from paddleocr import PaddleOCR
try:
    from rapidfuzz import fuzz, process as fuzz_process  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False

# Cache OCR instances per language to avoid re-initialization overhead
_OCR_CACHE: dict[str, PaddleOCR] = {}


def get_ocr(lang: str = "en") -> PaddleOCR:
    """Return cached PaddleOCR instance with working flags for predict-only flow."""
    if lang not in _OCR_CACHE:
        # Prefer newer textline orientation and avoid passing both flags together
        try:
            _OCR_CACHE[lang] = PaddleOCR(
                lang=lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
            )
        except TypeError:
            # Older versions: fall back to angle classifier
            _OCR_CACHE[lang] = PaddleOCR(
                lang=lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_angle_cls=True,
            )
    return _OCR_CACHE[lang]


def preprocess(IMG: Union[str, np.ndarray]) -> np.ndarray:
    """Grayscale, denoise, local-contrast, size normalize, sharpen, to BGR.

    - Ensures smallest side >= 500px for readability
    - Caps largest side to ~3800px to avoid Paddle's internal downscale
    - Uses CLAHE + mild unsharp mask for printed text
    """
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

    # Local contrast enhancement (more robust than global equalizeHist)
    try:
        clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    except Exception:
        pass

    h, w = gray.shape
    # Upscale if too small
    if min(h, w) < 500:
        scale = 500 / min(h, w)
        gray = cv.resize(gray, None, fx=scale, fy=scale, interpolation=cv.INTER_CUBIC)
        h, w = gray.shape

    # Downscale if too large (Paddle caps to ~4000; avoid double scaling)
    MAX_SIDE = 3800
    if max(h, w) > MAX_SIDE:
        scale = MAX_SIDE / max(h, w)
        gray = cv.resize(gray, None, fx=scale, fy=scale, interpolation=cv.INTER_AREA)
        h, w = gray.shape

    # Mild unsharp mask to crisp printed edges
    try:
        blur = cv.GaussianBlur(gray, (0, 0), sigmaX=1.0)
        gray = cv.addWeighted(gray, 1.5, blur, -0.5, 0)
    except Exception:
        pass

    bgr = cv.cvtColor(gray, cv.COLOR_GRAY2BGR)
    return bgr


def _predict_texts(img_bgr: np.ndarray, lang: str = "en") -> str:
    """Use PaddleOCR.ocr (stable API) and extract recognized texts into a single string.

    Handles both single-image and batched nested result shapes returned by PaddleOCR.
    """
    ocr = get_ocr(lang)
    processed = preprocess(img_bgr)

    try:
        results = ocr.ocr(processed, cls=False)
    except Exception:
        results = None

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
    if results:
        if isinstance(results, list) and len(results) == 1 and isinstance(results[0], list):
            parse_lines(results[0])
        elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], list) and (len(results[0]) > 0 and isinstance(results[0][0], (list, tuple))):
            # batched
            for batch in results:
                parse_lines(batch)
        else:
            parse_lines(results)

    # If no text parsed, try PaddleOCR.predict() fallback (newer API)
    if not texts:
        try:
            preds = ocr.predict(processed)
        except Exception:
            preds = None
        if preds:
            for res_obj in preds:
                try:
                    if hasattr(res_obj, 'json') and isinstance(res_obj.json, dict):
                        jd = res_obj.json
                        if 'res' in jd and isinstance(jd['res'], dict):
                            rec = jd['res'].get('rec_texts')
                            if isinstance(rec, list):
                                for t in rec:
                                    if isinstance(t, str) and t.strip():
                                        texts.append(t.strip())
                except Exception:
                    continue

    # Normalize common field labels/values and remove basic noise
    def _normalize_text_lines(lines: List[str]) -> List[str]:
        # Pre-normalize punctuation
        def norm_punct(s: str) -> str:
            return s.replace('—', '-').replace('–', '-').replace('：', ':')

        # Identify lines that start new labels (after rough normalization)
        LABEL_STARTS = re.compile(
            r"^\s*(first\s*name|middle\s*name|last\s*name|surname|family\s*name|gender|sex|address|age)\b",
            re.IGNORECASE,
        )

        # Phrase-level fuzzy label detection (very tolerant to misspellings)
        PHRASES = {
            "First Name": ["first name", "given name", "forename"],
            "Middle Name": ["middle name"],
            "Last Name": ["last name", "surname", "family name"],
            "Gender": ["gender", "sex"],
            "Address": ["address", "residential address", "permanent address", "current address", "correspondence address"],
            "Age": ["age"],
        }
        PHRASE_LIST = [(canon, p) for canon, lst in PHRASES.items() for p in lst]

        def best_label(line: str):
            text = line.lower()
            best = (None, None, 0.0)
            for canon, phrase in PHRASE_LIST:
                if _HAS_RAPIDFUZZ:
                    score = fuzz.token_set_ratio(phrase, text)
                else:
                    import difflib
                    score = difflib.SequenceMatcher(None, phrase, text).ratio() * 100
                if score > best[2]:
                    best = (canon, phrase, score)
            return best

        out: List[str] = []
        seen = set()
        i = 0
        N = len(lines)

        def add(label: str, value: str) -> None:
            v = value.strip().strip('-:').strip()
            if not v:
                return
            norm = f"{label}: {v}"
            if norm not in seen:
                out.append(norm)
                seen.add(norm)

        while i < N:
            raw0 = lines[i]
            if not isinstance(raw0, str):
                i += 1; continue
            raw = raw0.strip()
            if not raw:
                i += 1; continue
            ln = norm_punct(raw)
            ln_low = ln.lower()

            # 1) Fuzzy phrase detection first
            canon, phrase, score = best_label(ln_low)
            if canon and score >= 85:
                # Extract inline value
                val = ""
                msep = re.search(r":|-", ln)
                if msep:
                    val = ln[msep.end():].strip()
                else:
                    if ln_low.startswith(phrase):
                        val = ln[len(ln) - len(ln_low) + len(phrase):].strip()
                # Fallback to next line if empty and next not a label
                if not val and (i + 1) < N:
                    nxt_raw = (lines[i + 1] or "").strip()
                    nxt_ln = norm_punct(nxt_raw)
                    nxt_low = nxt_ln.lower()
                    if nxt_low and not LABEL_STARTS.match(nxt_low):
                        val = nxt_raw
                        i += 1

                if canon == "Gender" and val:
                    vlow = val.lower()
                    if vlow in {"m", "male"}: val = "Male"
                    elif vlow in {"f", "female"}: val = "Female"
                if canon == "Age" and val:
                    d = re.search(r"\b(\d{1,3})\b", val)
                    if d: val = d.group(1)

                if val:
                    add(canon, val)
                    i += 1
                    continue

            # 2) Regex fallback for inline patterns
            m = re.match(r"^\s*(first\s*name|given\s*name|forename)\s*[:\-]?\s*(.+)$", ln_low, flags=re.IGNORECASE)
            if m:
                add("First Name", ln[m.start(2):].strip()); i += 1; continue
            m = re.match(r"^\s*(middle\s*name)\s*[:\-]?\s*(.+)$", ln_low, flags=re.IGNORECASE)
            if m:
                add("Middle Name", ln[m.start(2):].strip()); i += 1; continue
            m = re.match(r"^\s*(last\s*name|surname|family\s*name)\s*[:\-]?\s*(.+)$", ln_low, flags=re.IGNORECASE)
            if m:
                add("Last Name", ln[m.start(2):].strip()); i += 1; continue

            m = re.match(r"^\s*(gender|sex)\s*[:\-]?\s*(.+)$", ln_low, flags=re.IGNORECASE)
            if m:
                val = ln[m.start(2):].strip(); vlow = val.lower()
                if vlow in {"m", "male"}: val = "Male"
                elif vlow in {"f", "female"}: val = "Female"
                add("Gender", val); i += 1; continue

            m = re.match(r"^\s*(address|addr|residential\s*address|permanent\s*address|current\s*address|correspondence\s*address)\s*[:\-]?\s*(.+)$", ln_low, flags=re.IGNORECASE)
            if m:
                add("Address", ln[m.start(2):].strip()); i += 1; continue

            m = re.match(r"^\s*(age)\s*[:\-]?\s*(.+)$", ln_low, flags=re.IGNORECASE)
            if m:
                after = ln[m.start(2):]; d = re.search(r"\b(\d{1,3})\b", after)
                if d: add("Age", d.group(1)); i += 1; continue

            # 3) Keep other meaningful lines
            if re.search(r"[A-Za-z0-9]", raw) and len(raw) >= 3 and raw not in seen:
                out.append(raw); seen.add(raw)
            i += 1

        return out

    texts = _normalize_text_lines(texts)
    return "\n".join(texts)


def image_bytes_to_bgr(data: bytes) -> Optional[np.ndarray]:
    """Decode image bytes to BGR ndarray. Returns None if decode fails."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv.imdecode(arr, cv.IMREAD_COLOR)
    return img if img is not None else None


def extract_from_pdf_bytes(data: bytes, lang: str = "en", zoom: float = 6.0) -> str:
    """Rasterize PDF bytes with PyMuPDF and run _predict_texts per page.

    Dynamically caps the rendered page size to ~3800px on the longest side
    to avoid Paddle's internal resize and preserve effective resolution.
    """
    doc = fitz.open(stream=data, filetype="pdf")
    all_text: list[str] = []
    try:
        for i, page in enumerate(doc, 1):
            # Compute a zoom per-page to cap longest side ~3800px
            MAX_SIDE = 3800.0
            page_w, page_h = float(page.rect.width), float(page.rect.height)
            page_max = max(page_w, page_h)
            # base zoom request vs cap zoom to fit MAX_SIDE
            cap_zoom = MAX_SIDE / page_max if page_max > 0 else zoom
            use_zoom = min(zoom, cap_zoom)
            mat = fitz.Matrix(use_zoom, use_zoom)
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

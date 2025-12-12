# backend/a3_utils.py
# Utilities for A3: normalization + fuzzy matching + aggregation
#
# Usage:
#   pip install rapidfuzz
#   python backend/a3_utils.py
#
# This file contains:
# - unicode / punctuation / abbreviation normalization
# - normalize for phone/date/id
# - name/address/phone/dob/gender scoring using rapidfuzz
# - aggregate_confidence() to compute overall score and per-field scores

import re
import unicodedata
from datetime import datetime
from typing import Dict, Tuple, Any
from rapidfuzz import fuzz
try:
    # Unidecode provides transliteration (Hindi -> ASCII) without dropping meaning.
    from unidecode import unidecode
except ImportError:  # graceful fallback if not installed yet
    def unidecode(x: str) -> str:
        return x

# --- small mappings used in normalization ---
ABBR = {
    # thoroughfares
    # with and without trailing dots
    "st": "street", "st.": "street",
    "rd": "road", "rd.": "road",
    "ave": "avenue", "av": "avenue", "ave.": "avenue", "av.": "avenue",
    "ln": "lane", "ln.": "lane",
    "ct": "court", "ct.": "court",
    "cir": "circle", "cir.": "circle",
    "dr": "drive", "dr.": "drive",
    "pl": "place", "pl.": "place",
    "pkwy": "parkway", "pkwy.": "parkway",
    "hwy": "highway", "hwy.": "highway",
    # buildings / units
    "bldg": "building", "blk": "block", "apt": "apartment", "flat": "flat", "ste": "suite",
    "fl": "floor", "flr": "floor", "twr": "tower", "ph": "phase", "sec": "sector",
    # numbers / house
    "no": "number", "hno": "house number",
    # misc local (common in IN addresses)
    "po": "post office", "ps": "police station", "stn": "station", "dist": "district", "tal": "taluk", "teh": "tehsil", "nr": "near",
    # Hindi (native script) common tokens -> English expansions
    "रोड": "road", "मार्ग": "road", "सड़क": "road", "सडक": "road", "सड़क": "road", "गली": "lane",
    "मकान": "house", "भवन": "building", "टावर": "tower", "अपार्टमेंट": "apartment", "फ़्लैट": "flat", "फ्लैट": "flat",
    "नजदीक": "near", "नज़दीक": "near", "पास": "near",
    # Hindi transliterations (post-unidecode) -> English expansions
    "rod": "road", "marg": "road", "sadak": "road", "gali": "lane", "makan": "house", "bhavan": "building",
    "tavar": "tower", "apartment": "apartment", "phlait": "flat", "flat": "flat", "najdik": "near", "nazdik": "near", "paas": "near",
}
STOPWORDS = {
    # address glue words (kept conservative to avoid harming names)
    "near", "nearby", "opposite", "opp", "behind", "beside", "by", "at", "the", "in",
    "next", "to", "of", "and",
    # frequent non-informative tokens in addresses
    "country", "usa", "india",
    # Hindi stopwords (common particles / connectors)
    "के", "और", "में", "का", "की", "पर", "को", "से", "तक",
}
COMMON_DATE_FORMATS = [
    "%d-%m-%Y", "%d-%m-%y", "%d/%m/%Y", "%d/%m/%y",
    "%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%d %B %Y",
    "%b %d, %Y", "%B %d, %Y"
]

# -----------------------------
# Normalization functions
# -----------------------------
def normalize_unicode(s: str) -> str:
    """Normalize & transliterate unicode.

    Steps:
    - NFKD decomposition
    - Transliterate (e.g. Hindi देवनागरी -> Latin) via unidecode when available
    - Remove control characters
    This retains semantic content of Hindi instead of dropping characters.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = unidecode(s)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")
    return s

def normalize_digits(s: str) -> str:
    """Return digits only (useful for phone / id)."""
    if not s:
        return ""
    # Map Devanagari digits to ASCII before stripping
    dev_map = str.maketrans({
        '०': '0','१': '1','२': '2','३': '3','४': '4','५': '5','६': '6','७': '7','८': '8','९': '9'
    })
    s2 = str(s).translate(dev_map)
    return re.sub(r"\D", "", s2)

def normalize_date(s: str) -> str:
    """
    Try to parse common date formats and return ISO 'YYYY-MM-DD'.
    Return empty string if unable to parse.
    """
    if not s:
        return ""
    s0 = str(s).strip().replace(".", "-").replace("/", "-")
    s0 = re.sub(r"[^\w\s\-:,]", "", s0)
    for fmt in COMMON_DATE_FORMATS:
        try:
            return datetime.strptime(s0, fmt).date().isoformat()
        except Exception:
            pass
    # heuristic: numeric parts
    parts = re.split(r"[-\s:]", s0)
    digits = [p for p in parts if p.isdigit()]
    if len(digits) == 3:
        d1, d2, d3 = digits
        for cand in [(d3, d2, d1), (d1, d2, d3)]:  # try dd-mm-yyyy, then yyyy-mm-dd
            try:
                return datetime(int(cand[0]), int(cand[1]), int(cand[2])).date().isoformat()
            except Exception:
                pass
    return ""

def expand_abbreviations(s: str) -> str:
    """Replace common abbreviations / Hindi tokens in tokens (st -> street, मार्ग -> road)."""
    if not s:
        return ""
    words = s.split()
    out = []
    for w in words:
        # preserve tokens like "st." to map via ABBR
        w_clean = re.sub(r"^([\w]+)[^\w]*$", r"\1", w.lower())
        out.append(ABBR.get(w_clean, w_clean))
    return " ".join(out)

def remove_stopwords(s: str) -> str:
    """Remove noisy small words often present in addresses."""
    if not s:
        return ""
    return " ".join(w for w in s.split() if w not in STOPWORDS)

def normalize_full(s: str, field_type: str = "generic") -> str:
    """
    Full normalization pipeline.
    - field_type: "generic" (names/addresses), "phone", "date", "id"
    """
    if not s:
        return ""
    s = normalize_unicode(s)
    if field_type in ("phone", "id"):
        return normalize_digits(s)
    if field_type == "date":
        return normalize_date(s)
    # generic text (name / address)
    s = s.lower().strip()
    # replace common punctuation with space
    s = re.sub(r"[.,;:!?\-()\"'\/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = expand_abbreviations(s)
    s = remove_stopwords(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# -----------------------------
# Scoring / fuzzy functions
# -----------------------------
FIELD_WEIGHTS_DEFAULT = {"name":0.35, "dob":0.30, "phone":0.15, "address":0.15, "gender":0.05}

def name_score(a: str, b: str) -> float:
    """Return robust fuzzy score for names (0..1)."""
    a_n = normalize_full(a, "generic")
    b_n = normalize_full(b, "generic")
    if not a_n or not b_n:
        return 0.0
    s1 = fuzz.ratio(a_n, b_n)
    s2 = fuzz.token_sort_ratio(a_n, b_n)
    s3 = fuzz.partial_ratio(a_n, b_n)
    best = max(s1, s2, s3) / 100.0
    toks_a = a_n.split()
    toks_b = b_n.split()
    # Boost for token permutations (order variance)
    if set(toks_a) == set(toks_b) and len(toks_a) == len(toks_b):
        best = max(best, 0.95)
    # Mild boost for prefix truncation or middle initials
    def strip_dot(x: str) -> str:
        return x.replace('.', '')
    if len(toks_a) == len(toks_b) - 1:
        if all(strip_dot(toks_a[i]) == strip_dot(toks_b[i]) for i in range(len(toks_a)-1)) and toks_b[-1].startswith(strip_dot(toks_a[-1])):
            best = max(best, 0.87)
    # Abbreviation case same length: allow middle/last initial with dot
    if len(toks_a) == len(toks_b) == 2:
        if strip_dot(toks_a[0]) == strip_dot(toks_b[0]) and (strip_dot(toks_a[1]).startswith(strip_dot(toks_b[1])) or strip_dot(toks_b[1]).startswith(strip_dot(toks_a[1]))):
            best = max(best, 0.87)
    # Three-token case: tolerate middle initial
    if len(toks_a) == len(toks_b) == 3:
        if strip_dot(toks_a[0]) == strip_dot(toks_b[0]) and strip_dot(toks_a[-1]) == strip_dot(toks_b[-1]):
            mid_a = strip_dot(toks_a[1])
            mid_b = strip_dot(toks_b[1])
            if mid_a[:1] == mid_b[:1]:
                best = max(best, 0.9)
    # Specific reversal boost for two-token names
    if len(toks_a) == len(toks_b) == 2 and toks_a[0] == toks_b[1] and toks_a[1] == toks_b[0]:
        best = max(best, 0.95)
    return best

def address_score(a: str, b: str) -> float:
    """Use multiple fuzzy strategies + token overlap bonuses (0..1)."""
    an = normalize_full(a, "generic")
    bn = normalize_full(b, "generic")
    if not an or not bn:
        return 0.0
    s_partial = fuzz.partial_ratio(an, bn) / 100.0
    s_token = fuzz.token_sort_ratio(an, bn) / 100.0
    s_set = fuzz.token_set_ratio(an, bn) / 100.0
    s_w = getattr(fuzz, "WRatio", lambda x, y: 0)(an, bn) / 100.0
    s_raw = max(s_token, s_set, s_w, s_partial)

    # Bonus for matching numeric tokens like house/flat numbers
    nums_a = set(re.findall(r"\b\d+\b", an))
    nums_b = set(re.findall(r"\b\d+\b", bn))
    bonus_num = 0.0
    if nums_a and nums_b:
        inter = len(nums_a & nums_b)
        if inter > 0:
            bonus_num = min(0.05, 0.02 * inter)

    # Small bonus for general token overlap (Jaccard)
    toks_a = set(an.split())
    toks_b = set(bn.split())
    union = len(toks_a | toks_b) or 1
    inter = len(toks_a & toks_b)
    jacc = inter / union
    bonus_jacc = min(0.05, 0.05 * jacc)

    # Penalize partial-only matches: require coverage of smaller side
    # Coverage based on the larger address to penalize missing key tokens
    coverage = inter / max(1, max(len(toks_a), len(toks_b)))
    # If the fuzzy score is already very high, treat it as near-full match (e.g., minor spacing/punctuation)
    if s_raw >= 0.9:
        coverage = 1.0
    coverage = max(0.5, coverage)  # avoid over-penalizing tiny differences like extra spaces
    s_raw_adjusted = s_raw * coverage

    total_bonus = min(0.08, bonus_num + bonus_jacc)
    return min(1.0, s_raw_adjusted + total_bonus)

def phone_score(a: str, b: str) -> float:
    """Compare phones robustly with country codes/trunk prefixes.

    Heuristic approach:
    - Normalize to digits.
    - Compare NSN (last 10 digits) when available; if NSNs match => 1.0.
    - Otherwise, compute per-digit similarity on the NSN portion with a mild penalty.
    """
    da = normalize_full(a, "phone")
    db = normalize_full(b, "phone")
    if not da or not db:
        return 0.0
    if da == db:
        return 1.0

    # Helper: split into (country_code, nsn) where nsn ~ last 10 digits when available
    def split_phone(d: str) -> Tuple[str, str]:
        if not d:
            return "", ""
        if len(d) >= 10:
            nsn = d[-10:]
            cc = d[:-10].lstrip('0')
        else:
            nsn = d
            cc = ""
        return cc, nsn

    cc_a, nsn_a = split_phone(da)
    cc_b, nsn_b = split_phone(db)

    if nsn_a and nsn_b and nsn_a == nsn_b:
        return 1.0

    # Partial suffix matches (area code differences). Give partial credit.
    for k, val in ((9, 0.95), (8, 0.9), (7, 0.85), (6, 0.80)):
        if len(da) >= k and len(db) >= k and da[-k:] == db[-k:]:
            return val

    # Fall back: digit similarity on NSN (or full digits if short)
    x = nsn_a or da
    y = nsn_b or db
    ld = max(len(x), len(y))
    if ld == 0:
        return 0.0
    diff = sum(1 for p, q in zip(x.zfill(ld), y.zfill(ld)) if p != q) + abs(len(x) - len(y))
    # minimum denominator to avoid harsh penalty on short numbers
    score = max(0.0, 1 - diff / max(6, ld))
    return score

def dob_score(a: str, b: str) -> float:
    """Equality after robust normalization; allow digit-only fallback and 2-digit years."""
    da = normalize_full(a, "date")
    db = normalize_full(b, "date")

    # If ISO parse succeeds for both, compare directly
    if da and db:
        if da == db:
            return 1.0

    def digits_only(x: str) -> str:
        if not x:
            return ""
        # strip labels like "dob:" and keep digits only
        d = "".join(ch for ch in x if ch.isdigit())
        # handle 2-digit year by preferring 20xx
        if len(d) == 6:  # ddmmyy
            d = f"{d[:4]}20{d[4:]}"
        if len(d) == 7:  # dddmmyy -> pad day
            d = f"0{d}"
        return d

    da_d = digits_only(a or da)
    db_d = digits_only(b or db)
    if da_d and db_d and da_d == db_d:
        return 1.0

    return 0.0

def gender_score(a: str, b: str) -> float:
    """Strict gender matching using defined synonym mapping only."""
    mapping = {
        # English & abbreviations
        "m": "male", "male": "male", "man": "male", "boy": "male",
        "f": "female", "female": "female", "woman": "female", "girl": "female",
        "other": "other", "others": "other", "nb": "other", "non-binary": "other", "nonbinary": "other",
        # Hindi (native script)
        "पुरुष": "male", "आदमी": "male", "लड़का": "male", "लड़का": "male", "बालक": "male",
        "महिला": "female", "स्त्री": "female", "नारी": "female", "लड़की": "female", "लड़की": "female",
        "अन्य": "other", "दूसरे": "other",
        # Hindi transliterations (after unidecode approximation)
        "purush": "male", "aadmi": "male", "ladka": "male", "balak": "male",
        "mahila": "female", "stree": "female", "naari": "female", "nari": "female", "ladki": "female",
        "anya": "other", "dusre": "other",
    }
    def norm(x: str) -> str:
        x = (x or "").strip().lower()
        return mapping.get(x, x)
    an = norm(a)
    bn = norm(b)
    return 1.0 if an and an == bn else 0.0

def decision_from_confidence(score: float, thresholds=(0.85, 0.6)) -> str:
    """Turn numeric score into a decision label."""
    match_t, review_t = thresholds
    if score >= match_t:
        return "MATCH"
    if score >= review_t:
        return "REVIEW"
    return "MISMATCH"

def aggregate_confidence(ocr_json: Dict[str, Any], user_json: Dict[str, Any], weights: Dict[str, float] = None) -> Tuple[float, Dict[str, float], list]:
    """
    Compute per-field scores and a weighted overall confidence.
    Returns (final_score_in_0_1, per_field_scores, notes_list).
    """
    scores = {}
    scores['name'] = name_score(ocr_json.get('name'), user_json.get('name'))
    scores['dob']  = dob_score(ocr_json.get('dob'), user_json.get('dob'))
    scores['phone'] = phone_score(ocr_json.get('phone'), user_json.get('phone'))
    scores['address'] = address_score(ocr_json.get('address'), user_json.get('address'))
    scores['gender'] = gender_score(ocr_json.get('gender'), user_json.get('gender'))

    # consider only fields present (non-empty) on both sides
    effective_weights = weights or FIELD_WEIGHTS_DEFAULT
    available = {k: v for k, v in effective_weights.items() if (ocr_json.get(k) not in (None, "")) and (user_json.get(k) not in (None, ""))}
    total_w = sum(available.values()) or 1.0

    final = 0.0
    notes = []
    for k, w in available.items():
        final += (w / total_w) * scores[k]
        if scores[k] < 0.6:
            notes.append(f"{k} low_score({scores[k]:.2f})")
    return final, scores, notes

# -----------------------------
# Public API wrapper for routes
# -----------------------------
def verify(ocr_json: Dict[str, Any], user_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare OCR/mapped fields with user/reference fields and return a
    JSON-friendly summary containing overall confidence, decision, per-field
    scores, and notes.
    """
    final, fields, notes = aggregate_confidence(ocr_json, user_json)
    return {
        "overall_confidence": round(final, 4),
        "decision": decision_from_confidence(final),
        "fields": fields,
        "notes": notes,
    }

# -----------------------------
# Example / quick test
# -----------------------------
if __name__ == "__main__":
    # sample OCR output and user-provided form
    ocr = {
        "name": "Ramesh Kumaar",
        "dob": "19/04/2001",
        "phone": "+91 98765-43210",
        "address": "Flat No. B-12/3, Gandhi St. (Near MG Road)",
        "gender": "Male"
    }
    user = {
        "name": "Ramesh Kumar",
        "dob": "19-04-2001",
        "phone": "9876543210",
        "address": "B12 Gandhi Street MG Road",
        "gender": "male"
    }

    final, fields, notes = aggregate_confidence(ocr, user)
    print("Overall confidence:", round(final, 4))
    print("Field scores:")
    for k, v in fields.items():
        print(f"  {k}: {v:.3f}")
    print("Decision:", decision_from_confidence(final))
    print("Notes:", notes)

import re
from typing import Dict, List, Optional
try:
    from rapidfuzz import fuzz  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False

class FieldMapper:
    def __init__(self):
        self.field_patterns = self._get_combined_patterns()
    
    def _get_combined_patterns(self):
        """Return patterns that include both Hindi and English"""
        return {
            'first_name': [
                # Hindi patterns
                r'\b(?:प्रथम|फर्स्ट)\s*नाम[:\s]*([^\n]{2,})',
                r'\bपहला\s*नाम[:\s]*([^\n]{2,})',
                # English patterns
                r'\b(?:FIRST|FUEST)\s*(?:NAME|MOUNT)[:\s]*([A-Za-z]{2,})',
                r'\bFirst Name[:\s]*([A-Za-z]{2,})'
            ],
            'middle_name': [
                # Hindi
                r'\bमध्य\s*नाम[:\s]*([^\n]{2,})',
                r'\bबीच\s*का\s*नाम[:\s]*([^\n]{2,})',
                # English
                r'\bMIDDLE\s*NAME[:\s]*([A-Za-z]{2,})',
                r'\bMiddle Name[:\s]*([A-Za-z]{2,})'
            ],
            'last_name': [
                # Hindi
                r'\bअंतिम\s*नाम[:\s]*([^\n]{2,})',
                r'\bआखिरी\s*नाम[:\s]*([^\n]{2,})',
                # English
                r'\bLAST\s*NAME[:\s]*([A-Za-z]{2,})',
                r'\bLast Name[:\s]*([A-Za-z]{2,})'
            ],
            'gender': [
                # Hindi
                r'\bलिंग[:\s]*([^\n]{4,10})',
                r'\bजेंडर[:\s]*([^\n]{4,10})',
                # English
                r'\b(?:Gender|Chender)[:\s]*([A-Za-z]{4,8})',
                r'\bSex[:\s]*([A-Za-z]{4,8})'
            ],
            'dob': [
                # Hindi
                r'\b(?:जन्म तिथि|जन्मतिथि)[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                r'\bजन्म\s*दिनांक[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                # English
                r'\b(?:Date of birth|DOB)[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                r'\bBirth Date[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})'
            ],
            'age': [
                # Hindi
                r'\bउम्र[:\s]*(\d{1,3})',
                r'\bआयु[:\s]*(\d{1,3})',
                # English
                r'\bAge[:\s]*(\d{1,3})',
                r'\bYears[:\s]*(\d{1,3})'
            ],
            'address_line1': [
                # Hindi
                r'\bपता\s*पंक्ति\s*१[:\s]*([^\n]{5,})',
                r'\bएड्रेस\s*लाइन\s*१[:\s]*([^\n]{5,})',
                # English
                r'\b(?:ADDRESS|ADDREAS)\s*LINE?\s*1[:\s]*([^\n]{5,})',
                r'\bAddress Line 1[:\s]*([^\n]{5,})'
            ],
            'address_line2': [
                # Hindi
                r'\bपता\s*पंक्ति\s*२[:\s]*([^\n]{5,})',
                r'\bएड्रेस\s*लाइन\s*२[:\s]*([^\n]{5,})',
                # English
                r'\b(?:ADDRESS|ADDREAS)\s*LINE?\s*2[:\s]*([^\n]{5,})',
                r'\bAddress Line 2[:\s]*([^\n]{5,})'
            ],
            'city': [
                # Hindi
                r'\bशहर[:\s]*([^\n]{3,})',
                r'\bसिटी[:\s]*([^\n]{3,})',
                # English
                r'\bCity[:\s]*([A-Za-z\s]{3,})',
                r'\bCITY[:\s]*([A-Za-z\s]{3,})'
            ],
            'state': [
                # Hindi
                r'\bराज्य[:\s]*([^\n]{3,})',
                r'\bस्टेट[:\s]*([^\n]{3,})',
                # English
                r'\bSTATE[:\s]*([A-Za-z\s]{3,})',
                r'\bState[:\s]*([A-Za-z\s]{3,})'
            ],
            'pincode': [
                # Hindi
                r'\b(?:पिन|पिनकोड)[:\s]*(\d{4,8})',
                r'\bपिन\s*कोड[:\s]*(\d{4,8})',
                # English
                r'\b(?:PIN|Prin)\s*CODE[:\s]*(\d{4,8})',
                r'\bPincode[:\s]*(\d{4,8})'
            ],
            'phone': [
                # Hindi
                r'\b(?:फोन|टेलीफोन)[:\s]*([+0-9\s\-().]{7,})',
                r'\bमोबाइल[:\s]*([+0-9\s\-().]{7,})',
                # English
                r'\b(?:Phone|PHONE)\s*(?:number)?[:\s]*([+0-9\s\-().]{7,})',
                r'\bMobile[:\s]*([+0-9\s\-().]{7,})'
            ],
            'email': [
                # Hindi
                r'\b(?:ईमेल|इमेल)[:\s]*([a-zA-Z0-9._%+-@]{5,})',
                r'\bई-मेल[:\s]*([a-zA-Z0-9._%+-@]{5,})',
                # English
                r'\b(?:EMAIL|EMAIL ID)[:\s]*([a-zA-Z0-9._%+-@]{5,})',
                r'\bE-?mail[:\s]*([a-zA-Z0-9._%+-@]{5,})'
            ]
        }
    
    def extract_fields(self, raw_text: str, document_type: Optional[str] = None) -> Dict[str, str]:
        extracted_data = {}
        name_parts = {}
        
        # If document_type focuses on name (e.g., Aadhaar/Voter), do a fast pass
        doc = (document_type or "").lower()
        if doc in {"aadhar", "aadhaar", "voter"}:
            # Try robust name extraction from noisy OCR lines
            lines = [ln.strip() for ln in raw_text.splitlines() if ln and len(ln.strip()) >= 3]

            # Candidate label phrases and a simple scorer
            name_labels = [
                "first name", "middle name", "last name",
                "given name", "surname", "family name"
            ]

            # Generic label starter detection to avoid taking the next label as value
            LABEL_STARTS = re.compile(
                r"^\s*(first\s*name|middle\s*name|last\s*name|surname|family\s*name|"
                r"gender|sex|address|addr|city|state|age|dob|date\s*of\s*birth|phone|mobile|email|e-?mail)\b",
                re.IGNORECASE,
            )

            def score_label(text: str) -> str:
                t = text.lower()
                best = None
                best_s = 0
                for lab in name_labels:
                    if _HAS_RAPIDFUZZ:
                        s = fuzz.token_set_ratio(lab, t)
                    else:
                        import difflib
                        s = int(difflib.SequenceMatcher(None, lab, t).ratio() * 100)
                    if s > best_s:
                        best_s = s
                        best = lab
                return best if best_s >= 80 else ""

            # Direct 'Name:' capture (single-label form)
            for ln in lines:
                m_name = re.match(r"^\s*name\s*[:\-]?\s*(.+)$", ln, flags=re.IGNORECASE)
                if m_name:
                    full = m_name.group(1).strip()
                    if full:
                        extracted_data['name'] = ' '.join(self.clean_field('first_name', full).split())
                        # do not break; still attempt parts below in case present

            i = 0
            while i < len(lines):
                ln = lines[i]
                label = score_label(ln)
                if label:
                    # Extract inline value after ':' or '-' else take next line
                    val = ""
                    m = re.search(r":|-", ln)
                    if m:
                        val = ln[m.end():].strip()
                    if not val and (i + 1) < len(lines):
                        nxt = lines[i + 1].strip()
                        # Avoid picking another label line (for any field)
                        if not LABEL_STARTS.match(nxt):
                            val = nxt
                            i += 1

                    if val:
                        if "first" in label or "given" in label:
                            name_parts['first_name'] = self.clean_field('first_name', val)
                        elif "middle" in label:
                            name_parts['middle_name'] = self.clean_field('middle_name', val)
                        elif "last" in label or "surname" in label or "family" in label:
                            name_parts['last_name'] = self.clean_field('last_name', val)
                i += 1

            # If we still don't have parts, fallback to existing regex patterns
            if not name_parts:
                for field in ['first_name', 'middle_name', 'last_name']:
                    for pattern in self.field_patterns.get(field, []):
                        m = re.search(pattern, raw_text, re.IGNORECASE)
                        if m:
                            name_parts[field] = self.clean_field(field, m.group(1).strip())
                            break

            # Combine and return only name
            if name_parts:
                first = name_parts.get('first_name', '')
                middle = name_parts.get('middle_name', '')
                last = name_parts.get('last_name', '')
                full_name = f"{first} {middle} {last}".strip()
                if full_name:
                    extracted_data['name'] = ' '.join(full_name.split())
            return extracted_data

        for field, patterns in self.field_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    raw_value = match.group(1).strip()
                    cleaned_value = self.clean_field(field, raw_value)
                    
                    # Handle name parts separately
                    if field in ['first_name', 'middle_name', 'last_name']:
                        name_parts[field] = cleaned_value
                    else:
                        extracted_data[field] = cleaned_value
                    break
        
        # Fallback: generic label-value parsing when patterns miss
        def fallback_label_parse(text: str) -> Dict[str, str]:
            out: Dict[str, str] = {}
            lines = [ln.strip() for ln in text.splitlines() if ln and len(ln.strip()) >= 3]
            # Canonical label targets
            targets = {
                'name': ['name', 'full name', 'given name'],
                'address': ['address', 'addr'],
                'phone': ['phone', 'phone number', 'mobile'],
                'email': ['email', 'email id', 'e-mail'],
                'gender': ['gender', 'sex'],
                'dob': ['date of birth', 'dob', 'birth date'],
                'age': ['age', 'years'],
            }
            # Parse each line by flexible pattern: label [:|-] value OR exact startswith
            for ln in lines:
                for canon, labs in targets.items():
                    for lab in labs:
                        # direct pattern with optional separator
                        m = re.match(rf"^\s*{re.escape(lab)}\s*[:\-]?\s*(.+)$", ln, flags=re.IGNORECASE)
                        if m:
                            val = m.group(1).strip()
                            if val:
                                cleaned = self.clean_field(canon if canon in {'phone','email','pincode'} else canon, val)
                                out[canon] = cleaned
                                break
                    if canon in out:
                        continue
            return out

        # Merge fallback results (do not overwrite existing)
        fb = fallback_label_parse(raw_text)
        for k, v in fb.items():
            if k not in extracted_data:
                extracted_data[k] = v

        # Combine name parts
        if name_parts:
            first = name_parts.get('first_name', '')
            middle = name_parts.get('middle_name', '')
            last = name_parts.get('last_name', '')
            full_name = f"{first} {middle} {last}".strip()
            if full_name:
                extracted_data['name'] = ' '.join(full_name.split())
        
        # Combine address lines
        if all(k in extracted_data for k in ['address_line1', 'address_line2']):
            addr1 = extracted_data.pop('address_line1')
            addr2 = extracted_data.pop('address_line2')
            extracted_data['address'] = f"{addr1} {addr2}".strip()
        elif 'address_line1' in extracted_data:
            extracted_data['address'] = extracted_data.pop('address_line1')
        elif 'address_line2' in extracted_data:
            extracted_data['address'] = extracted_data.pop('address_line2')
        
        return extracted_data
    
    def clean_field(self, field_name: str, raw_value: str) -> str:
        raw_value = raw_value.strip()
        
        if field_name == 'phone':
            return re.sub(r'[\s().-]', '', raw_value)
        
        elif field_name == 'email':
            cleaned = raw_value.lower()
            cleaned = re.sub(r'\s+', '', cleaned)
            cleaned = re.sub(r'qmail', 'gmail', cleaned)
            return cleaned
        
        elif field_name == 'pincode':
            digits = re.sub(r'\D', '', raw_value)
            return digits[:6] if digits else raw_value
        
        elif field_name in ['first_name', 'middle_name', 'last_name']:
            return raw_value.title()
        
        return raw_value
    
    def get_missing_fields(self, extracted_data: Dict[str, str]) -> List[str]:
        expected_fields = ['name', 'age', 'gender', 'address', 'phone', 'email']
        return [field for field in expected_fields if field not in extracted_data]


# Create mapper instance
field_mapper = FieldMapper()


def test_mapper():
    """Test with both English and Hindi"""
    
    english_text = """
    FIRST NAME: Abigail
    MIDDLE NAME: Grace  
    LAST NAME: Summer
    Gender: Female
    Date of birth: 27-09-2000
    Address Line1: Road#1, Street #2
    City: Bangalore
    Pin Code: 560068
    Phone number: 9987659110
    Email Id: abigail@gmail.com
    """
    
    hindi_text = """
    प्रथम नाम: राजेश
    मध्य नाम: कुमार
    अंतिम नाम: शर्मा
    लिंग: पुरुष
    जन्म तिथि: 15-03-1995
    पता पंक्ति १: १२३, एमजी रोड
    शहर: दिल्ली
    पिनकोड: ११०००१
    फोन: ९८७६५४३२१०
    ईमेल: rajes@example.com
    """
    
    mapper = FieldMapper()
    
    print("=== English Text ===")
    result_en = mapper.extract_fields(english_text)
    print(result_en)
    
    print("\n=== Hindi Text ===")
    result_hi = mapper.extract_fields(hindi_text)
    print(result_hi)


if __name__ == "__main__":
    test_mapper()

import re
from typing import Dict, List

class FieldMapper:
    def __init__(self):
        self.field_patterns = self._get_combined_patterns()
    
    def _get_combined_patterns(self):
        """Return patterns that include both Hindi and English"""
        return {
            'name': [
                # Generic single-line name capture (English/Hindi labels)
                r'\bName[:\s]*([^\n]{2,})',
                r'\bNAME[:\s]*([^\n]{2,})',
                r'\bनाम[:\s]*([^\n]{2,})',
            ],
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
                r'\bलिंग[:\s]*([^\n]{2,10})',
                r'\bजेंडर[:\s]*([^\n]{2,10})',
                # English
                r'\b(?:Gender|Chender)[:\s]*([A-Za-z]{2,10})',
                r'\bSex[:\s]*([A-Za-z]{2,10})'
            ],
            'dob': [
                # Hindi
                r'\b(?:जन्म तिथि|जन्मतिथि)[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                r'\bजन्म\s*दिनांक[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                # English
                r'\b(?:Date of birth|DOB)[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                r'\bBirth Date[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                # Month name variants e.g., 19 Apr 2001 / Apr 19, 2001
                r'\b(?:DOB|Date of birth|Birth Date)[:\s]*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})',
                r'\b(?:DOB|Date of birth|Birth Date)[:\s]*([A-Za-z]{3,9}\s+[0-9]{1,2},\s*[0-9]{4})'
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
            'address': [
                # Generic single-line address capture
                r'\bAddress[:\s]*([^\n]{5,})',
                r'\bADDRESS[:\s]*([^\n]{5,})',
                r'\bपता[:\s]*([^\n]{5,})',
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
    
    def extract_fields(self, raw_text: str) -> Dict[str, str]:
        extracted_data = {}
        name_parts = {}
        
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

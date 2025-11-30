import re
from typing import Dict, List

class FieldMapper:
    def __init__(self):
        # Separate DOB from age; keep age strictly numeric; allow multiple date delimiters.
        self.field_patterns = {
            'name': [
                r'\bName[:\s]+([^\n]{3,})',
                r'\bFull Name[:\s]+([^\n]{3,})',
                r'\bFirst name[:\s]+([^\n]{3,})'
            ],
            'dob': [
                r'\bDOB[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                r'\bDate of Birth[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})',
                # Day MonthName/Abbrev Year (e.g., 19 Apr 2001, 7 September 1999)
                r'\bDOB[:\s]*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})',
                r'\bDate of Birth[:\s]*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})'
            ],
            'age': [
                r'\bAge[:\s]*(\d{1,3})'
            ],
            'gender': [
                r'\bGender[:\s]*([^\n]{1,12})',
                r'\bSex[:\s]*([^\n]{1,12})'
            ],
            'address': [
                r'\bAddress[:\s]*([^\n]{5,})',
                r'\bAddr[:\s]*([^\n]{5,})'
            ],
            'phone': [
                r'\bPhone[:\s]*([+0-9\s\-()]{7,})',
                r'\bMobile[:\s]*([+0-9\s\-()]{7,})',
                r'\bContact[:\s]*([+0-9\s\-()]{7,})'
            ],
            'email': [
                r'\bEmail[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'\bEmail Id[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ]
        }
    
    def extract_fields(self, raw_text: str) -> Dict[str, str]:
        extracted_data = {}
        
        for field, patterns in self.field_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    raw_value = match.group(1).strip()
                    cleaned_value = self.clean_field(field, raw_value)
                    extracted_data[field] = cleaned_value
                    break
        
        return extracted_data
    
    def clean_field(self, field_name: str, raw_value: str) -> str:
        raw_value = raw_value.strip()
        if field_name == 'phone':
            # Preserve leading plus; strip spacing, hyphens, parentheses.
            cleaned = re.sub(r'[\s()-]', '', raw_value)
            if raw_value.startswith('+') and not cleaned.startswith('+'):
                cleaned = '+' + cleaned.lstrip('+')
            return cleaned
        if field_name == 'email':
            return raw_value.lower()
        if field_name == 'gender':
            return raw_value.lower()
        return raw_value
    
    def get_missing_fields(self, extracted_data: Dict[str, str]) -> List[str]:
        expected_fields = ['name', 'dob', 'age', 'gender', 'address', 'phone', 'email']
        return [f for f in expected_fields if f not in extracted_data]


field_mapper = FieldMapper()


def test_mapper():
    test_text = """
    Name: Ananya Shama
    Age: 29
    Gender: Female
    Address: 123, MG Road, Bengaluru
    Email: ananya.sharma@example.com
    Phone: +91-9876543210
    """
    
    mapper = FieldMapper()
    result = mapper.extract_fields(test_text)
    print("Test Result:", result)

if __name__ == "__main__":
    test_mapper()

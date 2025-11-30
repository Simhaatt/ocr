import re
from typing import Dict, List

class FieldMapper:
    def __init__(self):
        self.field_patterns = {
            'first_name': [
                r'\b(?:FIRST|FUEST)\s*(?:NAME|MOUNT)[:\s]*([A-Za-z]{2,})'
            ],
            'middle_name': [
                r'\bMIDDLE\s*NAME[:\s]*([A-Za-z]{2,})'
            ],
            'last_name': [
                r'\bLAST\s*NAME[:\s]*([A-Za-z]{2,})'
            ],
            'gender': [
                r'\b(?:Gender|Chender)[:\s]*([A-Za-z]{4,8})'
            ],
            'dob': [
                r'\b(?:Date of birth|DOB)[:\s]*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})'
            ],
            'address_line1': [
                r'\b(?:ADDRESS|ADDREAS)\s*LINE?\s*1[:\s]*([^\n]{5,})'
            ],
            'address_line2': [
                r'\b(?:ADDRESS|ADDREAS)\s*LINE?\s*2[:\s]*([^\n]{5,})'
            ],
            'city': [
                r'\bCity[:\s]*([A-Za-z\s]{3,})'
            ],
            'state': [
                r'\bSTATE[:\s]*([A-Za-z\s]{3,})'
            ],
            'pincode': [
                r'\b(?:PIN|Prin)\s*CODE[:\s]*(\d{4,8})'
            ],
            'phone': [
                r'\b(?:Phone|PHONE)\s*(?:number)?[:\s]*([+0-9\s\-().]{7,})'
            ],
            'email': [
                r'\b(?:EMAIL|EMAIL ID)[:\s]*([a-zA-Z0-9._%+-@]{5,})'
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
        
        if all(k in extracted_data for k in ['first_name', 'last_name']):
            first = extracted_data.pop('first_name')
            middle = extracted_data.pop('middle_name', '')
            last = extracted_data.pop('last_name')
            full_name = f"{first} {middle} {last}".strip()
            extracted_data['name'] = ' '.join(full_name.split())  
        
    
        if all(k in extracted_data for k in ['address_line1', 'address_line2']):
            addr1 = extracted_data.pop('address_line1')
            addr2 = extracted_data.pop('address_line2')
            extracted_data['address'] = f"{addr1} {addr2}".strip()
        
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
            return digits[:6]  
        
        elif field_name in ['first_name', 'middle_name', 'last_name']:
        
            return raw_value.title()
        
        return raw_value
    
    def get_missing_fields(self, extracted_data: Dict[str, str]) -> List[str]:
        expected_fields = ['name', 'dob', 'age', 'gender', 'address', 'phone', 'email']
        return [f for f in expected_fields if f not in extracted_data]


field_mapper = FieldMapper()


def test_mapper():
    test_text = """
    FUEST MOUNT : ABIQGLA
MIDDLE NAME: CHARGE
LAST NAME SUMMARY
Chender : Female 1987
Date of birth : 27-09-000 .
ADDRESS LIMEI : READ #1, STREET #2
ADDREAS LINE2: HSR LAYEN
" City : Bangalore 0 0 0 0
STATE: KAWAYAYAYA LAKE
Prin Code : 56000680008
" Phone number : 9987659110.
EMAIL ID. ABIQAL@ QMAIL.COM
    """
    
    mapper = FieldMapper()
    result = mapper.extract_fields(test_text)
    print("Test Result:", result)

if __name__ == "__main__":
    test_mapper()

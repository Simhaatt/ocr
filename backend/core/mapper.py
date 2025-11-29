import re
from typing import Dict, List

class FieldMapper:
    def __init__(self):
        
        self.field_patterns = {
            'name': [
                r'Name[:\s]*([^\n]+)',
                r'Full Name[:\s]*([^\n]+)',
                r'First name[:\s]*([^\n]+)' 
            ],
            'age': [
                r'Age[:\s]*(\d+)',
                r'DOB[:\s]*([\d-]+)',
                r'Date of Birth[:\s]*([\d-]+)'
            ],
            'gender': [
                r'Gender[:\s]*([^\n]+)',
                r'Sex[:\s]*([^\n]+)'
            ],
            'address': [
                r'Address[:\s]*([^\n]+)',
                r'Addr[:\s]*([^\n]+)'
            ],
            'phone': [
                r'Phone[:\s]*([+\d\s\-()]+)',    
                r'Mobile[:\s]*([+\d\s\-()]+)',   
                r'Contact[:\s]*([+\d\s\-()]+)'   
            ],
            'email': [
                r'Email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'Email Id[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
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
        if field_name == 'phone':
            return re.sub(r'[\s()-]', '', raw_value)
        elif field_name == 'email':
            return raw_value.lower().strip()
        return raw_value.strip()
    
    def get_missing_fields(self, extracted_data: Dict[str, str]) -> List[str]:
        expected_fields = ['name', 'age', 'gender', 'address', 'phone', 'email']
        return [field for field in expected_fields if field not in extracted_data]


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

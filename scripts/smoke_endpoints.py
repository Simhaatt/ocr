import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def main():
    print('--- OCR health ---')
    print(client.get('/api/v1/ocr/health').json())
    print('--- Extraction health ---')
    print(client.get('/api/v1/health').json())

    raw = (
        'Name: Ramesh Kumar\n'
        'DOB: 19/04/2001\n'
        'Age: 24\n'
        'Gender: Male\n'
        'Address: Flat No. B-12/3, Gandhi St. Near MG Road\n'
        'Phone: +91 98765-43210\n'
        'Email: ramesh.kumar@example.com\n'
    )
    user = {
        'name':'Ramesh Kumar',
        'dob':'19-04-2001',
        'phone':'9876543210',
        'address':'B12/3 Gandhi Street MG Road',
        'gender':'male'
    }
    resp = client.post('/api/v1/map-and-verify', json={'raw_text': raw, 'user': user})
    print('--- map-and-verify ---')
    print(resp.status_code)
    print(resp.json())

if __name__ == '__main__':
    main()

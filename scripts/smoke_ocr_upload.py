import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
from backend.app import app
client = TestClient(app)

import numpy as np, cv2 as cv

def main():
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    cv.putText(img, 'Name: Ramesh Kumar', (30, 80), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    cv.putText(img, 'DOB: 19/04/2001', (30, 130), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    cv.putText(img, 'Gender: Male', (30, 180), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    cv.putText(img, 'Address: B12/3 Gandhi Street MG Road', (30, 230), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
    cv.putText(img, 'Phone: +91 98765-43210', (30, 280), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    path = 'tmp_test.png'
    cv.imwrite(path, img)

    try:
        with open(path, 'rb') as f:
            files = {'file': ('tmp_test.png', f, 'image/png')}
            resp = client.post('/api/v1/ocr/extract-text', files=files)
            print('extract-text status:', resp.status_code)
            print('extract-text keys:', list(resp.json().keys()))
            body = resp.json()
            print('extracted_text sample:', body.get('extracted_text', '')[:200])
    finally:
        os.remove(path)

if __name__ == '__main__':
    main()

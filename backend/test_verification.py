import urllib.request
import json

def test():
    # 1. Login or Register
    reg_url = 'http://127.0.0.1:8000/api/v1/auth/register'
    user_payload = {
        'email': 'evaluator_test_2@ai.com',
        'password': 'password123',
        'full_name': 'Evaluator Test'
    }
    try:
        req = urllib.request.Request(
            reg_url, 
            data=json.dumps(user_payload).encode(), 
            headers={'Content-Type': 'application/json'}
        )
        res = urllib.request.urlopen(req)
        token = json.loads(res.read().decode())['access_token']
    except Exception:
        login_url = 'http://127.0.0.1:8000/api/v1/auth/login'
        form_data = 'username=evaluator_test_2%40ai.com&password=password123'
        req = urllib.request.Request(
            login_url,
            data=form_data.encode(),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        res = urllib.request.urlopen(req)
        token = json.loads(res.read().decode())['access_token']

    print("Auth Token acquired successfully")

    # 2. Upload Document
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    file_content = "# Quantum Machine Learning Research\n\nVariational quantum algorithms optimize parameterized quantum circuits to minimize cost functions."
    
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="quantum_research.txt"\r\n'
        'Content-Type: text/plain\r\n\r\n'
        f"{file_content}\r\n"
        f"--{boundary}--\r\n"
    ).encode('utf-8')

    upload_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/documents/upload',
        data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }
    )
    doc_res = urllib.request.urlopen(upload_req)
    doc_data = json.loads(doc_res.read().decode())
    doc_id = doc_data['id']
    print(f"Uploaded document ID: {doc_id}, Initial Status: {doc_data['status']}")

    # 3. Wait 3 seconds for Celery worker background task
    import time
    time.sleep(3)

    # 4. Fetch Document Detail (Chunks)
    detail_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/documents/{doc_id}',
        headers={'Authorization': f'Bearer {token}'}
    )
    detail_res = urllib.request.urlopen(detail_req)
    detail_data = json.loads(detail_res.read().decode())

    print(f"\n==========================================")
    print(f"DOCUMENT STATUS: {detail_data['status']}")
    print(f"TOTAL CHUNKS CREATED: {len(detail_data['chunks'])}")
    print(f"==========================================")

    for c in detail_data['chunks']:
        print(f"\nChunk #{c['chunk_index']} | Section: '{c['section']}' | Page: {c['page_number']}")
        print(f"Content: \"{c['content']}\"")
        print(f"Metadata: {c['chunk_metadata']}")

if __name__ == '__main__':
    test()

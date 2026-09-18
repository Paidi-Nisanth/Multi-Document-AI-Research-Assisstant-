import urllib.request
import json
import time

def run_quick_test():
    email = f"quick_eval_{int(time.time())}@ai.com"
    reg_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/auth/register',
        data=json.dumps({'email': email, 'password': 'password123', 'full_name': 'Quick Evaluator'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    token = json.loads(urllib.request.urlopen(reg_req).read().decode())['access_token']

    # Upload document inline
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    doc_text = "# Variational Quantum Algorithms\n\nParameterized quantum circuits optimize rotation angles to minimize cost functions in quantum machine learning."
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="variational_qa.txt"\r\n'
        'Content-Type: text/plain\r\n\r\n'
        f"{doc_text}\r\n"
        f"--{boundary}--\r\n"
    ).encode('utf-8')

    upload_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/documents/upload',
        data=body,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    doc_res = json.loads(urllib.request.urlopen(upload_req).read().decode())
    print(f"Document Upload Status: {doc_res['status']}")

    # Test Search Endpoints
    query = "quantum circuits optimization"
    for search_mode in ['vector', 'keyword', 'hybrid', 'rerank']:
        s_req = urllib.request.Request(
            f'http://127.0.0.1:8000/api/v1/search/{search_mode}',
            data=json.dumps({'query': query, 'top_k': 3}).encode(),
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        )
        s_res = json.loads(urllib.request.urlopen(s_req).read().decode())
        print(f"Search mode [{search_mode.upper()}]: {len(s_res)} results returned.")
        if s_res:
            print(f"  Top #1 Chunk Section: '{s_res[0].get('section')}' | Score: {s_res[0].get('similarity_score')}")

if __name__ == '__main__':
    run_quick_test()

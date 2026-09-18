import urllib.request
import json
import time

def test_mx():
    email = f"mx_eval_{int(time.time())}@ai.com"
    reg_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/auth/register',
        data=json.dumps({'email': email, 'password': 'password123', 'full_name': 'MX Evaluator'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    token = json.loads(urllib.request.urlopen(reg_req).read().decode())['access_token']

    # Upload document with exact target phrase
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    doc_text = "# Microscaling Formats\n\nMX format pushing limits of FP8 and FP4 floating point precision in deep neural network inference."
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="mx_format_paper.txt"\r\n'
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
    print(f"Uploaded Document ID: {doc_res['id']}, Status: {doc_res['status']}")

    time.sleep(1)

    # Search for "MX format pushing limits"
    query = "MX format pushing limits"
    for mode in ['vector', 'keyword', 'hybrid', 'rerank']:
        s_req = urllib.request.Request(
            f'http://127.0.0.1:8000/api/v1/search/{mode}',
            data=json.dumps({'query': query, 'top_k': 3}).encode(),
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        )
        s_res = json.loads(urllib.request.urlopen(s_req).read().decode())
        print(f"Mode [{mode.upper()}]: {len(s_res)} matches returned")
        if s_res:
            print(f"  Result #1 Score: {s_res[0].get('similarity_score')} | Content: \"{s_res[0].get('content')}\"")

if __name__ == '__main__':
    test_mx()

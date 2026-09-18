import urllib.request
import json
import time

def test_stage3():
    print("==================================================")
    print("STAGE 3 RETRIEVAL & EMBEDDING VERIFICATION SUITE")
    print("==================================================")

    unique_id = int(time.time())
    email = f"stage3_evaluator_{unique_id}@ai.com"

    # 1. Register User
    reg_url = 'http://127.0.0.1:8000/api/v1/auth/register'
    user_payload = {
        'email': email,
        'password': 'password123',
        'full_name': 'Stage 3 Evaluator'
    }
    
    req = urllib.request.Request(
        reg_url, 
        data=json.dumps(user_payload).encode(), 
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    token = json.loads(res.read().decode())['access_token']

    print(" Auth Token acquired successfully.")

    # 2. Upload Document
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    doc_text = (
        "# Introduction to Quantum Neural Networks\n\n"
        "Quantum Neural Networks (QNNs) combine quantum circuit architectures with deep learning optimization techniques.\n\n"
        "# Variational Quantum Circuits\n\n"
        "Parameterized quantum circuits optimize rotation angles on qubits to minimize loss functions in machine learning tasks.\n\n"
        "# Quantum Advantage and Entanglement\n\n"
        "Quantum entanglement allows QNNs to represent high-dimensional Hilbert space features exponentially faster than classical neural networks."
    )

    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="qnn_paper.txt"\r\n'
        'Content-Type: text/plain\r\n\r\n'
        f"{doc_text}\r\n"
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
    print(f" Uploaded document ID: {doc_id}, Initial Status: {doc_data['status']}")

    # Wait for Celery / Ingestion completion
    time.sleep(2)

    # Verify Document Status
    detail_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/documents/{doc_id}',
        headers={'Authorization': f'Bearer {token}'}
    )
    detail_res = urllib.request.urlopen(detail_req)
    detail_data = json.loads(detail_res.read().decode())
    print(f" Ingested Document Status: {detail_data['status']} | Chunks Created: {len(detail_data['chunks'])}\n")

    query_text = "How do variational quantum circuits optimize rotation angles?"

    # 3. Test Vector Search
    print("--- 1. Testing Vector Cosine Search (/api/v1/search/vector) ---")
    v_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/search/vector',
        data=json.dumps({'query': query_text, 'top_k': 3}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    v_res = json.loads(urllib.request.urlopen(v_req).read().decode())
    for r in v_res:
        print(f"   [Rank #{r.get('rank')}] Similarity: {r['similarity_score']} | Section: {r['section']}")
        print(f"   Content: \"{r['content'][:80]}...\"")

    # 4. Test Keyword Search
    print("\n--- 2. Testing Keyword Search (/api/v1/search/keyword) ---")
    k_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/search/keyword',
        data=json.dumps({'query': query_text, 'top_k': 3}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    k_res = json.loads(urllib.request.urlopen(k_req).read().decode())
    for r in k_res:
        print(f"   [Rank #{r.get('rank')}] Score: {r['similarity_score']} | Section: {r['section']}")

    # 5. Test Hybrid RRF Search
    print("\n--- 3. Testing Hybrid RRF Search (/api/v1/search/hybrid) ---")
    h_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/search/hybrid',
        data=json.dumps({'query': query_text, 'top_k': 3}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    h_res = json.loads(urllib.request.urlopen(h_req).read().decode())
    for r in h_res:
        print(f"   [Rank #{r.get('rank')}] RRF Score: {r['similarity_score']} | Section: {r['section']}")

    # 6. Test MS-MARCO Cross-Encoder Reranking Search
    print("\n--- 4. Testing MS-MARCO Cross-Encoder Rerank (/api/v1/search/rerank) ---")
    r_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/search/rerank',
        data=json.dumps({'query': query_text, 'top_k': 3}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    r_res = json.loads(urllib.request.urlopen(r_req).read().decode())
    for r in r_res:
        print(f"   [Rank #{r.get('rank')}] Rerank Score: {r.get('rerank_score')} | Section: {r['section']}")
        print(f"   Content: \"{r['content']}\"")

    print("\n==================================================")
    print("STAGE 3 RETRIEVAL API VERIFICATION SUCCESSFUL!")
    print("==================================================")

if __name__ == '__main__':
    test_stage3()

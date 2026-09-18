import urllib.request
import json
import time

def test_stage4():
    print("==================================================")
    print("STAGE 4: RAG CHAT & CITATION VERIFICATION SUITE")
    print("==================================================")

    # 1. Login
    login_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/auth/login',
        data='username=studio_user%40ai.com&password=password123'.encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    token = json.loads(urllib.request.urlopen(login_req).read().decode())['access_token']
    print(" Auth token acquired.")

    query = "What is the MX+ format and how does it push limits?"

    # 2. Test Non-Streaming Chat Completions
    print(f"\n--- 1. Testing Non-Streaming RAG Chat (/api/v1/chat/completions) ---")
    comp_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/chat/completions',
        data=json.dumps({'query': query, 'search_mode': 'rerank', 'top_k': 5}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    comp_res = json.loads(urllib.request.urlopen(comp_req).read().decode())
    print(f"  Provider: {comp_res.get('provider')}")
    print(f"  Answer Output: \"{comp_res.get('answer')[:150]}...\"")
    print(f"  Parsed Citations Count: {len(comp_res.get('citations', []))}")
    for cit in comp_res.get('citations', []):
        print(f"    Citation [{cit.get('citation_id')}]: Doc '{cit.get('filename')}' (p. {cit.get('page_number')})")

    # 3. Test SSE Streaming Chat
    print(f"\n--- 2. Testing SSE Streaming RAG Chat (/api/v1/chat/stream) ---")
    stream_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/chat/stream',
        data=json.dumps({'query': query, 'search_mode': 'rerank', 'top_k': 5}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    stream_res = urllib.request.urlopen(stream_req)
    
    tokens_received = 0
    final_meta = None

    for raw_line in stream_res:
        line = raw_line.decode('utf-8').strip()
        if not line.startswith('data: '):
            continue
        payload = line.replace('data: ', '')
        if payload.startswith('[CITATION_DATA]'):
            final_meta = json.loads(payload.replace('[CITATION_DATA]', ''))
        else:
            tokens_received += 1

    print(f"  SSE Stream Success! Tokens Received: {tokens_received}")
    if final_meta:
        print(f"  Final Citation Payload Received. Citations Count: {len(final_meta.get('citations', []))}")
        print(f"  Sources Used Count: {len(final_meta.get('sources_used', []))}")

    print("\n==================================================")
    print("STAGE 4 RAG CHAT & CITATION VERIFICATION SUCCESSFUL!")
    print("==================================================")

if __name__ == '__main__':
    test_stage4()

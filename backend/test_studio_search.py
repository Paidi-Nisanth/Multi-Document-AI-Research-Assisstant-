import urllib.request
import json

def test_studio():
    # Login as studio_user@ai.com
    login_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/auth/login',
        data='username=studio_user%40ai.com&password=password123'.encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    token = json.loads(urllib.request.urlopen(login_req).read().decode())['access_token']

    query = "MX pushing the limits"
    print(f"=== TESTING STUDIO SEARCH FOR QUERY: '{query}' ===")

    for mode in ['vector', 'keyword', 'hybrid', 'rerank']:
        s_req = urllib.request.Request(
            f'http://127.0.0.1:8000/api/v1/search/{mode}',
            data=json.dumps({'query': query, 'top_k': 5}).encode(),
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        )
        s_res = json.loads(urllib.request.urlopen(s_req).read().decode())
        print(f"\nMode [{mode.upper()}]: {len(s_res)} results returned.")
        for r in s_res[:3]:
            print(f"  Rank #{r.get('rank')} | Score: {r.get('similarity_score')} | Section: '{r.get('section')}'")
            print(f"  Snippet: {r.get('content')[:120]}...")

if __name__ == '__main__':
    test_studio()

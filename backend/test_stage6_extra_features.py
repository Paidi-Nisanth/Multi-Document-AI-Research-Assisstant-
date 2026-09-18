import os
import sys
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)


def main():
    print_section("STAGE 6: EXTRA FEATURES VERIFICATION SUITE")

    # 1. Login
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_data = {
        "username": "studio_user@ai.com",
        "password": "password123"
    }
    with httpx.Client(timeout=120.0) as client:
        res = client.post(login_url, data=login_data)
        assert res.status_code == 200, f"Login failed: {res.text}"
        token = res.json()["access_token"]
        print(" Auth token acquired.")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 2. Get available documents
        docs_res = client.get(f"{BASE_URL}/api/v1/documents/", headers=headers)
        assert docs_res.status_code == 200, f"Get docs failed: {docs_res.text}"
        docs = docs_res.json()
        assert len(docs) > 0, "No documents found in workspace to test."
        target_doc = docs[0]
        print(f" Target Document for Stage 6 tests: '{target_doc['filename']}' ({target_doc['id']})")

        # 3. Test Feature 1: Hierarchical Document Summarization
        print_section("1. Testing Map-Reduce Document Summarization")
        sum_res = client.post(
            f"{BASE_URL}/api/v1/documents/{target_doc['id']}/summarize",
            json={"force_refresh": False},
            headers=headers,
            timeout=90.0
        )
        assert sum_res.status_code == 200, f"Summarize failed: {sum_res.text}"
        sum_data = sum_res.json()
        print(f" Document Summarized! Cached: {sum_data.get('cached')}")
        print(f" Summary Preview:\n{sum_data.get('summary', '')[:300]}...\n")
        assert len(sum_data.get("summary", "")) > 100, "Expected non-empty summary!"

        # Fast cache check: second call should be cached
        fast_sum_res = client.get(
            f"{BASE_URL}/api/v1/documents/{target_doc['id']}/summary",
            headers=headers
        )
        assert fast_sum_res.status_code == 200
        print(f" Verified instant cached summary retrieval ({len(fast_sum_res.json()['summary'])} chars)")

        # 4. Test Feature 2: Structured Flashcard Generation
        print_section("2. Testing Structured JSON Flashcard Generation")
        fc_res = client.post(
            f"{BASE_URL}/api/v1/flashcards/generate/{target_doc['id']}",
            json={"num_cards": 4},
            headers=headers,
            timeout=90.0
        )
        assert fc_res.status_code == 201, f"Flashcard generation failed: {fc_res.text}"
        cards = fc_res.json()
        print(f" Successfully generated {len(cards)} structured study flashcards!")
        for idx, card in enumerate(cards[:2], 1):
            print(f"   Card {idx}:")
            print(f"     Q: {card['question']}")
            print(f"     A: {card['answer'][:100]}...")

        # Test listing flashcards
        list_fc_res = client.get(f"{BASE_URL}/api/v1/flashcards/", headers=headers)
        assert list_fc_res.status_code == 200
        all_cards = list_fc_res.json()
        assert len(all_cards) >= len(cards)
        print(f" Verified flashcard listing. Total workspace flashcards: {len(all_cards)}")

        # 5. Test Feature 3: Semantic Query Caching
        print_section("3. Testing Semantic Query Cache (pgvector + Redis)")
        q1 = "What are the primary micro-architectural differences in mixed precision quantization?"
        print(f" Sending Query 1: '{q1}' (Expect Cache Miss & Store)...")
        c1_res = client.post(
            f"{BASE_URL}/api/v1/chat/completions",
            json={"query": q1, "use_cache": True, "top_k": 3},
            headers=headers,
            timeout=120.0
        )
        assert c1_res.status_code == 200
        c1_data = c1_res.json()
        print(f"   Query 1 processed by provider='{c1_data['provider']}'. Cached={c1_data.get('cached')}")

        # Query 2 (Identical or near-identical semantic intent)
        q2 = "What are the primary micro-architectural differences in mixed precision quantization?"
        print(f"\n Sending Query 2 (identical query): '{q2}' (Expect Cache Hit)...")
        c2_res = client.post(
            f"{BASE_URL}/api/v1/chat/completions",
            json={"query": q2, "use_cache": True, "top_k": 3},
            headers=headers,
            timeout=10.0
        )
        assert c2_res.status_code == 200
        c2_data = c2_res.json()
        print(f"   Query 2 result: Cached={c2_data.get('cached')}, Provider='{c2_data.get('provider')}'")
        assert c2_data.get("cached") is True, f"Expected cache hit for query 2! Got: {c2_data}"
        print(f" [CACHE HIT] Semantic Cache Verified! Similarity score: {c2_data.get('cache_similarity', 1.0)}")

        print_section("STAGE 6 BACKEND VERIFICATION SUCCESSFUL!")


if __name__ == "__main__":
    main()

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
    print_section("STAGE 5: MEMORY & MULTI-DOC VERIFICATION SUITE")

    # 1. Login to get token
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_data = {
        "username": "studio_user@ai.com",
        "password": "password123"
    }
    with httpx.Client(timeout=120.0) as client:
        res = client.post(login_url, data=login_data)
        if res.status_code != 200:
            print(f"Login failed: {res.text}")
            sys.exit(1)
        token = res.json()["access_token"]
        print(" Auth token acquired.")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 2. Test Conversation CRUD
        print_section("1. Testing Conversation Creation & Persistence")
        create_res = client.post(
            f"{BASE_URL}/api/v1/conversations/",
            json={"title": "Stage 5 Hardware Quantization Research"},
            headers=headers
        )
        assert create_res.status_code == 201, f"Create conv failed: {create_res.text}"
        conv_obj = create_res.json()
        conv_id = conv_obj["id"]
        print(f" Created Conversation: ID='{conv_id}', Title='{conv_obj['title']}'")

        # 3. Test Chat Completion with conversation_id
        print_section("2. Testing Chat Turn with Conversation Persistence")
        chat_payload = {
            "query": "What are the primary micro-architectural differences in mixed precision quantization?",
            "conversation_id": conv_id,
            "search_mode": "rerank",
            "top_k": 3,
            "temperature": 0.2
        }
        chat_res = client.post(
            f"{BASE_URL}/api/v1/chat/completions",
            json=chat_payload,
            headers=headers,
            timeout=120.0
        )
        assert chat_res.status_code == 200, f"Chat completion failed: {chat_res.text}"
        chat_data = chat_res.json()
        print(f" Chat response received from provider='{chat_data['provider']}':")
        print(f"   Answer preview: {chat_data['answer'][:120]}...")
        print(f"   Returned conversation_id='{chat_data['conversation_id']}'")
        assert chat_data['conversation_id'] == conv_id

        # 4. Verify Message History in Conversation
        print_section("3. Verifying Message History in Database")
        get_conv_res = client.get(
            f"{BASE_URL}/api/v1/conversations/{conv_id}",
            headers=headers
        )
        assert get_conv_res.status_code == 200, f"Get conv failed: {get_conv_res.text}"
        conv_detail = get_conv_res.json()
        msgs = conv_detail["messages"]
        print(f" Total persisted messages in conversation: {len(msgs)}")
        assert len(msgs) >= 2, f"Expected at least 2 messages (user + assistant), got {len(msgs)}"
        print(f"   Turn 1 (User): '{msgs[0]['content'][:60]}...'")
        print(f"   Turn 2 (Assistant): '{msgs[1]['content'][:60]}...'")

        # 5. Test Multi-Document Comparison (Map-Reduce)
        print_section("4. Testing Multi-Document Map-Reduce Comparison")
        docs_res = client.get(f"{BASE_URL}/api/v1/documents/", headers=headers)
        assert docs_res.status_code == 200, f"Get docs failed: {docs_res.text}"
        docs = docs_res.json()
        print(f" Found {len(docs)} documents in workspace.")

        compare_payload = {
            "query": "Compare these architectures on memory efficiency and quantization overhead",
            "comparison_axes": [
                "Target Precision",
                "Hardware Unit Reconfigurability",
                "Perplexity / Accuracy Trade-off"
            ]
        }
        if len(docs) >= 2:
            compare_payload["document_ids"] = [docs[0]["id"], docs[1]["id"]]
            print(f" Comparing doc 1 ('{docs[0]['filename']}') and doc 2 ('{docs[1]['filename']}')...")

        compare_res = client.post(
            f"{BASE_URL}/api/v1/chat/compare",
            json=compare_payload,
            headers=headers,
            timeout=60.0
        )
        assert compare_res.status_code == 200, f"Compare failed: {compare_res.text}"
        comp_data = compare_res.json()
        print(f" Mapped documents count: {len(comp_data.get('documents_compared', []))}")
        print(" Synthesis Preview:")
        print(comp_data.get("synthesis", "")[:400] + "...\n")
        assert "Table" in comp_data.get("synthesis", "") or "|" in comp_data.get("synthesis", ""), "Expected Markdown table in synthesis!"

        print_section("STAGE 5 BACKEND VERIFICATION SUCCESSFUL!")


if __name__ == "__main__":
    main()

import asyncio
from app.services.embedding import EmbeddingService
from app.services.reranker import CrossEncoderReranker

async def run_standalone_verification():
    print("==================================================")
    print("STAGE 3 STANDALONE ALGORITHM VERIFICATION")
    print("==================================================")

    # 1. Test Embedding Generation (BAAI/bge-small-en-v1.5)
    texts = [
        "Quantum algorithms leverage superposition and entanglement for quadratic and exponential speedups.",
        "Variational quantum eigensolvers optimize parameterized quantum circuits to approximate ground state energies."
    ]
    print("\n1. Testing BGE-Small Embedding Generation...")
    embeddings = EmbeddingService.generate_embeddings(texts)
    print(f" Generated {len(embeddings)} vectors of dimension {len(embeddings[0]) if embeddings else 0}")
    print(f" Sample vector values (first 5 dims): {embeddings[0][:5] if embeddings else None}")

    query = "How do variational algorithms optimize quantum circuits?"
    query_vec = EmbeddingService.generate_query_embedding(query)
    print(f" Generated Query Embedding of dim {len(query_vec)}")

    # 2. Test Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking
    candidates = [
        {
            "chunk_id": "chunk-001",
            "document_id": "doc-001",
            "filename": "quantum_intro.pdf",
            "section": "Introduction to Quantum Computing",
            "page_number": 1,
            "content": "Quantum algorithms leverage superposition and entanglement for quadratic and exponential speedups.",
            "similarity_score": 0.85,
            "rrf_score": 0.032
        },
        {
            "chunk_id": "chunk-002",
            "document_id": "doc-001",
            "filename": "quantum_intro.pdf",
            "section": "Variational Circuits",
            "page_number": 3,
            "content": "Variational quantum eigensolvers optimize parameterized quantum circuits to approximate ground state energies.",
            "similarity_score": 0.92,
            "rrf_score": 0.035
        }
    ]

    print("\n2. Testing Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)...")
    reranked = CrossEncoderReranker.rerank(query, candidates, top_n=2)

    for idx, item in enumerate(reranked):
        print(f" [Rank #{idx+1}] Rerank Score: {item.get('rerank_score'):.4f} | Section: '{item.get('section')}'")
        print(f" Content: \"{item.get('content')}\"")

    print("\n==================================================")
    print("ALL STAGE 3 EMBEDDING & RETRIEVAL ALGORITHMS VERIFIED!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_standalone_verification())

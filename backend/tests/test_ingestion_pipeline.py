import os
import tempfile
from app.services.extractor import DocumentExtractor, ExtractedBlock
from app.services.chunker import StructureAwareChunker

def test_txt_extraction_and_chunking():
    sample_text = """# Introduction to Quantum Machine Learning

Quantum Machine Learning (QML) merges quantum computing with classical machine learning algorithms. By leveraging quantum principles like superposition and entanglement, QML algorithms promise speedups for complex computations.

# Quantum Circuits and Variational Algorithms

Variational Quantum Circuits (VQCs) act as parameterized models trained via classical gradient descent. They are widely applied in quantum chemistry, optimization, and generative modeling.

# Experimental Results

Our benchmark shows that hybrid mamba-transformer models achieve high accuracy on time-series quantum state forecasting while maintaining low parameter footprint.
"""

    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as f:
        f.write(sample_text)
        temp_path = f.name

    try:
        # Test Extraction
        blocks = DocumentExtractor.extract(temp_path, "txt")
        print(f"Extracted {len(blocks)} structural blocks.")
        for b in blocks:
            print(f"  - Section: '{b.section_title}', Length: {len(b.content)} chars")

        assert len(blocks) >= 3, "Expected at least 3 sections extracted"

        # Test Chunker
        chunker = StructureAwareChunker(target_tokens=50, max_tokens=100, overlap_tokens=10)
        chunks = chunker.chunk_blocks(blocks)
        print(f"\nGenerated {len(chunks)} chunks:")
        for c in chunks:
            print(f"  Chunk index {c.chunk_index}: [{c.section}] page={c.page_number} ({c.chunk_metadata.get('token_count')} tokens)")

        assert len(chunks) >= 3, "Expected at least 3 chunks generated"
        print("\nUnit test verification PASSED successfully!")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    test_txt_extraction_and_chunking()

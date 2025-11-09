"""Direct test of embedding service"""
import os
os.environ['ASTRA_EMBEDDINGS_MODEL'] = 'sentence-transformers/all-MiniLM-L6-v2'

from embedding_service import get_embedding_service

service = get_embedding_service()
print(f"Service stats: {service.get_stats()}")

# Test encoding
test_text = "quantum computing breakthrough"
print(f"\nEncoding test text: '{test_text}'")
embedding = service.encode(test_text)
print(f"Embedding shape: {embedding.shape}")
print(f"Embedding sample (first 5): {embedding[:5]}")

# Test search
print(f"\nCurrent index has {len(service.memory_ids)} vectors")
if len(service.memory_ids) > 0:
    print("Memory IDs in index:", service.memory_ids)
    results = service.search("quantum physics", top_k=3)
    print(f"Search results: {results}")
else:
    print("Index is empty - no vectors to search")

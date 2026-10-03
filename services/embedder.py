"""
Lightweight embeddings using Voyage AI API (no large model downloads).
Alternative to sentence-transformers to reduce bundle size for Vercel.
"""
import os
import httpx

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3-lite")  # lightweight model

# Fallback to a simple TF-IDF hash-based embedding if no API key
USE_API = bool(VOYAGE_API_KEY)

def _hash_embedding(text: str, dim: int = 384) -> list[float]:
    """Simple fallback: hash-based pseudo-embedding (not semantic, but lightweight)"""
    import hashlib
    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()
    
    # Convert to floats and normalize
    embedding = []
    for i in range(dim):
        byte_val = hash_bytes[i % len(hash_bytes)]
        embedding.append((byte_val / 255.0) * 2 - 1)  # normalize to [-1, 1]
    
    # Simple L2 normalization
    magnitude = sum(x**2 for x in embedding) ** 0.5
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]
    
    return embedding


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts using Voyage AI API or fallback to hash-based"""
    if not USE_API:
        # Fallback for local dev without API key
        return [_hash_embedding(text) for text in texts]
    
    try:
        response = httpx.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "input": texts,
                "model": VOYAGE_MODEL,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
    except Exception as e:
        print(f"Voyage API error, using fallback: {e}")
        return [_hash_embedding(text) for text in texts]


def embed_query(query: str) -> list[float]:
    """Embed a single query text"""
    embeddings = embed_texts([query])
    return embeddings[0]
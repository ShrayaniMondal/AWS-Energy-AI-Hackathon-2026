"""
Vector index for semantic search over DDR narratives and reference docs.

Uses Amazon Bedrock (Titan Embeddings) + FAISS for in-memory similarity search.
Falls back to a simple TF-IDF index if Bedrock is unavailable.
"""

import json
import pickle
from pathlib import Path

import numpy as np
from data_loader import load_narrative_chunks, load_reference_docs

INDEX_CACHE_DIR = Path(__file__).resolve().parent.parent / "outputs" / ".cache"


def _get_bedrock_embeddings(
    texts: list[str], model_id: str = "amazon.titan-embed-text-v2:0"
) -> np.ndarray:
    """Generate embeddings using Amazon Bedrock Titan."""
    import boto3

    client = boto3.client("bedrock-runtime")
    embeddings = []
    batch_size = 5
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for text in batch:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps({"inputText": text[:8000]}),
            )
            result = json.loads(response["body"].read())
            embeddings.append(result["embedding"])
    return np.array(embeddings, dtype="float32")


def _get_tfidf_embeddings(texts: list[str]) -> np.ndarray:
    """Fallback: TF-IDF embeddings when Bedrock is unavailable."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(max_features=512, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    _save_pickle(vectorizer, "tfidf_vectorizer.pkl")
    return matrix.toarray().astype("float32")


def build_index(use_bedrock: bool = True) -> dict:
    """
    Build a FAISS index over all narrative chunks and reference docs.

    Returns:
        {
            "index": faiss.IndexFlatIP,
            "chunks": list[dict],  # parallel array — chunks[i] matches index vector i
            "use_bedrock": bool,
        }
    """
    import faiss

    narrative_chunks = load_narrative_chunks()
    ref_docs = load_reference_docs()

    all_chunks = []
    texts = []

    for chunk in narrative_chunks:
        all_chunks.append(chunk)
        texts.append(chunk["text"])

    for doc in ref_docs:
        all_chunks.append(
            {
                "text": doc["text"],
                "source": doc["source"],
                "well_key": "",
                "date": "",
                "corpus": "reference",
                "metadata": {"heading": doc["heading"]},
            }
        )
        texts.append(doc["text"])

    if not texts:
        raise ValueError("No text chunks found to index")

    if use_bedrock:
        try:
            embeddings = _get_bedrock_embeddings(texts)
        except Exception as e:
            print(f"Bedrock unavailable ({e}), falling back to TF-IDF")
            embeddings = _get_tfidf_embeddings(texts)
            use_bedrock = False
    else:
        embeddings = _get_tfidf_embeddings(texts)

    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    return {
        "index": index,
        "chunks": all_chunks,
        "use_bedrock": use_bedrock,
        "dim": dim,
    }


def search(query: str, index_data: dict, top_k: int = 5) -> list[dict]:
    """
    Semantic search over the index.

    Returns top_k results, each with: text, source, score, well_key, date, corpus.
    """
    import faiss

    if index_data["use_bedrock"]:
        q_emb = _get_bedrock_embeddings([query])
    else:
        vectorizer = _load_pickle("tfidf_vectorizer.pkl")
        q_emb = vectorizer.transform([query]).toarray().astype("float32")

    faiss.normalize_L2(q_emb)
    scores, indices = index_data["index"].search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0], strict=True):
        if idx < 0:
            continue
        chunk = index_data["chunks"][idx]
        results.append({**chunk, "score": float(score)})
    return results


def _save_pickle(obj, filename: str):
    INDEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_CACHE_DIR / filename, "wb") as f:
        pickle.dump(obj, f)


def _load_pickle(filename: str):
    with open(INDEX_CACHE_DIR / filename, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    print("Building vector index...")
    index_data = build_index(use_bedrock=False)
    print(f"Indexed {len(index_data['chunks'])} chunks, dim={index_data['dim']}")

    test_queries = [
        "stuck pipe incidents",
        "mud weight increase in Wolfcamp",
        "bit wear and ROP decline",
    ]
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        results = search(q, index_data, top_k=3)
        for r in results:
            print(f"  [{r['score']:.3f}] {r['source']}: {r['text'][:100]}...")

# =====================================
# RAG SEARCH API - ANSTAT
# Service de recherche uniquement (FAISS + reranking)
# Le LLM est gere par le Pipe OpenWebUI
# =====================================
import json
import os
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import List, Dict

import numpy as np
import faiss
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, CrossEncoder

# =====================================
# CONFIGURATION
# =====================================
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
FAISS_PATH = DATA_DIR / "embeddings" / "faiss_index.bin"
CHUNK_MAP_PATH = DATA_DIR / "embeddings" / "chunk_map.json"

TOP_K_SEARCH = int(os.getenv("TOP_K_SEARCH", "10"))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "5"))

RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-2-v2")
RERANKER_MAX_LENGTH = int(os.getenv("RERANKER_MAX_LENGTH", "512"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# =====================================
# CHARGEMENT DES DONNEES
# =====================================
print("=" * 60)
print("RAG SEARCH API - ANSTAT")
print("=" * 60)

print(f"Loading FAISS index from {FAISS_PATH}...")
index = faiss.read_index(str(FAISS_PATH))
print(f"  FAISS: {index.ntotal} vecteurs, {index.d} dimensions")

FAISS_THREADS = int(os.getenv("OMP_NUM_THREADS", "4"))
faiss.omp_set_num_threads(FAISS_THREADS)

print(f"Loading chunk_map from {CHUNK_MAP_PATH}...")
with open(CHUNK_MAP_PATH, "r", encoding="utf-8") as f:
    chunk_map = json.load(f)
chunk_ids = list(chunk_map.keys())
print(f"  {len(chunk_ids)} chunks charges")

# =====================================
# MODELE D'EMBEDDING
# =====================================
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
print(f"Loading embedding model: {EMBED_MODEL_NAME}...")
embed_model = SentenceTransformer(EMBED_MODEL_NAME)
embed_dim = embed_model.get_sentence_embedding_dimension()
print(f"  Modele charge: {embed_dim} dimensions")

if embed_dim != index.d:
    raise RuntimeError(
        f"Dimension mismatch: modele={embed_dim}, index={index.d}"
    )

# =====================================
# RERANKER
# =====================================
print(f"Loading reranker: {RERANKER_MODEL_NAME}...")
reranker = CrossEncoder(RERANKER_MODEL_NAME, max_length=RERANKER_MAX_LENGTH)
print(f"  Reranker charge (max_length={RERANKER_MAX_LENGTH})")

print(f"\nSearch API pret: {len(chunk_ids)} chunks, {index.ntotal} vecteurs")
print("=" * 60)

# =====================================
# CACHE D'EMBEDDINGS
# =====================================
CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "256"))


@lru_cache(maxsize=CACHE_SIZE)
def _cached_embedding(query_hash: str, query: str):
    return embed_model.encode(
        query, normalize_embeddings=True, show_progress_bar=False
    ).astype(np.float32)


def get_query_embedding(query: str) -> np.ndarray:
    query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
    return _cached_embedding(query_hash, query)


# =====================================
# RECHERCHE FAISS + RERANKING
# =====================================
def search(query: str, top_k_search: int = None, top_k_rerank: int = None) -> List[Dict]:
    if top_k_search is None:
        top_k_search = TOP_K_SEARCH
    if top_k_rerank is None:
        top_k_rerank = TOP_K_RERANK

    query_emb = get_query_embedding(query)
    scores, indices = index.search(np.array([query_emb]), top_k_search)

    candidates = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(chunk_ids):
            continue
        chunk_id = chunk_ids[idx]
        chunk = chunk_map.get(chunk_id, {})
        if not chunk:
            continue
        candidates.append({
            "faiss_score": float(score),
            "content": chunk.get("content", ""),
            "doc": chunk.get("document_id", ""),
            "page": chunk.get("page_number", 0),
            "source": chunk.get("source_file", ""),
        })

    if not candidates:
        return []

    rerank_pairs = [(query, c["content"]) for c in candidates]
    rerank_scores = reranker.predict(rerank_pairs)

    ranked = sorted(
        zip(candidates, rerank_scores),
        key=lambda x: x[1],
        reverse=True,
    )

    results = []
    for candidate, rr_score in ranked[:top_k_rerank]:
        results.append({
            "score": float(rr_score),
            "faiss_score": candidate["faiss_score"],
            "content": candidate["content"],
            "doc": candidate["doc"],
            "page": candidate["page"],
            "source": candidate["source"],
        })

    return results


# =====================================
# FASTAPI
# =====================================
app = FastAPI(title="RAG Search API - ANSTAT", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    top_k_search: int = None
    top_k_rerank: int = None


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "chunks": len(chunk_ids),
        "vectors": index.ntotal,
        "embedding_model": EMBED_MODEL_NAME,
        "reranker": RERANKER_MODEL_NAME,
    }


@app.post("/search")
async def search_endpoint(req: SearchRequest):
    results = search(req.query, req.top_k_search, req.top_k_rerank)
    return {"query": req.query, "results": results, "count": len(results)}


# =====================================
# LANCEMENT
# =====================================
if __name__ == "__main__":
    import uvicorn

    workers = int(os.getenv("UVICORN_WORKERS", "1"))
    print(f"Demarrage Search API sur port 8084 (workers={workers})")

    uvicorn.run(
        "rag_api:app",
        host="0.0.0.0",
        port=8084,
        workers=workers,
        limit_concurrency=100,
        timeout_keep_alive=30,
    )

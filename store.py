import json
import os
from pathlib import Path

import numpy as np
from openai import OpenAI

DATA_DIR = Path(__file__).parent / "clients_data"
DATA_DIR.mkdir(exist_ok=True)

EMBEDDING_MODEL = "text-embedding-3-small"


def _client_path(client_id):
    return DATA_DIR / f"{client_id}.json"


def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY nahi mila. .env file mein set karein."
        )
    return OpenAI(api_key=api_key)


def embed_texts(texts, oa_client):
    """Batch-embed a list of strings, returns list of vectors."""
    resp = oa_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def save_client_kb(client_id, business_name, source_url, chunks, theme_color):
    data = {
        "client_id": client_id,
        "business_name": business_name,
        "source_url": source_url,
        "theme_color": theme_color,
        "chunks": chunks,
    }
    """Embed chunks and save the knowledge base for a client."""

    oa_client = get_openai_client()

    texts = [c["text"] for c in chunks]
    vectors = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        vectors.extend(embed_texts(batch, oa_client))

    for c, v in zip(chunks, vectors):
        c["embedding"] = v

    data = {
        "client_id": client_id,
        "business_name": business_name,
        "source_url": source_url,
        "chunks": chunks,
        "theme_color": theme_color,
    }
    with open(_client_path(client_id), "w", encoding="utf-8") as f:
        json.dump(data, f)

    return len(chunks)


def load_client_kb(client_id):
    path = _client_path(client_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def client_exists(client_id):
    return _client_path(client_id).exists()


def get_relevant_chunks(client_id, question, top_k=8):
    kb = load_client_kb(client_id)
    if not kb or not kb["chunks"]:
        return []

    oa_client = get_openai_client()
    q_vector = np.array(embed_texts([question], oa_client)[0])

    matrix = np.array([c["embedding"] for c in kb["chunks"]])
    norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_vector)
    norms[norms == 0] = 1e-10
    scores = matrix @ q_vector / norms

    top_idx = np.argsort(scores)[::-1][:top_k]
    results = [kb["chunks"][i] for i in top_idx if scores[i] > 0.12]

    count_keywords = [
        "kitne", "kitni", "ginti", "count", "how many", "total",
        "sare", "saare", "number of",
    ]
    if any(kw in question.lower() for kw in count_keywords):
        count_chunks = [c for c in kb["chunks"] if c.get("is_count")]
        existing_texts = {c["text"] for c in results}
        for c in count_chunks:
            if c["text"] not in existing_texts:
                results.append(c)

    return results
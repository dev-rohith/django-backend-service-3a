import json
import os
import threading

import faiss
import numpy as np
from django.conf import settings
from sentence_transformers import SentenceTransformer

from ai.constants import EMBEDDING_MODEL

DIMENSION = 384  # output size of EMBEDDING_MODEL (all-MiniLM-L6-v2)


class VectorStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._encoder = None
        self._index = None
        self._meta = {}
        self._index_path = None
        self._meta_path = None

    def _load(self):
        if self._encoder is not None:
            return
        self._encoder = SentenceTransformer(EMBEDDING_MODEL)
        index_dir = str(settings.FAISS_INDEX_DIR)
        os.makedirs(index_dir, exist_ok=True)
        self._index_path = os.path.join(index_dir, "index.faiss")
        self._meta_path = os.path.join(index_dir, "metadata.json")

        if os.path.exists(self._index_path) and os.path.exists(self._meta_path):
            self._index = faiss.read_index(self._index_path)
            with open(self._meta_path) as f:
                self._meta = json.load(f)
        else:
            self._index = faiss.IndexIDMap(faiss.IndexFlatL2(DIMENSION))

    def _embed(self, text: str) -> np.ndarray:
        vec = self._encoder.encode(text, normalize_embeddings=True)
        return np.array(vec, dtype=np.float32).reshape(1, -1)

    def _save(self):
        faiss.write_index(self._index, self._index_path)
        with open(self._meta_path, "w") as f:
            json.dump(self._meta, f)

    def add(self, chunk_id: int, document_id: str, text: str) -> None:
        with self._lock:
            self._load()
            self._index.add_with_ids(self._embed(text), np.array([chunk_id], dtype=np.int64))
            self._meta[str(chunk_id)] = {"document_id": document_id, "chunk_text": text}
            self._save()

    def remove(self, chunk_ids: list[int]) -> None:
        if not chunk_ids:
            return
        with self._lock:
            self._load()
            self._index.remove_ids(
                faiss.IDSelectorBatch(np.array(chunk_ids, dtype=np.int64))
            )
            for cid in chunk_ids:
                self._meta.pop(str(cid), None)
            self._save()

    def search(self, query: str, k: int = 3) -> list[dict]:
        with self._lock:
            self._load()
            if self._index.ntotal == 0:
                return []
            _, ids = self._index.search(self._embed(query), min(k, self._index.ntotal))
            return [self._meta[str(i)] for i in ids[0] if i >= 0 and str(i) in self._meta]


store = VectorStore()

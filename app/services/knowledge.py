import json
import os
from typing import List, Dict, Optional

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sentence_transformers import SentenceTransformer

from app.config import settings


class KnowledgeBase:
    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

        return self._model

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or getattr(settings, "knowledge_base_dir", "data/kb")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.embeddings_path = os.path.join(self.storage_dir, "embeddings.npy")
        self.meta_path = os.path.join(self.storage_dir, "metadata.json")
        self._model = None
        self.model_name = "all-MiniLM-L6-v2"
        self._embeddings = None
        self._metadata: List[Dict] = []
        self._nn = None
        self._load()

    def _load(self):
        if os.path.exists(self.embeddings_path) and os.path.exists(self.meta_path):
            try:
                self._embeddings = np.load(self.embeddings_path)
                with open(self.meta_path, "r", encoding="utf-8") as fh:
                    self._metadata = json.load(fh)
                if len(self._metadata) and self._embeddings is not None:
                    self._fit_index()
            except Exception:
                self._embeddings = None
                self._metadata = []

    def _fit_index(self):
        if self._embeddings is None or len(self._embeddings) == 0:
            self._nn = None
            return
        self._nn = NearestNeighbors(n_neighbors=5, metric="cosine")
        self._nn.fit(self._embeddings)

    def _persist(self):
        if self._embeddings is not None:
            np.save(self.embeddings_path, self._embeddings)
        with open(self.meta_path, "w", encoding="utf-8") as fh:
            json.dump(self._metadata, fh, ensure_ascii=False, indent=2)

    def _chunk_text(self, text: str, chunk_size: int = 800) -> List[str]:
        text = text.strip()
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end].strip())
            start = end
        return chunks

    def add_documents(self, docs: List[Dict[str, str]]):
        """Add documents to the knowledge base.

        Each doc is a dict with keys: "id", "text" and optional "title"/"meta".
        """
        new_texts = []
        new_meta = []
        for doc in docs:
            text = doc.get("text") or ""
            title = doc.get("title")
            doc_id = doc.get("id")
            chunks = self._chunk_text(text)
            for i, chunk in enumerate(chunks):
                meta = {"source_id": doc_id, "chunk_index": i, "title": title, "text": chunk}
                new_texts.append(chunk)
                new_meta.append(meta)

        if not new_texts:
            return

        embeddings = self.model.encode(new_texts, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype=np.float32)

        if self._embeddings is None:
            self._embeddings = embeddings
            self._metadata = new_meta
        else:
            self._embeddings = np.vstack([self._embeddings, embeddings])
            self._metadata.extend(new_meta)

        self._fit_index()
        self._persist()

    def query(self, query_text: str, top_k: int = 3) -> List[Dict]:
        top_k = max(1, min(top_k, 10))

        if (
            self._embeddings is None
            or self._embeddings.shape[0] == 0
            or self._nn is None
        ):
            return []

        q_emb = self.model.encode([query_text], show_progress_bar=False)
        distances, indices = self._nn.kneighbors(q_emb, n_neighbors=min(top_k, len(self._embeddings)))
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            meta = self._metadata[int(idx)]
            results.append({"meta": meta, "distance": float(dist), "text": meta.get("text")})
        return results


# singleton to import elsewhere
kb = KnowledgeBase()
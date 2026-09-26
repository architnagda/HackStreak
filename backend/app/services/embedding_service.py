import os
import logging
from typing import List, Dict, Any, Optional

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Embedding generation using sentence-transformers/all-MiniLM-L6-v2
    and ChromaDB vector index persistence.
    """

    def __init__(self):
        self._model = None
        self._chroma_client = None
        self._collection = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
            # Automatically downloads or loads from local cache
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer model loaded successfully.")
        return self._model

    @property
    def chroma_client(self) -> chromadb.PersistentClient:
        if self._chroma_client is None:
            os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIRECTORY,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._chroma_client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.chroma_client.get_or_create_collection(
                name="documind_vectors",
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings for a list of texts.
        """
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def add_chunks(
        self,
        document_id: int,
        user_id: int,
        filename: str,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """
        Generates embeddings for chunks and upserts them to ChromaDB.
        """
        if not chunks:
            return 0

        texts = [c["content"] for c in chunks]
        embeddings = self.embed_texts(texts)

        ids = [f"doc_{document_id}_chunk_{c['id']}" for c in chunks]
        metadatas = [
            {
                "document_id": int(document_id),
                "chunk_id": int(c["id"]),
                "user_id": int(user_id),
                "filename": str(filename),
                "page_number": int(c["page_number"]),
                "section": str(c.get("section") or f"Page {c['page_number']}"),
                "chunk_index": int(c["chunk_index"])
            }
            for c in chunks
        ]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        logger.info(f"Indexed {len(chunks)} chunks for document_id={document_id} into ChromaDB")
        return len(chunks)

    def query_similar(
        self,
        user_id: int,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k most semantically relevant chunks for a user query.
        """
        if not query.strip():
            return []

        query_embedding = self.embed_texts([query])[0]

        # Construct metadata filter
        where_filter: Dict[str, Any] = {"user_id": int(user_id)}
        if document_ids and len(document_ids) > 0:
            if len(document_ids) == 1:
                where_filter = {
                    "$and": [
                        {"user_id": int(user_id)},
                        {"document_id": int(document_ids[0])}
                    ]
                }
            else:
                where_filter = {
                    "$and": [
                        {"user_id": int(user_id)},
                        {"document_id": {"$in": [int(d) for d in document_ids]}}
                    ]
                }

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        formatted_results = []
        if results and results.get("ids") and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                doc_text = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if "distances" in results and results["distances"] else 0.0
                
                # Cosine distance to similarity score
                similarity = max(0.0, min(1.0, 1.0 - distance))

                formatted_results.append({
                    "chunk_id": metadata.get("chunk_id"),
                    "document_id": metadata.get("document_id"),
                    "filename": metadata.get("filename"),
                    "page_number": metadata.get("page_number", 1),
                    "section": metadata.get("section", ""),
                    "content": doc_text,
                    "relevance_score": round(similarity, 4)
                })

        return formatted_results

    def delete_document(self, document_id: int) -> None:
        """
        Removes all vectors associated with a document_id from ChromaDB.
        """
        try:
            self.collection.delete(
                where={"document_id": int(document_id)}
            )
            logger.info(f"Deleted vector chunks for document_id={document_id} from ChromaDB")
        except Exception as e:
            logger.warning(f"Error deleting vectors for document {document_id}: {e}")

embedding_service = EmbeddingService()

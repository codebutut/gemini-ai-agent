import logging
import os
from typing import Any, List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Handles persistent vector storage and semantic search using ChromaDB.
    """

    def __init__(self, persist_directory: str = ".chroma_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(allow_reset=True)
        )
        # Using default embedding function (SentenceTransformer)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="project_knowledge",
            embedding_function=self.embedding_function
        )

    def add_documents(self, documents: List[str], metadatas: List[dict], ids: List[str]):
        """Adds documents to the vector store."""
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to ChromaDB.")
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")

    def query(self, query_text: str, n_results: int = 5) -> dict:
        """Performs a semantic search."""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {"documents": [], "metadatas": [], "ids": []}

    def delete_collection(self):
        """Deletes the current collection."""
        self.client.delete_collection("project_knowledge")
        self.collection = self.client.get_or_create_collection(
            name="project_knowledge",
            embedding_function=self.embedding_function
        )

    def get_count(self) -> int:
        """Returns the number of items in the collection."""
        return self.collection.count()

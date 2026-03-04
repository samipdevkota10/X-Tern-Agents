"""RAG (Retrieval Augmented Generation) module using Chroma vector database."""

from app.rag.knowledge_base import KnowledgeBase, get_knowledge_base

__all__ = ["KnowledgeBase", "get_knowledge_base"]

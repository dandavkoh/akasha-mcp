"""
NAS Search Tool for MCP

This tool implements a production-grade Retrieval Augmented Generation (RAG)
retrieval pipeline for searching documents indexed from a NAS.

Pipeline overview:

User Query
    ↓
Embedding Search (Chroma)
    ↓
MMR Diversification
    ↓
Cross-Encoder Reranking
    ↓
Top-K Context Extraction
    ↓
Structured Snippet Response with Citations

The design ensures:
- High retrieval accuracy
- Good result diversity
- Efficient model loading
- Stable performance in long-running MCP servers
"""

from pathlib import Path
from typing import List, Tuple

import torch

from mcp.server.fastmcp import FastMCP

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma

from sentence_transformers import CrossEncoder


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

# Location of the persistent Chroma vector index
CHROMA_PERSIST_DIR = Path("/app/chroma_index")

# Embedding model used during indexing
EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# Cross encoder model used for reranking
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Retrieval configuration
INITIAL_RETRIEVAL_K = 30   # how many candidates to fetch from vector DB
MMR_TOP_K = 10             # how many documents after diversification
FINAL_TOP_K = 5            # final number returned after reranking

# Snippet length returned to the LLM/user
MAX_SNIPPET_LENGTH = 1000


# ------------------------------------------------------------------------------
# Global singletons (loaded once for performance)
# ------------------------------------------------------------------------------

_embedding_model = None
_vectordb = None
_reranker = None


# ------------------------------------------------------------------------------
# Model Initialization
# ------------------------------------------------------------------------------

def get_embedding_model():
    """
    Load the embedding model once and reuse it across tool calls.
    """
    global _embedding_model

    if _embedding_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

        _embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )

    return _embedding_model


def get_vectordb():
    """
    Load the persistent Chroma vector database.
    """
    global _vectordb

    if _vectordb is None:
        if not CHROMA_PERSIST_DIR.exists():
            raise RuntimeError(
                "Chroma index not found. Run the indexing pipeline first."
            )

        _vectordb = Chroma(
            persist_directory=str(CHROMA_PERSIST_DIR),
            embedding_function=get_embedding_model(),
        )

    return _vectordb


def get_reranker():
    """
    Load the cross-encoder reranker model.

    Cross-encoders evaluate (query, document) pairs jointly
    and produce a much more accurate relevance score than
    embedding similarity alone.
    """
    global _reranker

    if _reranker is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _reranker = CrossEncoder(RERANKER_MODEL_NAME, device=device)

    return _reranker


# ------------------------------------------------------------------------------
# Retrieval Pipeline
# ------------------------------------------------------------------------------

def retrieve_documents(query: str) -> List[Document]:
    """
    Perform initial vector retrieval with MMR diversification.

    MMR (Max Marginal Relevance) ensures the results are not all
    from the same paragraph or document.
    """

    vectordb = get_vectordb()

    docs = vectordb.max_marginal_relevance_search(
        query=query,
        k=MMR_TOP_K,
        fetch_k=INITIAL_RETRIEVAL_K,
    )

    return docs


def rerank_documents(query: str, docs: List[Document]) -> List[Tuple[Document, float]]:
    """
    Re-rank retrieved documents using a cross-encoder model.

    The cross-encoder evaluates the full query-document pair,
    which dramatically improves relevance ranking.
    """

    reranker = get_reranker()

    pairs = [(query, d.page_content) for d in docs]

    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(docs, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    return ranked


# ------------------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------------------

def format_results(results: List[Tuple[Document, float]]) -> str:
    """
    Format the final retrieved documents into readable snippets
    with citations and metadata.
    """

    snippets = []

    for doc, score in results[:FINAL_TOP_K]:

        filename = doc.metadata.get("filename", "Unknown file")
        relative_path = doc.metadata.get("relative_path", "Unknown path")
        chunk_index = doc.metadata.get("chunk_index", 0)

        snippet = doc.page_content[:MAX_SNIPPET_LENGTH].strip()

        snippets.append(
            (
                f"📄 File: {filename}\n"
                f"📂 Path: {relative_path}\n"
                f"🔢 Chunk: {chunk_index}\n"
                f"⭐ Relevance: {score:.3f}\n\n"
                f"{snippet}..."
            )
        )

    return "\n\n---\n\n".join(snippets)


# ------------------------------------------------------------------------------
# MCP Tool Registration
# ------------------------------------------------------------------------------

def register(mcp: FastMCP):
    """
    Register the NAS search tool with the MCP server.
    """

    @mcp.tool()
    def search_nas(query: str) -> str:
        """
        Search indexed NAS documents using a professional RAG retrieval pipeline.

        Steps performed:
        1. Vector search with embeddings
        2. MMR diversification
        3. Cross-encoder reranking
        4. Return structured snippets with citations

        Args:
            query: Natural language search query

        Returns:
            Formatted search results with document citations.
        """

        try:

            vectordb = get_vectordb()

            if vectordb._collection.count() == 0:
                return "❌ The vector index is empty. Please run the indexing pipeline."

            # Step 1: retrieve candidate documents
            docs = retrieve_documents(query)

            if not docs:
                return "No relevant information found."

            # Step 2: rerank results
            ranked = rerank_documents(query, docs)

            # Step 3: format output
            return format_results(ranked)

        except Exception as e:
            return f"❌ Search failed: {str(e)}"
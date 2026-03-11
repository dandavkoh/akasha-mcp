"""
NAS Search Tool for MCP

This tool provides high quality retrieval over internal company
documents stored on a NAS. It is designed for use with MCP.

Pipeline:

Queries
  ↓
Embedding Search (Chroma)
  ↓
MMR Diversification
  ↓
Cross-Encoder Reranking
  ↓
Top-K Context Extraction
  ↓
Structured Snippets with Citations

The system supports multi-query retrieval so the LLM can search
with different wordings of the same question.
"""

from pathlib import Path
from typing import List, Tuple
import torch

from mcp.server.fastmcp import FastMCP

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma

from sentence_transformers import CrossEncoder

from ldap3 import Server, Connection, ALL, NTLM


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
INITIAL_RETRIEVAL_K = 50   # how many candidates to fetch from vector DB
MMR_TOP_K = 15             # how many documents after diversification
FINAL_TOP_K = 5            # final number returned after reranking

MAX_SNIPPET_LENGTH = 1000

# LDAP/Active Directory configuration for ACL filtering
LDAP_SERVER = "192.168.136.3"
LDAP_PORT = 389
LDAP_USE_TLS = False
LDAP_APP_DN = "CN=Mai Ldap,OU=ServiceAccounts,OU=Users,OU=MyBusiness,DC=manner,DC=local"
LDAP_APP_PASSWORD = "ldap0815!"
LDAP_SEARCH_BASE = "OU=Employees,OU=SBSUsers,OU=Users,OU=MyBusiness,DC=manner,DC=local"


# ------------------------------------------------------------------------------
# Global singletons (loaded once for performance)
# ------------------------------------------------------------------------------

_embedding_model = None
_vectordb = None
_reranker = None


# -------------------------------------------------------------------------------
# Active Directory User Lookup and ACL Filtering
# -------------------------------------------------------------------------------
def get_ad_user(email: str):
    server = Server(LDAP_SERVER, port=LDAP_PORT, use_ssl=LDAP_USE_TLS, get_info=ALL)
    conn = Connection(server, user=LDAP_APP_DN, password=LDAP_APP_PASSWORD, authentication="SIMPLE", auto_bind=True)
    conn.search(
        search_base=LDAP_SEARCH_BASE,
        search_filter=f"(mail={email})",
        attributes=["distinguishedName", "mail", "memberOf", "sAMAccountName"]
    )
    if conn.entries:
        return conn.entries[0]
    return None


def filter_docs_by_acl(docs: List[Document], ad_user) -> List[Document]:
    allowed_docs = []
    user_id = str(ad_user.sAMAccountName) if ad_user else None
    user_groups = set(str(g) for g in ad_user.memberOf) if ad_user else set()

    for doc in docs:
        acl_users = set(doc.metadata.get("acl_users", []))
        acl_groups = set(doc.metadata.get("acl_groups", []))

        # remove "none" placeholder if present
        acl_users.discard("none")
        acl_groups.discard("none")

        # if ACL empty, allow all
        if not acl_users and not acl_groups:
            allowed_docs.append(doc)
            continue

        # Check if user id is in ACL users or if any of the user's groups are in ACL groups
        if (user_id and user_id in acl_users) or (user_groups & acl_groups):
            allowed_docs.append(doc)
    
    return allowed_docs


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
            raise RuntimeError("Chroma index not found. Run the indexing pipeline.")

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

def retrieve_documents_multi(queries: List[str]) -> List[Document]:
    """
    Perform initial vector retrieval with MMR diversification.

    MMR (Max Marginal Relevance) ensures the results are not all
    from the same paragraph or document.
    """

    vectordb = get_vectordb()
    all_docs = []

    for query in queries:

        docs = vectordb.max_marginal_relevance_search(
            query=query,
            k=MMR_TOP_K,
            fetch_k=INITIAL_RETRIEVAL_K,
        )

        all_docs.extend(docs)

    # deduplicate by chunk_id
    seen = set()
    unique_docs = []

    for doc in all_docs:
        cid = doc.metadata.get("chunk_id")

        if cid not in seen:
            seen.add(cid)
            unique_docs.append(doc)

    return unique_docs


# ------------------------------------------------------------------------------
# Reranking
# ------------------------------------------------------------------------------

def rerank_documents(query: str, docs: List[Document]) -> List[Tuple[Document, float]]:
    """
    Re-rank retrieved documents using a cross-encoder model.

    The cross-encoder evaluates the full query-document pair,
    which dramatically improves relevance ranking.
    """

    reranker = get_reranker()

    pairs = [(query, d.page_content) for d in docs]

    scores = reranker.predict(
        pairs,
        batch_size=32
    )

    ranked = sorted(
        zip(docs, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    return ranked


# ------------------------------------------------------------------------------
# Snippet extraction
# ------------------------------------------------------------------------------

def centered_snippet(text: str, query: str, max_len: int):
    """
    Return a snippet centered around the first occurrence of the query.

    If the query is not found, the beginning of the text is returned.
    The snippet is truncated to max_len characters and may include
    "..." when text is omitted.
    """

    lower = text.lower()
    q = query.lower()

    idx = lower.find(q)

    if idx == -1:
        return text[:max_len]

    start = max(idx - max_len // 2, 0)
    end = start + max_len

    snippet = text[start:end]

    if start > 0:
        snippet = "..." + snippet

    if end < len(text):
        snippet = snippet + "..."

    return snippet.strip()


# ------------------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------------------

def format_results(query: str, results: List[Tuple[Document, float]]) -> str:
    """
    Format reranked documents into readable snippets with metadata.

    Each result includes file information, relevance score, and a
    query-centered text snippet.
    """

    snippets = []

    for doc, score in results[:FINAL_TOP_K]:

        filename = doc.metadata.get("filename", "Unknown file")
        relative_path = doc.metadata.get("relative_path", "Unknown path")
        chunk_index = doc.metadata.get("chunk_index", 0)
        content_type = doc.metadata.get("content_type", "text")

        snippet = centered_snippet(
            doc.page_content,
            query,
            MAX_SNIPPET_LENGTH
        )

        snippets.append(
            (
                f"📄 File: {filename}\n"
                f"📂 Path: {relative_path}\n"
                f"🔢 Chunk: {chunk_index}\n"
                f"📑 Type: {content_type}\n"
                f"⭐ Relevance: {score:.3f}\n\n"
                f"{snippet}"
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
    def search_nas(queries: List[str], top_k: int = 5, user_context: dict = None) -> str:
        """
        Search internal company documents stored on the NAS.

        ACL-filtered: user only sees documents they are allowed to.

        This includes all types of internal information such as:

        - company policies and procedures
        - project documentation
        - internal reports
        - contracts and agreements
        - operational guidelines
        - technical documentation
        - audit and compliance documentation
        - management reports and meeting notes
        - and more...

        You may provide multiple search queries to explore different
        phrasings of the same question.

        Example:
        ["audit results 2026", "internal audit findings"]

        You can call this tool multiple times with different queries
        to gather additional information.

        Args:
            queries: List of search queries
            top_k: Number of results to return

        Returns:
            Relevant document snippets with file references.
        """

        user_email = user_context.get("user_email")

        try:

            vectordb = get_vectordb()

            if vectordb._collection.count() == 0:
                return "❌ The vector index is empty. Please run the indexing pipeline."

            # Step 1: ldap lookup to get user info and permissions
            ad_user = get_ad_user(user_email)

            # Step 2: retrieve candidate documents
            docs = retrieve_documents_multi(queries)
            if not docs:
                return "No relevant information found."
            
            # Step 3: filter by ACLs
            docs = filter_docs_by_acl(docs, ad_user)
            if not docs:
                return "No documents available for your user/group."

            # Step 4: rerank results
            ranked = rerank_documents(queries[0], docs)

            # Step 5: format output
            return format_results(queries[0], ranked[:top_k])

        except Exception as e:
            return f"❌ Search failed: {str(e)}"


    @mcp.tool()
    def open_document(path: str, user_context: dict = None) -> str:
        """
        Open a document from the NAS and return its indexed text.

        Use this after search_nas if you want to read the document
        in more detail.

        Args:
            path: relative_path of the document

        Returns:
            Larger excerpt of the document contents.
        """

        try:

            vectordb = get_vectordb()

            docs = vectordb.similarity_search(
                query=path,
                k=20,
                filter={"relative_path": path}
            )

            if not docs:
                return "Document not found."

            text = "\n\n".join([d.page_content for d in docs])

            return text[:10000]

        except Exception as e:
            return f"❌ Failed to open document: {str(e)}"
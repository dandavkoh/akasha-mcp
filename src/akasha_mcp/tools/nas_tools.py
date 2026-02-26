from mcp.server.fastmcp import FastMCP
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


# Path to the Chroma Index (must be the same as used in `chroma_index/index_nas.py`)
CHROMA_PERSIST_DIR = Path("/app/chroma_index")

# Embedding Model (must be the same as used during indexing)
EMBED_MODEL = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def register(mcp: FastMCP):
    @mcp.tool()
    def search_nas(query: str) -> str:
        """
        Search for relevant information in NAS documents using RAG.
        Note: Documents must be indexed first using `index-chroma` command.
        """
        # Load the existing Chroma Index
        if not CHROMA_PERSIST_DIR.exists():
            return "❌ No index found. Please run `index-chroma` first to index the documents."
        
        vectordb = Chroma(
            persist_directory=str(CHROMA_PERSIST_DIR),
            embedding_function=EMBED_MODEL
        )
        
        # Check if the index contains data
        if len(vectordb.get()["ids"]) == 0:
            return "❌ The index is empty. Please run `index-chroma` first to index the documents."

        # Search for top 3 similar chunks
        results = vectordb.similarity_search(query, k=3)

        # Return combined results
        if not results:
            return "No relevant information found."

        answer_snippets = []
        for r in results:
            src = r.metadata.get("source", "Unknown")
            snippet = r.page_content[:300]  # only first snippet
            answer_snippets.append(f"Source: {src}\n{snippet}...")

        return "\n\n".join(answer_snippets)
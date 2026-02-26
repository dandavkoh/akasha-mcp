#!/usr/bin/env python3
"""
Script for one-time indexing of NAS documents in Chroma.
Can be executed via CLI: `index-chroma`
"""
from pathlib import Path
from docling.document_converter import DocumentConverter

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Path to NAS (Docker Volume or mounted NAS)
NAS_PATH = Path("/mnt/nas_docs")

# Path to the Chroma Index (must be the same as used in `nas_tools.py`)
CHROMA_PERSIST_DIR = Path("/app/chroma_index")

# Embedding Model (must be the same as used in `nas_tools.py`)
EMBED_MODEL = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Document Text Splitter
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)


def main():
    """Main function for indexing NAS documents."""
    print(f"🔍 Starting indexing of documents in {NAS_PATH}...")
    
    if not NAS_PATH.exists():
        print(f"❌ Error: NAS path {NAS_PATH} does not exist!")
        return
    
    # Load and parse documents
    all_texts = []
    converter = DocumentConverter()
    
    file_count = 0
    for file_path in NAS_PATH.glob("**/*"):
        if file_path.suffix.lower() in [".pdf", ".docx", ".txt", ".md"]:
            file_count += 1
            try:
                print(f"  📄 Processing: {file_path.name}")
                result = converter.convert(str(file_path))
                text = result.document.export_to_markdown()
                all_texts.append(Document(page_content=text, metadata={"source": str(file_path)}))
            except Exception as e:
                print(f"  ⚠️  Error parsing {file_path}: {e}")
    
    if not all_texts:
        print("❌ No documents found.")
        return
    
    print(f"✅ {len(all_texts)} documents successfully processed.")
    
    # Split text into chunks
    print("✂️  Splitting documents into chunks...")
    chunks = []
    for doc in all_texts:
        chunk_texts = TEXT_SPLITTER.split_text(doc.page_content)
        for chunk in chunk_texts:
            chunks.append(Document(page_content=chunk, metadata=doc.metadata))
    
    print(f"✅ {len(chunks)} chunks created.")
    
    # Create Chroma Vectorstore
    print(f"💾 Creating Chroma Index in {CHROMA_PERSIST_DIR}...")
    vectordb = Chroma(
        persist_directory=str(CHROMA_PERSIST_DIR),
        embedding_function=EMBED_MODEL
    )
    
    # Delete old data and add new data
    existing_ids = vectordb.get()["ids"]
    if existing_ids:
        print(f"🗑️  Deleting {len(existing_ids)} old entries...")
        vectordb.delete(ids=existing_ids)
    
    print("📝 Adding new chunks to the index...")
    vectordb.add_documents(chunks)
    vectordb.persist()
    
    print("✅ Indexing completed successfully!")
    print(f"📊 A total of {len(chunks)} chunks from {len(all_texts)} documents have been indexed.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Enhanced NAS document indexing with improved chunking and metadata."""

import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

from docling.document_converter import DocumentConverter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm
import torch

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
NAS_PATH = Path("/mnt/nas_docs")
CHROMA_PERSIST_DIR = Path("/app/chroma_index")
METADATA_CACHE = Path("/app/metadata_cache.json")

# Improved embedding model
EMBED_MODEL = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# Optimized text splitter
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", "", "\t"],
    length_function=len,
)

def generate_doc_id(content: str, metadata: dict) -> str:
    """Generate unique ID for document chunk."""
    unique_str = f"{metadata.get('source', '')}{content[:100]}"
    return hashlib.md5(unique_str.encode()).hexdigest()

def enrich_metadata(file_path: Path) -> Dict[str, Any]:
    """Enhanced metadata extraction."""
    import mimetypes
    
    stats = file_path.stat()
    
    metadata = {
        "source": str(file_path),
        "filename": file_path.name,
        "file_type": file_path.suffix.lower(),
        "mime_type": mimetypes.guess_type(str(file_path))[0],
        "file_size": stats.st_size,
        "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        "relative_path": str(file_path.relative_to(NAS_PATH)),
        "directory": str(file_path.parent.relative_to(NAS_PATH)),
    }
    
    # Add document category based on directory structure
    path_parts = metadata["relative_path"].split("/")
    if len(path_parts) > 1:
        metadata["category"] = path_parts[0]
    
    return metadata

def process_document(file_path: Path, converter: DocumentConverter) -> List[Document]:
    """Process single document with enhanced error handling."""
    chunks = []
    
    try:
        logger.info(f"Processing: {file_path.name}")
        
        # Convert document
        result = converter.convert(str(file_path))
        text = result.document.export_to_markdown()
        
        # Get metadata
        metadata = enrich_metadata(file_path)
        
        # Create base document
        doc = Document(page_content=text, metadata=metadata)
        
        # Smart chunking
        chunk_texts = TEXT_SPLITTER.split_text(text)
        
        for i, chunk_text in enumerate(chunk_texts):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunk_texts)
            #chunk_metadata["chunk_id"] = generate_doc_id(chunk_text, metadata)
            chunk_metadata["chunk_id"] = f"{metadata['filename']}_chunk_{i}"
            
            chunks.append(Document(
                page_content=chunk_text, 
                metadata=chunk_metadata
            ))
            
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
    
    return chunks

def main():
    """Enhanced main function with progress tracking."""
    print("🚀 Enhanced NAS Document Indexing")
    print("=" * 50)
    
    if not NAS_PATH.exists():
        logger.error(f"NAS path {NAS_PATH} does not exist!")
        return
    
    # Collect files
    supported_formats = {".pdf", ".docx", ".txt", ".md", ".doc", ".rtf"}
    files = [f for f in NAS_PATH.glob("**/*") 
             if f.suffix.lower() in supported_formats]
    
    print(f"📁 Found {len(files)} documents to process")
    
    if not files:
        logger.warning("No documents found.")
        return
    
    # Initialize converter
    converter = DocumentConverter()
    
    # Process documents with progress bar
    all_chunks = []
    
    for file_path in tqdm(files, desc="Processing documents"):
        chunks = process_document(file_path, converter)
        all_chunks.extend(chunks)
    
    print(f"\n✅ Generated {len(all_chunks)} chunks from {len(files)} documents")
    
    # Create/Update Chroma index
    print(f"\n💾 Updating Chroma index...")
    
    vectordb = Chroma(
        persist_directory=str(CHROMA_PERSIST_DIR),
        embedding_function=EMBED_MODEL,
        collection_metadata={"hnsw:space": "cosine"}  # Optimized for similarity
    )
    
    # Clear existing data
    existing_ids = vectordb.get()["ids"]
    if existing_ids:
        print(f"🗑️  Removing {len(existing_ids)} old entries...")
        vectordb.delete(ids=existing_ids)
    
    # Add documents in batches for better performance
    batch_size = 100
    for i in tqdm(range(0, len(all_chunks), batch_size), desc="Indexing chunks"):
        batch = all_chunks[i:i+batch_size]
        
        # Add with IDs for deduplication
        ids = [chunk.metadata["chunk_id"] for chunk in batch]
        vectordb.add_documents(documents=batch, ids=ids)
    
    # Save metadata cache for analysis
    metadata_summary = {
        "indexed_at": datetime.now().isoformat(),
        "total_documents": len(files),
        "total_chunks": len(all_chunks),
        "files": [str(f) for f in files],
        "statistics": {
            "by_type": {},
            "by_directory": {}
        }
    }
    
    # Calculate statistics
    for chunk in all_chunks:
        file_type = chunk.metadata.get("file_type", "unknown")
        directory = chunk.metadata.get("directory", "root")
        
        metadata_summary["statistics"]["by_type"][file_type] = \
            metadata_summary["statistics"]["by_type"].get(file_type, 0) + 1
        
        metadata_summary["statistics"]["by_directory"][directory] = \
            metadata_summary["statistics"]["by_directory"].get(directory, 0) + 1
    
    with open(METADATA_CACHE, "w") as f:
        json.dump(metadata_summary, f, indent=2)
    
    print("\n" + "=" * 50)
    print("✅ Indexing completed successfully!")
    print(f"📊 Statistics:")
    print(f"   - Documents: {len(files)}")
    print(f"   - Chunks: {len(all_chunks)}")
    print(f"   - Avg chunks/doc: {len(all_chunks)/len(files):.1f}")
    print(f"   - Index location: {CHROMA_PERSIST_DIR}")
    print(f"   - Metadata cache: {METADATA_CACHE}")

if __name__ == "__main__":
    main()

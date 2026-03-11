#!/usr/bin/env python3
"""Enhanced NAS document indexing with improved chunking and metadata."""

import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging
import subprocess

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

SUPPORTED_FORMATS = {".pdf", ".docx", ".txt", ".md", ".doc", ".rtf"}

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

def get_file_acl(file_path: Path) -> Dict[str, List[str]]:
    """
    Extract readable users and groups from filesystem ACL.
    Works on Linux/NFS/Samba/WSL mounts.
    """
    users = []
    groups = []

    try:
        result = subprocess.run(
            ["getfacl", "-cp", str(file_path)],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("user:"):
                parts = line.split(":")
                if len(parts) >= 3 and "r" in parts[2]:
                    if parts[1]:  # skip empty
                        users.append(parts[1])
            if line.startswith("group:"):
                parts = line.split(":")
                if len(parts) >= 3 and "r" in parts[2]:
                    if parts[1]:
                        groups.append(parts[1])
    except Exception as e:
        logger.warning(f"Could not read ACL for {file_path}: {e}")

    return {"acl_users": users, "acl_groups": groups}

def generate_doc_id(content: str, metadata: dict, chunk_index: int) -> str:
    """Generate unique ID for document chunk."""
    unique_str = (
        f"{metadata['relative_path']}"
        f"{metadata['modified_at']}"
        f"{chunk_index}"
        f"{content[:200]}"
    )
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
    
    # Add ACL info
    acl = get_file_acl(file_path)
    acl["acl_users"] = acl["acl_users"] or ["none"]
    acl["acl_groups"] = acl["acl_groups"] or ["none"]
    
    metadata.update(acl)
    
    return metadata

def process_document(file_path: Path, converter: DocumentConverter) -> List[Document]:
    """Process single document with enhanced error handling."""
    chunks = []
    
    try:
        logger.info(f"Processing: {file_path.name}")
        
        # Convert document
        result = converter.convert(str(file_path))
        doc = result.document
        text = doc.export_to_markdown()
        
        # Get metadata
        metadata = enrich_metadata(file_path)

        # ---------------------------
        # Process tables (if any)
        # ---------------------------
        for t_idx, table in enumerate(getattr(doc, "tables", [])):

            try:
                # --- Raw table chunk ---
                raw_md = table.export_to_markdown(doc=doc)
                raw_metadata = metadata.copy()
                raw_metadata.update({
                    "content_type": "table_raw",
                    "table_index": t_idx,
                    "chunk_id": f"{metadata['filename']}_table_raw_{t_idx}"
                })
                chunks.append(Document(page_content=raw_md, metadata=raw_metadata))

                # --- Simple table summary ---
                # Extrahiere ersten Text aus Markdown als Header-Summary
                first_line = raw_md.splitlines()[0] if raw_md else "Table"
                summary_text = f"Table summary: {first_line}"
                summary_metadata = metadata.copy()
                summary_metadata.update({
                    "content_type": "table_summary",
                    "table_index": t_idx,
                    "chunk_id": f"{metadata['filename']}_table_summary_{t_idx}"
                })
                chunks.append(Document(page_content=summary_text, metadata=summary_metadata))

                # --- Row chunks ---
                # Split markdown rows by line, ignoriere header
                rows = raw_md.splitlines()[1:] if len(raw_md.splitlines()) > 1 else []
                for r_idx, row in enumerate(rows):
                    row_text = row.strip()
                    if not row_text:
                        continue
                    row_metadata = metadata.copy()
                    row_metadata.update({
                        "content_type": "table_row",
                        "table_index": t_idx,
                        "row_index": r_idx,
                        "chunk_id": f"{metadata['filename']}_table_{t_idx}_row_{r_idx}"
                    })
                    chunks.append(Document(page_content=row_text, metadata=row_metadata))

            except Exception as e:
                logger.warning(f"Table export failed: {e}")
        
        # ---------------------------
        # Process normal text
        # ---------------------------
        chunk_texts = TEXT_SPLITTER.split_text(text)

        for i, chunk_text in enumerate(chunk_texts):

            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "content_type": "text",
                "chunk_index": i,
                "total_chunks": len(chunk_texts),
                "chunk_id": generate_doc_id(chunk_text, metadata, i)
            })

            chunks.append(
                Document(
                    page_content=chunk_text,
                    metadata=chunk_metadata
                )
            )
            
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
    files = [f for f in NAS_PATH.glob("**/*") 
             if f.suffix.lower() in SUPPORTED_FORMATS]
    
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
    existing = vectordb.get()
    existing_ids = existing.get("ids", [])
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

#!/usr/bin/env python3
"""
Load embeddings into ChromaDB for local vector storage.
This replaces Vertex AI Vector Search for small datasets.
"""

import os
import json
import chromadb
from pathlib import Path
from chromadb.config import Settings

def load_embeddings_to_chromadb(
    embeddings_file: str,
    collection_name: str = "uplifted_mascot",
    persist_directory: str = "./chroma_db"
):
    """
    Load embeddings from JSON file into ChromaDB.
    
    Args:
        embeddings_file: JSON file with embeddings (from create_embeddings.py)
        collection_name: Name for the ChromaDB collection
        persist_directory: Directory to persist ChromaDB data
    """
    # Load embeddings
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        embeddings_data = json.load(f)
    
    print(f"Loading {len(embeddings_data)} embeddings into ChromaDB...")
    
    # Initialize ChromaDB client (persistent mode)
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get or create collection
    # ChromaDB will automatically handle the embeddings dimension
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Uplifted Mascot knowledge base embeddings"}
    )
    
    # Prepare data for ChromaDB
    # ChromaDB expects: ids, embeddings, documents, metadatas
    ids = []
    embeddings = []
    documents = []
    metadatas = []
    
    for item in embeddings_data:
        # Create unique ID from metadata
        file_path = item.get("metadata", {}).get("file_path", "")
        chunk_index = item.get("metadata", {}).get("chunk_index", "")
        doc_id = f"{file_path}:{chunk_index}"
        
        ids.append(doc_id)
        embeddings.append(item["embedding"])
        documents.append(item["text"])
        
        # Store metadata (ChromaDB requires metadata to be dict with string values)
        metadata = {
            "file_path": str(file_path),
            "chunk_index": str(chunk_index),
            "filename": str(item.get("metadata", {}).get("file_path", "").replace("\\", "/").split("/")[-1])
        }
        metadatas.append(metadata)
    
    # Add to collection (ChromaDB handles batching internally)
    print("Adding embeddings to ChromaDB...")
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    
    print(f"✓ Successfully loaded {len(ids)} embeddings into ChromaDB")
    print(f"  Collection: {collection_name}")
    print(f"  Database location: {Path(persist_directory).absolute()}")
    
    # Verify
    count = collection.count()
    print(f"  Total documents in collection: {count}")
    
    return collection

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python load_chromadb.py <embeddings_file> [collection_name] [persist_directory]")
        print("\nExample (from workspace root):")
        print("  python scripts/load_chromadb.py scripts/embeddings-array.json")
        print("  python scripts/load_chromadb.py scripts/embeddings-array.json my_collection ./chroma_db")
        print("\nNote: Use embeddings-array.json (JSON array format), not embeddings.json (JSONL format)")
        sys.exit(1)
    
    embeddings_file = sys.argv[1]
    collection_name = sys.argv[2] if len(sys.argv) > 2 else "uplifted_mascot"
    persist_directory = sys.argv[3] if len(sys.argv) > 3 else "./chroma_db"
    
    if not os.path.exists(embeddings_file):
        print(f"Error: Embeddings file not found: {embeddings_file}")
        sys.exit(1)
    
    load_embeddings_to_chromadb(embeddings_file, collection_name, persist_directory)


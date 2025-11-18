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
    persist_directory: str = "./chroma_db",
    chroma_host: str = None,
    chroma_port: int = 8000
):
    """
    Load embeddings from JSON file into ChromaDB.
    
    Args:
        embeddings_file: JSON file with embeddings (from create_embeddings.py)
        collection_name: Name for the ChromaDB collection
        persist_directory: Directory to persist ChromaDB data (for local mode)
        chroma_host: ChromaDB service hostname (for HTTP client mode). If set, uses HTTP client.
        chroma_port: ChromaDB service port (default: 8000)
    """
    # Load embeddings
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        embeddings_data = json.load(f)
    
    print(f"Loading {len(embeddings_data)} embeddings into ChromaDB...")
    
    # Initialize ChromaDB client (HTTP mode if host provided, otherwise persistent mode)
    if chroma_host:
        print(f"Connecting to ChromaDB service at {chroma_host}:{chroma_port}")
        client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(anonymized_telemetry=False)
        )
    else:
        print(f"Using local ChromaDB at {persist_directory}")
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
    if chroma_host:
        print(f"  ChromaDB service: {chroma_host}:{chroma_port}")
    else:
        print(f"  Database location: {Path(persist_directory).absolute()}")
    
    # Verify
    count = collection.count()
    print(f"  Total documents in collection: {count}")
    
    return collection

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python load_chromadb.py <embeddings_file> [collection_name] [persist_directory|chroma_host:port]")
        print("\nExamples:")
        print("  # Local mode (persistent client):")
        print("  python scripts/load_chromadb.py scripts/embeddings-array.json")
        print("  python scripts/load_chromadb.py scripts/embeddings-array.json my_collection ./chroma_db")
        print("\n  # HTTP mode (connect to ChromaDB service):")
        print("  CHROMA_HOST=chromadb CHROMA_PORT=8000 python scripts/load_chromadb.py scripts/embeddings-array.json")
        print("  python scripts/load_chromadb.py scripts/embeddings-array.json my_collection http://chromadb:8000")
        print("\nNote: Use embeddings-array.json (JSON array format), not embeddings.json (JSONL format)")
        sys.exit(1)
    
    embeddings_file = sys.argv[1]
    collection_name = sys.argv[2] if len(sys.argv) > 2 else "uplifted_mascot"
    
    # Check if third arg is a URL (http://host:port) or a directory path
    chroma_host = None
    chroma_port = 8000
    persist_directory = "./chroma_db"
    
    if len(sys.argv) > 3:
        third_arg = sys.argv[3]
        # Check if it's a URL
        if third_arg.startswith("http://") or third_arg.startswith("https://"):
            # Parse URL
            url = third_arg.replace("http://", "").replace("https://", "")
            if ":" in url:
                chroma_host, port_str = url.split(":", 1)
                chroma_port = int(port_str)
            else:
                chroma_host = url
        elif ":" in third_arg and not os.path.exists(third_arg):
            # Looks like host:port format
            chroma_host, port_str = third_arg.split(":", 1)
            chroma_port = int(port_str)
        else:
            # It's a directory path
            persist_directory = third_arg
    
    # Also check environment variables (takes precedence)
    chroma_host = os.getenv("CHROMA_HOST", chroma_host)
    if os.getenv("CHROMA_PORT"):
        chroma_port = int(os.getenv("CHROMA_PORT"))
    
    if not os.path.exists(embeddings_file):
        print(f"Error: Embeddings file not found: {embeddings_file}")
        sys.exit(1)
    
    load_embeddings_to_chromadb(embeddings_file, collection_name, persist_directory, chroma_host, chroma_port)


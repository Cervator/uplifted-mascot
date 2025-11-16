#!/usr/bin/env python3
"""
Simple script to validate ChromaDB collection and show sample data.
"""

import chromadb
from pathlib import Path
from chromadb.config import Settings

def validate_chromadb(
    collection_name: str = "uplifted_mascot",
    persist_directory: str = "./chroma_db"
):
    """
    Validate ChromaDB collection and show sample data.
    """
    # Try multiple paths for the database
    persist_paths = [
        Path(persist_directory),
        Path(__file__).parent.parent / persist_directory,
        Path("chroma_db"),
        Path("../chroma_db"),
    ]
    
    client = None
    for persist_path in persist_paths:
        if persist_path.exists():
            try:
                client = chromadb.PersistentClient(
                    path=str(persist_path),
                    settings=Settings(anonymized_telemetry=False)
                )
                print(f"✓ Connected to ChromaDB at: {persist_path.absolute()}")
                break
            except Exception as e:
                continue
    
    if client is None:
        print(f"✗ ChromaDB not found in any of these locations:")
        for path in persist_paths:
            print(f"  - {path.absolute()}")
        return False
    
    # Get collection
    try:
        collection = client.get_collection(name=collection_name)
        count = collection.count()
        print(f"✓ Collection '{collection_name}' found")
        print(f"  Total documents: {count}")
        
        # Get a few sample documents
        if count > 0:
            print("\nSample documents (first 3):")
            results = collection.get(limit=3, include=["documents", "metadatas"])
            
            for i, (doc_id, doc_text, metadata) in enumerate(zip(
                results["ids"],
                results["documents"],
                results["metadatas"]
            ), 1):
                print(f"\n  {i}. ID: {doc_id}")
                print(f"     File: {metadata.get('filename', 'N/A')}")
                print(f"     Text preview: {doc_text[:100]}...")
        
        # Test a simple query
        if count > 0:
            print("\n✓ Testing query capability...")
            try:
                # Get a sample document to query against
                sample = collection.get(limit=1, include=["embeddings"])
                # Check if embeddings exist (check length, not the array itself)
                has_embeddings = "embeddings" in sample and len(sample["embeddings"]) > 0
                if has_embeddings:
                    query_result = collection.query(
                        query_embeddings=[sample["embeddings"][0]],
                        n_results=min(3, count),
                        include=["documents", "metadatas", "distances"]
                    )
                    # Check results safely
                    has_results = "ids" in query_result and len(query_result["ids"]) > 0 and len(query_result["ids"][0]) > 0
                    if has_results:
                        print(f"  Query returned {len(query_result['ids'][0])} results")
                        print("  ✓ Query test successful!")
                    else:
                        print("  ⚠ Query returned no results")
                else:
                    print("  ⚠ Could not get sample embedding for query test")
            except Exception as query_error:
                print(f"  ⚠ Query test failed: {query_error}")
                print("  (This is okay - ChromaDB is still loaded correctly)")
        
        print("\n✓ ChromaDB validation complete - ready to use!")
        return True
        
    except Exception as e:
        print(f"✗ Error accessing collection '{collection_name}': {e}")
        return False

if __name__ == "__main__":
    import sys
    
    collection_name = sys.argv[1] if len(sys.argv) > 1 else "uplifted_mascot"
    persist_directory = sys.argv[2] if len(sys.argv) > 2 else "./chroma_db"
    
    validate_chromadb(collection_name, persist_directory)


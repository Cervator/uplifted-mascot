#!/usr/bin/env python3
"""
Convert embeddings JSON to JSONL format for Vector Search.
"""

import json
from pathlib import Path

def convert_to_jsonl(embeddings_file: str, output_file: str):
    """
    Convert embeddings JSON to JSONL format.
    
    Format: Each line is a JSON object with:
    - id: Unique identifier
    - embedding: The vector
    - metadata: Additional data (restricts to string values)
    """
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        embeddings_data = json.load(f)
    
    print(f"Converting {len(embeddings_data)} embeddings to JSONL...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(embeddings_data):
            # Create unique ID
            file_path = item["metadata"]["file_path"]
            chunk_idx = item["metadata"]["chunk_index"]
            doc_id = f"{file_path}:{chunk_idx}"
            
            # Vector Search JSONL format
            jsonl_item = {
                "id": doc_id,
                "embedding": item["embedding"]
            }
            
            # Add metadata (must be strings)
            jsonl_item["metadata"] = {
                "file_path": str(item["metadata"]["file_path"]),
                "filename": str(item["metadata"]["filename"]),
                "chunk_index": str(item["metadata"]["chunk_index"]),
                "text": item["text"][:500]  # First 500 chars for reference
            }
            
            f.write(json.dumps(jsonl_item) + '\n')
    
    print(f"Converted to: {Path(output_file).absolute()}")
    print(f"Lines: {len(embeddings_data)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python convert_to_jsonl.py <embeddings_file> [output_file]")
        sys.exit(1)
    
    embeddings_file = sys.argv[1]
    # Default to .json extension (Vertex AI requires .json even for JSONL content)
    # This will be the final file uploaded to Vector Search
    output_file = sys.argv[2] if len(sys.argv) > 2 else "embeddings.json"
    
    convert_to_jsonl(embeddings_file, output_file)


#!/usr/bin/env python3
"""
Create embeddings for document chunks using Vertex AI.
"""

import os
import json
import time
from pathlib import Path
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

def create_embeddings(chunks_file: str, output_file: str = "embeddings-array.json"):
    """
    Create embeddings for all chunks.
    
    Args:
        chunks_file: JSON file with chunks (from process_docs.py)
        output_file: Output file for embeddings
    """
    # Initialize Vertex AI
    PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
    LOCATION = "us-east1"  # Change if needed
    
    if not PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID environment variable not set")
    
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    
    # Load chunks
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)
    
    print(f"Creating embeddings for {len(chunks_data)} chunks...")
    
    # Initialize embedding model
    # Try text-embedding-004 first (available in us-east1), fall back to gecko models
    try:
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    except Exception:
        try:
            model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        except Exception:
            try:
                model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
            except Exception as e:
                print(f"Error loading embedding model: {e}")
                print("Available models may vary by region. Try:")
                print("  - text-embedding-004 (recommended for us-east1)")
                print("  - textembedding-gecko@003")
                print("  - textembedding-gecko@001")
                raise
    
    # Process in batches (API has rate limits)
    batch_size = 5
    embeddings_data = []
    
    for i in range(0, len(chunks_data), batch_size):
        batch = chunks_data[i:i+batch_size]
        texts = [item["text"] for item in batch]
        
        print(f"Processing batch {i//batch_size + 1}/{(len(chunks_data)-1)//batch_size + 1}")
        
        try:
            # Create embeddings
            embeddings = model.get_embeddings(texts)
            
            # Combine with metadata
            for item, embedding in zip(batch, embeddings):
                embeddings_data.append({
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "embedding": embedding.values
                })
            
            # Rate limiting
            time.sleep(0.5)
        
        except Exception as e:
            print(f"Error in batch {i//batch_size + 1}: {e}")
            continue
    
    # Save embeddings
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(embeddings_data, f, indent=2)
    
    print(f"\nCreated {len(embeddings_data)} embeddings")
    print(f"Saved to: {Path(output_file).absolute()}")
    
    return embeddings_data

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python create_embeddings.py <chunks_file> [output_file]")
        sys.exit(1)
    
    if not os.environ.get("GCP_PROJECT_ID"):
        print("Error: GCP_PROJECT_ID environment variable not set")
        sys.exit(1)
    
    chunks_file = sys.argv[1]
    # Default to embeddings-array.json to avoid conflict with JSONL output
    output_file = sys.argv[2] if len(sys.argv) > 2 else "embeddings-array.json"
    
    create_embeddings(chunks_file, output_file)


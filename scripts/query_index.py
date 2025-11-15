#!/usr/bin/env python3
"""
Test querying the Vector Search index.
"""

import os
from google.cloud import aiplatform
from vertexai.preview import vector_search
from vertexai.language_models import TextEmbeddingModel

def query_index(project_id: str, region: str, index_id: str, query_text: str, top_k: int = 5):
    """
    Query the vector index.
    
    Args:
        project_id: GCP project ID
        region: GCP region
        index_id: Vector Search index ID
        query_text: User's question
        top_k: Number of results to return
    """
    # Initialize
    aiplatform.init(project=project_id, location=region)
    
    # Create query embedding
    # Try text-embedding-004 first (available in us-east1), fall back to gecko models
    try:
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    except Exception:
        try:
            model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        except Exception:
            model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
    query_embedding = model.get_embeddings([query_text])[0]
    
    # Get index
    index = vector_search.get_index(index_id=index_id)
    
    # Query
    results = index.find_neighbors(
        deployed_index_id=None,  # Will be set when index is deployed
        queries=[query_embedding.values],
        num_neighbors=top_k
    )
    
    print(f"Query: {query_text}")
    print(f"\nFound {len(results[0])} results:\n")
    
    for i, result in enumerate(results[0], 1):
        print(f"{i}. Distance: {result.distance}")
        print(f"   Metadata: {result.metadata}")
        print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: python query_index.py <project_id> <region> <index_id> <query_text> [top_k]")
        sys.exit(1)
    
    project_id = sys.argv[1]
    region = sys.argv[2]
    index_id = sys.argv[3]
    query_text = sys.argv[4]
    top_k = int(sys.argv[5]) if len(sys.argv) > 5 else 5
    
    query_index(project_id, region, index_id, query_text, top_k)


#!/usr/bin/env python3
"""
Create a Vector Search index in Vertex AI.
"""

import os
import json
from google.cloud import aiplatform
from vertexai.preview import vector_search

def create_vector_index(project_id: str, region: str, bucket_name: str):
    """
    Create a Vector Search index.
    
    Args:
        project_id: GCP project ID
        region: GCP region (e.g., us-east1)
        bucket_name: Cloud Storage bucket with embeddings
    """
    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=region)
    
    # Index configuration
    index_config = {
        "displayName": "uplifted-mascot-index",
        "description": "Vector search index for Uplifted Mascot",
        "metadata": {
            "contentsDeltaUri": f"gs://{bucket_name}/",
            "config": {
                "dimensions": 768,  # textembedding-gecko@001 produces 768-dim vectors
                "approximateNeighborsCount": 10,
                "distanceMeasureType": "DOT_PRODUCT_DISTANCE",
                "algorithmConfig": {
                    "treeAhConfig": {
                        "leafNodeEmbeddingCount": 500,
                        "leafNodesToSearchPercent": 5
                    }
                }
            }
        }
    }
    
    print(f"Creating index in project {project_id}, region {region}...")
    print(f"Using bucket: gs://{bucket_name}/")
    
    # Create index
    # Note: This is a long-running operation (can take 30+ minutes)
    index = vector_search.create_index(
        display_name=index_config["displayName"],
        contents_delta_uri=index_config["metadata"]["contentsDeltaUri"],
        dimensions=index_config["metadata"]["config"]["dimensions"],
        approximate_neighbors_count=index_config["metadata"]["config"]["approximateNeighborsCount"],
        distance_measure_type=index_config["metadata"]["config"]["distanceMeasureType"],
        description=index_config["description"]
    )
    
    print(f"Index created: {index.name}")
    print(f"Index ID: {index.resource_name}")
    
    return index

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python create_index.py <project_id> <region> <bucket_name>")
        sys.exit(1)
    
    project_id = sys.argv[1]
    region = sys.argv[2]
    bucket_name = sys.argv[3]
    
    create_index(project_id, region, bucket_name)


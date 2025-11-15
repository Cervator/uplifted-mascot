#!/usr/bin/env python3
"""
Check available embedding models in your Vertex AI region.
Run this to see which models are available before using them.
"""

import os
import sys
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

def check_models(project_id: str, region: str = "us-east1"):
    """
    Try to load different embedding models to see which are available.
    
    Args:
        project_id: GCP project ID
        region: GCP region to check
    """
    print(f"Checking available embedding models in {region}...")
    print(f"Project: {project_id}\n")
    
    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=region)
    
    # List of models to try (order: most recommended first)
    models_to_try = [
        "text-embedding-004",  # Recommended for us-east1
        "textembedding-gecko@003",
        "textembedding-gecko@002", 
        "textembedding-gecko@001",
        "textembedding-gecko-multilingual@001",
    ]
    
    available_models = []
    
    for model_name in models_to_try:
        try:
            print(f"Trying {model_name}...", end=" ")
            model = TextEmbeddingModel.from_pretrained(model_name)
            # Try a simple test
            test_embedding = model.get_embeddings(["test"])[0]
            print(f"✓ Available (dimensions: {len(test_embedding.values)})")
            available_models.append(model_name)
        except Exception as e:
            print(f"✗ Not available: {str(e)[:60]}")
    
    print(f"\n{'='*60}")
    if available_models:
        print(f"Available models in {region}:")
        for model in available_models:
            print(f"  - {model}")
        print(f"\nRecommended: Use the highest version number available")
    else:
        print(f"No models found in {region}")
        print("Try a different region or check:")
        print("  1. Vertex AI API is enabled")
        print("  2. Project has necessary permissions")
        print("  3. Region supports the models")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        project_id = os.environ.get("GCP_PROJECT_ID")
        if not project_id:
            print("Usage: python check_models.py <project_id> [region]")
            print("Or set GCP_PROJECT_ID environment variable")
            sys.exit(1)
    else:
        project_id = sys.argv[1]
    
    region = sys.argv[2] if len(sys.argv) > 2 else "us-east1"
    
    check_models(project_id, region)


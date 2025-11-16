#!/usr/bin/env python3
"""
Check which Gemini models are available in your GCP project/region.
"""

import os
import sys
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
REGION = os.getenv("GCP_REGION", "us-east1")

if not PROJECT_ID:
    print("Error: GCP_PROJECT_ID not set in environment")
    sys.exit(1)

print(f"Checking Gemini models for project: {PROJECT_ID}, region: {REGION}")
print("=" * 60)

# Initialize Vertex AI
aiplatform.init(project=PROJECT_ID, location=REGION)

# List of model names to try - from Model Garden shortnames
# Using modern GenerativeModel API (simple names, no "google/" prefix)
model_names = [
    "gemini-2.5-pro",           # Latest Pro model
    "gemini-2.5-flash",          # Latest Flash model
    "gemini-2.5-flash-lite",     # Fastest model
    "gemini-2.0-flash-001",      # Stable Flash
    "gemini-2.0-flash-lite-001", # Stable Flash-Lite
    # Legacy names
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-pro",
]

print("\nTrying GenerativeModel() with various names (modern API):\n")

available_models = []
working_models = []  # Models that actually work (not just load)
for model_name in model_names:
    try:
        print(f"  Trying: {model_name}...", end=" ")
        model = GenerativeModel(model_name)
        print("✓ Loaded", end="")
        available_models.append(model_name)
        # Try to test it works - use generate_content (simpler, may avoid deprecation)
        try:
            # Try generate_content first (simpler, single-turn)
            response = model.generate_content("test")
            print(" ✓ Works (generate_content)")
            working_models.append(model_name)
        except AttributeError:
            # Fallback to chat API if generate_content doesn't exist
            try:
                chat = model.start_chat()
                response = chat.send_message("test")
                print(" ✓ Works (start_chat)")
                working_models.append(model_name)
            except Exception as e2:
                error_msg = str(e2)
                if "404" in error_msg or "not found" in error_msg.lower():
                    print(" ✗ Chat test failed (404)")
                else:
                    print(f" ✗ Chat test failed: {error_msg[:50]}")
        except Exception as e:
            # Other errors from generate_content
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                print(" ✗ Test failed (404)")
            else:
                print(f" ✗ Test failed: {error_msg[:50]}")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            print("✗ NOT FOUND")
        else:
            print(f"✗ ERROR: {error_msg[:60]}")

print("\n" + "=" * 60)
if working_models:
    print(f"\n✓ Working models (tested successfully): {', '.join(working_models)}")
    # Recommend Flash models for RAG (faster, cheaper)
    flash_models = [m for m in working_models if 'flash' in m.lower()]
    if flash_models:
        recommended = flash_models[0]  # First Flash model
        print(f"\n💡 Recommended for RAG: '{recommended}' (Flash models are faster and cheaper for document Q&A)")
    else:
        print(f"\n💡 Recommended: '{working_models[0]}'")
elif available_models:
    print(f"\n⚠ Models loaded but chat test failed: {', '.join(available_models)}")
    print("   These models may not be available in your region or may need different configuration")
else:
    print("\n✗ No Gemini models found!")
    print("\nPossible issues:")
    print("  1. Gemini API not enabled in your project")
    print("  2. Region doesn't support Gemini models")
    print("  3. Need to use a different model name format")
    print("\nTry enabling the Generative AI API:")
    print(f"  gcloud services enable generativelanguage.googleapis.com --project={PROJECT_ID}")
    print(f"  gcloud services enable aiplatform.googleapis.com --project={PROJECT_ID}")
    print("\nMake sure you're using the modern GenerativeModel API:")
    print("  from vertexai.generative_models import GenerativeModel")
    print("  model = GenerativeModel('gemini-2.5-pro')")


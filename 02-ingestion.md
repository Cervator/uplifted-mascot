# Document Ingestion Pipeline

## Overview

The ingestion pipeline processes markdown files from your knowledge base, chunks them into semantically meaningful segments, and creates embeddings using Vertex AI. This is the "brain building" phase of the Uplifted Mascot system.

## Prerequisites

- Python 3.9 or higher
- Google Cloud SDK (`gcloud`) installed and configured
- Vertex AI API enabled in your GCP project
- Authentication set up (see Authentication section)

## Setup

### Step 1: Install Dependencies

**Using requirements.txt (Recommended):**

```bash
# Create virtual environment
python3 -m venv ~/um-workspace/venv
source ~/um-workspace/venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
cd um/scripts
pip install -r requirements.txt
```

**Or install individually:**

```bash
pip install google-cloud-aiplatform
pip install tiktoken  # For token counting
```

**Windows-specific issues?** See `um/scripts/setup-windows.md` for troubleshooting.

### Step 2: Set Up GCP Authentication

```bash
# Authenticate with GCP
gcloud auth login

# Set your project
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Set application default credentials
gcloud auth application-default login
```

### Step 3: Verify Authentication

```bash
# Test API access
python3 << EOF
from google.cloud import aiplatform
print("Vertex AI access verified!")
EOF
```

## Document Processing Script

### Basic Processing Script

The document processing script is located at `scripts/process_docs.py` in this repository.

**Copy the script to your workspace:**
```bash
# Copy from this repo to your workspace
cp um/scripts/process_docs.py ~/um-workspace/
# Or on Windows:
copy um\scripts\process_docs.py %USERPROFILE%\um-workspace\
```

### Step 4: Run Document Processing

```bash
# Activate virtual environment
source ~/um-workspace/venv/bin/activate  # On Windows: venv\Scripts\activate

# Process your repository
python ~/um-workspace/process_docs.py ~/um-workspace/your-repo chunks.json
# On Windows:
python %USERPROFILE%\um-workspace\process_docs.py %USERPROFILE%\um-workspace\your-repo chunks.json

# Verify output
head -50 chunks.json  # On Windows: type chunks.json | more
```

## Creating Embeddings

### Embedding Script

The embedding creation script is located at `scripts/create_embeddings.py` in this repository.

**Copy the script to your workspace:**
```bash
# Copy from this repo to your workspace
cp um/scripts/create_embeddings.py ~/um-workspace/
# Or on Windows:
copy um\scripts\create_embeddings.py %USERPROFILE%\um-workspace\
```

### Step 5: Create Embeddings

```bash
# Set your GCP project
export GCP_PROJECT_ID="your-project-id"

# Create embeddings
python ~/um-workspace/create_embeddings.py chunks.json embeddings.json

# Check output size
ls -lh embeddings.json
```

## Manual Workflow Summary

### Complete Manual Process

```bash
# 1. Setup
cd ~/um-workspace
python3 -m venv venv
source venv/bin/activate
pip install google-cloud-aiplatform tiktoken

# 2. Authenticate
gcloud auth application-default login
export GCP_PROJECT_ID="your-project-id"

# 3. Process documents
python process_docs.py ~/path/to/repo chunks.json

# 4. Create embeddings
python create_embeddings.py chunks.json embeddings.json

# 5. Next: Upload to Vector Search (see 03-vector-storage.md)
```

## Troubleshooting

### Issue: Authentication Errors

```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project

# Check API is enabled
gcloud services list --enabled | grep aiplatform
```

### Issue: Rate Limiting

**Solution**: Increase delay between batches
```python
time.sleep(1.0)  # Increase from 0.5 to 1.0 seconds
```

### Issue: Large Files

**Solution**: Process files individually or increase chunk size
```python
# In process_docs.py, adjust:
max_chunk_size = 2000  # Increase from 1000
```

### Issue: Memory Issues

**Solution**: Process in smaller batches or files
```bash
# Process one file at a time
python process_docs.py ~/repo/docs/single-file.md single-chunks.json
```

## Next Steps

Once embeddings are created:

1. **Verify embeddings.json** - Check file size and structure
2. **Proceed to Vector Storage** - See `03-vector-storage.md` to upload to Vertex AI Vector Search

## Cost Estimation

- **Embedding API**: ~$0.0001 per 1K characters
- **Example**: 1000 chunks of ~1000 chars each = ~$0.10
- **Your $50 credit**: Should handle ~500,000 chunks

Monitor usage:
```bash
gcloud billing accounts list
```


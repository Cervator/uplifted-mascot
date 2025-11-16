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
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
cd scripts
pip install -r requirements.txt
```

**Or install individually:**

```bash
pip install google-cloud-aiplatform
pip install tiktoken  # For token counting
```

**Windows-specific issues?** See `scripts/setup-windows.md` for troubleshooting.

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

### Step 4: Run Document Processing

```bash
# Activate virtual environment (if using one)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Process your repository
python scripts/process_docs.py path/to/your-repo chunks.json
# On Windows:
python scripts\process_docs.py path\to\your-repo chunks.json

# Verify output
head -50 chunks.json  # On Windows: type chunks.json | more
```

## Creating Embeddings

### Embedding Script

The embedding creation script is located at `scripts/create_embeddings.py` in this repository.

### Step 5: Create Embeddings

```bash
# Set your GCP project
export GCP_PROJECT_ID="your-project-id"
# On Windows:
set GCP_PROJECT_ID=your-project-id

# Create embeddings (outputs JSON array format)
# From workspace root:
python scripts/create_embeddings.py scripts/chunks.json scripts/embeddings-array.json

# On Windows (from workspace root):
python scripts\create_embeddings.py scripts\chunks.json scripts\embeddings-array.json

# Check output size
ls -lh scripts/embeddings-array.json
# On Windows:
dir scripts\embeddings-array.json
```

## Manual Workflow Summary

### Complete Manual Process

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
cd scripts
pip install -r requirements.txt

# 2. Authenticate
gcloud auth application-default login
export GCP_PROJECT_ID="your-project-id"
# On Windows:
set GCP_PROJECT_ID=your-project-id

# 3. Process documents
python process_docs.py ../path/to/repo chunks.json

# 4. Create embeddings
python create_embeddings.py chunks.json embeddings-array.json

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


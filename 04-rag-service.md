# RAG Service API

## Overview

The RAG (Retrieval-Augmented Generation) Service is the API endpoint that powers the Uplifted Mascot. It receives user questions, retrieves relevant context from ChromaDB (or Vertex AI Vector Search for scaling), and generates responses using Vertex AI Gemini.

## Prerequisites

- **ChromaDB database loaded** (see `03-vector-storage.md`) - **Recommended for development**
- OR Vertex AI Vector Search index created and deployed (optional, for scaling)
- GCP project with Vertex AI API enabled (for embeddings and Gemini)
- Python 3.9+ environment
- GKE cluster (for deployment) or local testing setup

## Local Development Setup

### Step 1: Install Dependencies

```bash
# Activate virtual environment (if using one)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install web framework and dependencies
cd rag-service
pip install -r requirements.txt
```

### Step 2: Set Up Vector Storage

**Option A: ChromaDB (Recommended - Free, Local)**

1. Make sure you have `scripts/embeddings-array.json` (JSON array format from `create_embeddings.py`)
   - If you only have `embeddings.json` (JSONL format), regenerate: `python scripts/create_embeddings.py scripts/chunks.json scripts/embeddings-array.json`

2. Load embeddings into ChromaDB (from workspace root):
   ```bash
   python scripts/load_chromadb.py scripts/embeddings-array.json
   ```

3. That's it! The RAG service will automatically find and use ChromaDB.

**Option B: Vertex AI Vector Search (For Scaling)**

If you need Vertex AI Vector Search for large datasets:
1. Set up Vector Search index (see `03-vector-storage.md` - Scaling section)
2. Add these to your `.env` file (optional):
   ```env
   VECTOR_INDEX_ID=your-index-id
   VECTOR_ENDPOINT_ID=your-endpoint-id
   DEPLOYED_INDEX_ID=um_deployed_index
   ```

### Step 3: Create Environment File

The `.env` file works on Windows just like on Linux/Mac. Python's `python-dotenv` library (already in requirements.txt) automatically loads it.

Create the `.env` file at the root of the workspace with this content:

```env
# Required
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-east1

# ChromaDB (optional - defaults shown)
CHROMA_COLLECTION_NAME=uplifted_mascot
CHROMA_PERSIST_DIR=./chroma_db

# Vertex AI Vector Search (optional - only if using for scaling)
# VECTOR_INDEX_ID=your-index-id
# VECTOR_ENDPOINT_ID=your-endpoint-id
# DEPLOYED_INDEX_ID=um_deployed_index
```

**Note**: The RAG service uses ChromaDB by default. It will only use Vertex AI Vector Search if `VECTOR_INDEX_ID` and `VECTOR_ENDPOINT_ID` are set in `.env`.


**Note**: 
- The `.env` file is automatically loaded by `python-dotenv` when you run the RAG service
- Don't commit `.env` to git

### Loading .env Variables in Your Shell (Optional)

If you want to use the environment variables in your Windows shell (like `source .env` on Linux):

```cmd
set GCP_PROJECT_ID=teralivekubernetes
set GCP_REGION=us-east1
set VECTOR_INDEX_ID=1385072389695471616
set VECTOR_ENDPOINT_ID=your-endpoint-id
```

**Note**: For the RAG service, you don't need to load `.env` into your shell - `python-dotenv` handles it automatically when Python runs. These methods are only if you want the variables available in your shell for other commands.

### Step 4: Run Locally

```bash
# Make sure .env file is set up (see Step 3)
# The service will automatically load it

# Run the service
cd rag-service
python rag_service.py
```

The service will be available at `http://localhost:8000`

**What happens on startup:**
- Loads configuration from `.env`
- Connects to ChromaDB (or Vertex AI Vector Search if configured)
- Initializes Vertex AI for embeddings and Gemini
- Validates that vector storage is available

If ChromaDB is not found, you'll see an error with instructions to run `load_chromadb.py`.

### Step 5: Test the API

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/ask-mascot \
  -H "Content-Type: application/json" \
  -d '{
    "project": "bifrost",
    "mascot": "gooey",
    "question": "What is the Bifrost protocol?",
    "top_k": 5
  }'
```

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Deployment to GKE

### Step 5: Build and Push Container

The `Dockerfile` and `requirements.txt` are already in the `rag-service/` directory.

```bash
# Set variables
export GCP_PROJECT_ID="your-project-id"
export IMAGE_NAME="gcr.io/$GCP_PROJECT_ID/um-rag-service"
# On Windows:
set GCP_PROJECT_ID=your-project-id
set IMAGE_NAME=gcr.io/%GCP_PROJECT_ID%/um-rag-service

# Build
cd rag-service
docker build -t %IMAGE_NAME%:latest .

# Push to GCR
docker push %IMAGE_NAME%:latest
```

### Step 6: Deploy to GKE

The Kubernetes deployment file is located at `rag-service/k8s-deployment.yaml`. Edit it and update with your values:

```bash
# Edit the file and update:
# - YOUR_PROJECT_ID
# - Environment variable values
notepad rag-service\k8s-deployment.yaml
```

Deploy:

```bash
# Apply deployment
kubectl apply -f rag-service/k8s-deployment.yaml

# Check status
kubectl get pods -l app=um-rag-service
kubectl get service um-rag-service

# Get external IP
kubectl get service um-rag-service
```

## Manual Testing Workflow

```bash
# 1. Start service locally
cd rag-service
source ../venv/bin/activate  # On Windows: ..\venv\Scripts\activate
python rag_service.py

# 2. In another terminal, test
curl http://localhost:8000/health

# 3. Ask a question
curl -X POST http://localhost:8000/ask-mascot \
  -H "Content-Type: application/json" \
  -d '{
    "project": "bifrost",
    "mascot": "gooey",
    "question": "How does the JEP workflow work?",
    "top_k": 3
  }'

# 4. Check logs
# Service logs will show retrieval and generation steps
```

## Troubleshooting

### Issue: Virtual Environment Not Working (Windows)

If you see errors like `OSError: [WinError 2]` or pip installing to system Python:

**Solution 1: Verify venv is activated**
```cmd
REM Check that you see (venv) in your prompt
REM Verify Python path points to venv
where python
REM Should show: D:\Dev\GitWS\uplifted-mascot\venv\Scripts\python.exe

REM If not, reactivate:
venv\Scripts\activate
```

**Solution 2: Recreate the venv**
```cmd
REM Deactivate current venv (if active)
deactivate

REM Remove old venv
rmdir /s /q venv

REM Create fresh venv
python -m venv venv

REM Activate it
venv\Scripts\activate

REM Verify it's using venv Python
where python
REM Should show venv path, not system Python

REM Upgrade pip in venv
python -m pip install --upgrade pip

REM Now install requirements
cd rag-service
pip install -r requirements.txt
```

**Solution 3: Use python -m pip explicitly**
```cmd
REM Even if venv seems active, use explicit module invocation
python -m pip install -r rag-service\requirements.txt
```

### Issue: Gemini Model Not Found

If you see errors like "Unknown model publishers/google/models/gemini-*":

**Solution 1: Check available models**
```cmd
REM Run the model checker script
cd scripts
python check_gemini_models.py
```

This will test which Gemini models are available in your region and show you which one to use.

**Solution 2: Enable Generative AI API**
```cmd
gcloud services enable generativelanguage.googleapis.com --project=%GCP_PROJECT_ID%
gcloud services enable aiplatform.googleapis.com --project=%GCP_PROJECT_ID%
```

**Solution 3: Use Generative AI SDK (Alternative)**
If Vertex AI ChatModel doesn't work, you can use the Generative AI SDK instead:
```bash
pip install google-generativeai
```

Then in `rag_service.py`, replace the ChatModel import with:
```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
```

### Issue: Authentication Errors

```bash
# Re-authenticate
gcloud auth application-default login

# Verify in code
python -c "from google.cloud import aiplatform; print('Auth OK')"
```

### Issue: ChromaDB Collection Not Found

**Error**: `ChromaDB collection 'uplifted_mascot' not found`

**Solution**: Load embeddings into ChromaDB (make sure you're using `embeddings-array.json`, not `embeddings.json`):
```bash
# From workspace root
python scripts/load_chromadb.py scripts/embeddings-array.json
```

**Check**:
- ChromaDB database exists in `./chroma_db` (or path specified in `CHROMA_PERSIST_DIR`)
- Collection name matches `CHROMA_COLLECTION_NAME` in `.env` (default: `uplifted_mascot`)
- You've run `load_chromadb.py` after creating embeddings

### Issue: Vertex AI Vector Search Not Found (If Using for Scaling)

**Check**:
- INDEX_ID and ENDPOINT_ID are set in `.env`
- Index is deployed to endpoint
- Region matches
- Endpoint is not undeployed

### Issue: Slow Responses

**Optimize**:
- Reduce `top_k` (fewer chunks to process)
- Cache embeddings
- Use smaller context windows

### Issue: Memory Issues

**Solution**: Increase container resources in deployment YAML

## Cost Considerations

- **Embedding API**: ~$0.0001 per query
- **Gemini API**: ~$0.0005-0.002 per response (depends on length)
- **Per Query**: ~$0.001-0.002 total
- **Your $50 credit**: ~25,000-50,000 queries

## Next Steps

Once the RAG service is running:

1. **Test with various questions** - Verify quality of responses
2. **Proceed to Frontend** - See `05-frontend.md` to build the web interface

## Save Service URL

After deployment, save your service URL:

```bash
# Get service URL
SERVICE_URL=$(kubectl get service um-rag-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Save to config
echo "RAG_SERVICE_URL=http://$SERVICE_URL" >> config.env
```


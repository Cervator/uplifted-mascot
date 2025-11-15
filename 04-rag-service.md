# RAG Service API

## Overview

The RAG (Retrieval-Augmented Generation) Service is the API endpoint that powers the Uplifted Mascot. It receives user questions, retrieves relevant context from Vector Search, and generates responses using Vertex AI Gemini.

## Prerequisites

- Vector Search index created and deployed (see `03-vector-storage.md`)
- GCP project with Vertex AI API enabled
- Python 3.9+ environment
- GKE cluster (for deployment) or local testing setup

## Local Development Setup

### Step 1: Install Dependencies

```bash
# Activate virtual environment
source ~/um-workspace/venv/bin/activate

# Install web framework and dependencies
pip install fastapi uvicorn
pip install google-cloud-aiplatform
pip install python-dotenv
```

### Step 2: Copy RAG Service

The RAG service is located at `rag-service/rag_service.py` in this repository.

**Copy the service to your workspace:**

```bash
# Copy the RAG service directory
cp -r um/rag-service ~/um-workspace/
# On Windows PowerShell:
xcopy /E /I um\rag-service %USERPROFILE%\um-workspace\rag-service
```

### Step 3: Create Environment File

Copy the example environment file and update it with your values:

```bash
# Copy example .env file
cp um/config/.env.example ~/um-workspace/rag-service/.env
# On Windows:
copy um\config\.env.example %USERPROFILE%\um-workspace\rag-service\.env

# Edit .env and update with your actual values:
# - GCP_PROJECT_ID
# - VECTOR_INDEX_ID
# - VECTOR_ENDPOINT_ID
```

**Note**: Get these IDs from your Vector Search setup (see `03-vector-storage.md`).

### Step 4: Run Locally

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export VECTOR_INDEX_ID="your-index-id"
export VECTOR_ENDPOINT_ID="your-endpoint-id"

# Run the service
python ~/um-workspace/rag_service.py
```

The service will be available at `http://localhost:8000`

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

### Step 6: Dockerfile and Requirements

The `Dockerfile` and `requirements.txt` are already in the `rag-service/` directory you copied. They're ready to use.

### Step 8: Build and Push Container

```bash
# Set variables
export GCP_PROJECT_ID="your-project-id"
export IMAGE_NAME="gcr.io/$GCP_PROJECT_ID/um-rag-service"

# Build
docker build -t $IMAGE_NAME:latest ~/um-workspace

# Push to GCR
docker push $IMAGE_NAME:latest
```

### Step 9: Deploy to GKE

The Kubernetes deployment file is located at `rag-service/k8s-deployment.yaml`. Copy it and update with your values:

```bash
# Copy deployment file
cp um/rag-service/k8s-deployment.yaml ~/um-workspace/
# On Windows:
copy um\rag-service\k8s-deployment.yaml %USERPROFILE%\um-workspace\

# Edit the file and update:
# - YOUR_PROJECT_ID
# - Environment variable values
```

Deploy:

```bash
# Apply deployment
kubectl apply -f ~/um-workspace/k8s-deployment.yaml

# Check status
kubectl get pods -l app=um-rag-service
kubectl get service um-rag-service

# Get external IP
kubectl get service um-rag-service
```

## Manual Testing Workflow

```bash
# 1. Start service locally
cd ~/um-workspace
source venv/bin/activate
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

### Issue: Authentication Errors

```bash
# Re-authenticate
gcloud auth application-default login

# Verify in code
python -c "from google.cloud import aiplatform; print('Auth OK')"
```

### Issue: Index Not Found

**Check**:
- INDEX_ID and ENDPOINT_ID are correct
- Index is deployed to endpoint
- Region matches

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
echo "RAG_SERVICE_URL=http://$SERVICE_URL" >> ~/um-workspace/config.env
```


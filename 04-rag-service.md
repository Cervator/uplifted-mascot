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
# Activate virtual environment (if using one)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install web framework and dependencies
cd rag-service
pip install -r requirements.txt
```

### Step 2: Create Environment File

Create an environment file in the `rag-service/` directory:

```bash
# Create .env file in rag-service directory
cd rag-service
# On Windows:
cd rag-service

# Create .env file with your values:
# - GCP_PROJECT_ID
# - VECTOR_INDEX_ID
# - VECTOR_ENDPOINT_ID
```

**Note**: Get these IDs from your Vector Search setup (see `03-vector-storage.md`).

### Step 3: Run Locally

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export VECTOR_INDEX_ID="your-index-id"
export VECTOR_ENDPOINT_ID="your-endpoint-id"
# On Windows:
set GCP_PROJECT_ID=your-project-id
set VECTOR_INDEX_ID=your-index-id
set VECTOR_ENDPOINT_ID=your-endpoint-id

# Run the service
cd rag-service
python rag_service.py
# On Windows:
cd rag-service
python rag_service.py
```

The service will be available at `http://localhost:8000`

### Step 4: Test the API

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
echo "RAG_SERVICE_URL=http://$SERVICE_URL" >> config.env
```


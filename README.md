# Uplifted Mascot - Technical Documentation

This directory contains the technical implementation guides for the Uplifted Mascot system, broken down into 5 major components.

## Quick Start

For a complete manual workflow from GitHub to working website:

1. **Knowledge Base** (`01-knowledge-base.md`) - Set up your GitHub repository
2. **Ingestion** (`02-ingestion.md`) - Process markdown files and create embeddings
3. **Vector Storage** (`03-vector-storage.md`) - Upload embeddings to Vertex AI Vector Search
4. **RAG Service** (`04-rag-service.md`) - Build and deploy the API endpoint
5. **Frontend** (`05-frontend.md`) - Create the web interface

## Documentation Structure

### 01-knowledge-base.md
- Setting up GitHub repositories
- File structure and organization
- Manual repository cloning and validation
- Multiple repository support

### 02-ingestion.md
- Document processing and chunking
- Creating embeddings with Vertex AI
- Python scripts for processing
- Manual workflow commands

### 03-vector-storage.md
- Vertex AI Vector Search setup
- Cloud Storage bucket creation
- Index creation and deployment
- Query testing

### 04-rag-service.md
- FastAPI service implementation
- Local development setup
- GKE deployment
- API endpoints and testing

### 05-frontend.md
- HTML/CSS/JavaScript chat interface
- Embeddable widget version
- Deployment options (GitHub Pages, GCS, etc.)
- Customization guide

## Prerequisites

Before starting, ensure you have:

- **GCP Account**: With Vertex AI API enabled
- **Google Cloud SDK**: `gcloud` CLI installed
- **Python 3.9+**: For processing scripts
- **Git**: For repository access
- **Basic Terminal Skills**: For running commands

## Manual Workflow Summary

```bash
# 1. Setup environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
cd scripts
pip install -r requirements.txt
cd ../rag-service
pip install -r requirements.txt

# 2. Authenticate
gcloud auth application-default login
export GCP_PROJECT_ID="your-project-id"
# On Windows:
set GCP_PROJECT_ID=your-project-id

# 3. Process documents (see 01 & 02)
git clone https://github.com/your-org/your-repo.git
cd scripts
python process_docs.py ../your-repo chunks.json
python create_embeddings.py chunks.json embeddings-array.json

# 4. Setup vector storage (see 03)
# Create bucket, upload, create index

# 5. Deploy RAG service (see 04)
cd ../rag-service
python rag_service.py  # Local testing
# Or deploy to GKE

# 6. Create frontend (see 05)
cd ../frontend
# Edit HTML, test locally, deploy
```

## Cost Estimation

With Google Developer Program Premium ($50/month credit):

- **Development/Testing**: More than sufficient
- **Embedding Creation**: ~$0.10 per 1000 chunks
- **Query Operations**: ~$0.001-0.002 per question
- **Estimated Capacity**: 25,000-50,000 queries per month

## Next Steps

1. Start with `01-knowledge-base.md` to set up your repository
2. Follow each guide sequentially
3. Test each component before moving to the next
4. Once working manually, consider automating with Jenkins (future)

## Getting Help

- Check troubleshooting sections in each document
- Verify GCP authentication and API enablement
- Ensure all environment variables are set correctly
- Review error messages in service logs

## Related Documentation

- Main overview: `../uplifted-mascot.md`
- System integration: `../overview.md`
- Bifrost protocol: `../bifrost-protocol.md`


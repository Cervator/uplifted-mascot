# Vector Storage Setup

## Overview

Vertex AI Vector Search stores the document embeddings created during ingestion. This is the "brain" of the Uplifted Mascot system - it enables semantic search across your knowledge base.

## Prerequisites

- GCP project with Vertex AI API enabled
- Embeddings JSON file from ingestion step (see `02-ingestion.md`)
- `gcloud` CLI configured
- Python environment with required packages

## Initial Setup

### Step 1: Enable Required APIs

```bash
# Set your project
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage-component.googleapis.com
```

### Step 2: Create Cloud Storage Bucket

Vector Search requires embeddings to be stored in Cloud Storage first.

```bash
# Set variables
export BUCKET_NAME="um-embeddings-$(date +%s)"  # Unique bucket name
export REGION="us-east1"

# Create bucket
gsutil mb -p $GCP_PROJECT_ID -l $REGION gs://$BUCKET_NAME

# Verify
gsutil ls gs://$BUCKET_NAME
```

### Step 3: Upload Embeddings to Cloud Storage

```bash
# Upload embeddings JSON
gsutil cp embeddings.json gs://$BUCKET_NAME/

# Verify upload
gsutil ls gs://$BUCKET_NAME/
```

## Create Vector Search Index

### Step 4: Prepare Index Configuration

Copy the example configuration file from `config/index-config.yaml.example` and update it with your bucket name:

```bash
# Copy example config
cp um/config/index-config.yaml.example ~/um-workspace/index-config.yaml
# On Windows:
copy um\config\index-config.yaml.example %USERPROFILE%\um-workspace\index-config.yaml

# Edit the file and replace YOUR_BUCKET_NAME with your actual bucket name
```

### Step 5: Create Index Script

The index creation script is located at `scripts/create_index.py` in this repository.

**Copy the script to your workspace:**
```bash
cp um/scripts/create_index.py ~/um-workspace/
# On Windows:
copy um\scripts\create_index.py %USERPROFILE%\um-workspace\
```

### Step 6: Convert Embeddings to Vector Search Format

Vector Search requires a specific JSONL format. The conversion script is located at `scripts/convert_to_jsonl.py`.

**Copy the script to your workspace:**
```bash
cp um/scripts/convert_to_jsonl.py ~/um-workspace/
# On Windows:
copy um\scripts\convert_to_jsonl.py %USERPROFILE%\um-workspace\
```

### Step 7: Upload in Correct Format

```bash
# Convert to JSONL
python ~/um-workspace/convert_to_jsonl.py embeddings.json embeddings.jsonl

# Upload JSONL to bucket
gsutil cp embeddings.jsonl gs://$BUCKET_NAME/

# Also upload the original embeddings.json for reference
gsutil cp embeddings.json gs://$BUCKET_NAME/
```

## Alternative: Simplified Approach (Manual Index Creation)

For initial testing, you can use the `gcloud` CLI:

### Step 8: Create Index via gcloud

```bash
# Create index configuration file
# Note: displayName is specified via --display-name flag, not in this file
cat > index-config.yaml << EOF
config:
  dimensions: 768
  approximateNeighborsCount: 10
  distanceMeasureType: "DOT_PRODUCT_DISTANCE"
  algorithmConfig:
    treeAhConfig:
      leafNodeEmbeddingCount: 500
      fractionLeafNodesToSearch: 0.05
contentsDeltaUri: "gs://${BUCKET_NAME}/"
EOF

# Create index (this takes 30+ minutes)
gcloud ai indexes create \
  --project=$GCP_PROJECT_ID \
  --region=$REGION \
  --display-name="uplifted-mascot-index" \
  --metadata-file=index-config.yaml
```

**Note**: Index creation is asynchronous and can take 30-60 minutes for large datasets.

### Step 9: Check Index Status

```bash
# List indexes
gcloud ai indexes list --project=$GCP_PROJECT_ID --region=$REGION

# Get index details
gcloud ai indexes describe INDEX_ID \
  --project=$GCP_PROJECT_ID \
  --region=$REGION
```

## Query the Index (Testing)

### Step 10: Test Query Script

The query script is located at `scripts/query_index.py` in this repository.

**Copy the script to your workspace:**
```bash
cp um/scripts/query_index.py ~/um-workspace/
# On Windows:
copy um\scripts\query_index.py %USERPROFILE%\um-workspace\
```

## Manual Workflow Summary

```bash
# 1. Setup
export GCP_PROJECT_ID="your-project-id"
export REGION="us-east1"
export BUCKET_NAME="um-embeddings-$(date +%s)"

# 2. Create bucket
gsutil mb -p $GCP_PROJECT_ID -l $REGION gs://$BUCKET_NAME

# 3. Convert and upload embeddings
python convert_to_jsonl.py embeddings.json embeddings.jsonl
gsutil cp embeddings.jsonl gs://$BUCKET_NAME/

# 4. Create index (takes 30+ minutes)
gcloud ai indexes create \
  --project=$GCP_PROJECT_ID \
  --region=$REGION \
  --display-name="uplifted-mascot-index" \
  --metadata-file=index-config.yaml

# 5. Check status
gcloud ai indexes list --project=$GCP_PROJECT_ID --region=$REGION

# 6. Note the INDEX_ID for use in RAG service
```

## Important Notes

### Index Deployment

After creating an index, you need to deploy it to an endpoint before querying:

```bash
# Create endpoint
gcloud ai index-endpoints create \
  --project=$GCP_PROJECT_ID \
  --region=$REGION \
  --display-name="um-endpoint"

# Deploy index to endpoint
gcloud ai index-endpoints deploy-index ENDPOINT_ID \
  --project=$GCP_PROJECT_ID \
  --region=$REGION \
  --deployed-index-id="um-deployed-index" \
  --index=INDEX_ID
```

### Cost Considerations

- **Index Storage**: ~$0.10 per GB per month
- **Query Operations**: ~$0.10 per 1K queries
- **Your $50 credit**: Should handle significant usage for development

## Troubleshooting

### Issue: Index Creation Fails

**Check**:
- Bucket exists and is accessible
- JSONL format is correct
- Embedding dimensions match (768 for textembedding-gecko@001)

### Issue: Long Creation Time

**Normal**: Index creation can take 30-60 minutes for large datasets. Check status periodically.

### Issue: Query Errors

**Solution**: Ensure index is deployed to an endpoint before querying.

## Next Steps

Once your index is created and deployed:

1. **Note the Index ID and Endpoint ID** - You'll need these for the RAG service
2. **Proceed to RAG Service** - See `04-rag-service.md` to build the API endpoint

## Save Configuration

Create a config file with your setup:

```bash
cat > ~/um-workspace/vector-config.json << EOF
{
  "project_id": "$GCP_PROJECT_ID",
  "region": "$REGION",
  "bucket_name": "$BUCKET_NAME",
  "index_id": "YOUR_INDEX_ID",
  "endpoint_id": "YOUR_ENDPOINT_ID",
  "deployed_index_id": "um-deployed-index"
}
EOF
```


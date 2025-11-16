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
cp config/index-config.yaml.example index-config.yaml
# On Windows:
copy config\index-config.yaml.example index-config.yaml

# Edit the file and replace YOUR_BUCKET_NAME with your actual bucket name
```

### Step 5: Create Index Script

The index creation script is located at `scripts/create_index.py` in this repository.

### Step 6: Convert Embeddings to Vector Search Format

Vector Search requires a specific JSONL format. The conversion script is located at `scripts/convert_to_jsonl.py`.

### Step 7: Upload in Correct Format

```bash
# Convert to JSONL (with .json extension - Vector AI requires .json extension)
python scripts/convert_to_jsonl.py embeddings-array.json embeddings.json

# Upload JSON file to bucket (must have .json extension even though content is JSONL)
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

## Manual Workflow Summary

```bash
# 1. Setup
export GCP_PROJECT_ID="your-project-id"
export REGION="us-east1"
export BUCKET_NAME="um-embeddings-$(date +%s)"

# 2. Create bucket
gsutil mb -p $GCP_PROJECT_ID -l $REGION gs://$BUCKET_NAME

# 3. Convert and upload embeddings
python scripts/convert_to_jsonl.py embeddings-array.json embeddings.json
gsutil cp embeddings.json gs://$BUCKET_NAME/

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
# Create endpoint (just a container - no compute costs yet)
gcloud ai index-endpoints create \
  --project=$GCP_PROJECT_ID \
  --region=$REGION \
  --display-name="um-endpoint"

# Deploy index to endpoint
# IMPORTANT: The machine type is set HERE during deployment, not during endpoint creation
# Use --machine-type="e2-standard-2" for development to minimize costs!
# e2-standard-16 costs ~$0.75/hour vs e2-standard-2 at ~$0.10/hour
gcloud ai index-endpoints deploy-index ENDPOINT_ID \
  --project=$GCP_PROJECT_ID \
  --region=$REGION \
  --deployed-index-id="um_deployed_index" \
  --display-name="um_deployed_index" \
  --index=INDEX_ID \
  --machine-type="e2-standard-2"
```

### Cost Management

**⚠️ Important: Deployed indexes run 24/7 and can be expensive!**

**Key Point**: The endpoint itself is just a container (no cost). The compute costs come from the deployed index. When you deploy an index to an endpoint, that's when the compute instance starts running. Costs depend on the machine type specified during deployment:
- **e2-standard-2**: ~$0.10/hour (~$73/month) - Recommended
- **e2-standard-16**: ~$0.75/hour (~$547/month) - ⚠️ Very expensive!

**To reduce costs:**

1. **Delete endpoint when not in use** (stops all costs):
   ```bash
   # Delete the entire endpoint (index data is preserved)
   gcloud ai index-endpoints delete ENDPOINT_ID \
     --project=$GCP_PROJECT_ID \
     --region=$REGION
   
   # When needed again, recreate endpoint and redeploy index
   ```

2. **Undeploy index** (stops compute costs, endpoint remains but costs nothing):
   ```bash
   # Undeploy the index (stops compute costs)
   gcloud ai index-endpoints undeploy-index ENDPOINT_ID \
     --project=$GCP_PROJECT_ID \
     --region=$REGION \
     --deployed-index-id="um_deployed_index"
   
   # When needed again, redeploy with smaller machine type
   gcloud ai index-endpoints deploy-index ENDPOINT_ID \
     --project=$GCP_PROJECT_ID \
     --region=$REGION \
     --deployed-index-id="um_deployed_index" \
     --display-name="um_deployed_index" \
     --index=INDEX_ID \
     --machine-type="e2-standard-2"
   ```

### Cost Considerations

- **Index Storage**: ~$0.10 per GB per month (cheap - data storage)
- **Deployed Index Compute**: ~$0.10-0.75/hour depending on machine type (runs 24/7) ⚠️
- **Empty Endpoint**: No cost (endpoint without deployed index costs nothing)
- **Query Operations**: ~$0.10 per 1K queries (very cheap)
- **Your $50 credit**: Will be consumed quickly by endpoint compute costs if using large machine types!

**Recommendation**: Use `e2-standard-2` for development, and undeploy when not actively testing.

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
cat > vector-config.json << EOF
{
  "project_id": "$GCP_PROJECT_ID",
  "region": "$REGION",
  "bucket_name": "$BUCKET_NAME",
  "index_id": "YOUR_INDEX_ID",
  "endpoint_id": "YOUR_ENDPOINT_ID",
  "deployed_index_id": "um_deployed_index"
}
EOF
```


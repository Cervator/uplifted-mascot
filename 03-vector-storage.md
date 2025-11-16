# Vector Storage Setup

## Overview

For small to medium datasets (up to a few thousand documents), we use **ChromaDB** - a self-hosted, open-source vector database that runs locally with zero cost. This is the recommended approach for development and small-scale deployments.

For larger datasets or production scaling, see the [Vertex AI Vector Search](#scaling-with-vertex-ai-vector-search) section below.

## Prerequisites

- Embeddings JSON file from ingestion step (see `02-ingestion.md`)
- Python environment with required packages

## ChromaDB Setup (Recommended)

### Step 1: Install ChromaDB

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install ChromaDB
pip install chromadb>=0.4.0
```

Or install from requirements:

```bash
cd scripts
pip install -r requirements.txt
```

### Step 2: Load Embeddings into ChromaDB

**Important**: ChromaDB needs the JSON array format file (`embeddings-array.json`), NOT the JSONL file (`embeddings.json`).

**File formats:**
- `embeddings-array.json` - JSON array format (from `create_embeddings.py`) - **Use this for ChromaDB**
- `embeddings.json` - JSONL format (from `convert_to_jsonl.py`) - Only for Vertex AI Vector Search

If you don't have `embeddings-array.json`, create it first:
```bash
# From workspace root
# Make sure you have chunks.json from process_docs.py first
python scripts/create_embeddings.py scripts/chunks.json scripts/embeddings-array.json
```

Then load into ChromaDB:
```bash
# From workspace root
python scripts/load_chromadb.py scripts/embeddings-array.json

# Or specify custom collection name and directory
python scripts/load_chromadb.py scripts/embeddings-array.json my_collection ./chroma_db
```

**Note for Windows users**: Use forward slashes in paths, or use backslashes if needed. The Python script handles both.

**What this does:**
- Creates a persistent ChromaDB database in `./chroma_db` (or specified directory)
- Creates a collection named `uplifted_mascot` (or your custom name)
- Loads all embeddings with their text and metadata
- Stores everything locally - no cloud costs!

**Output:**
```
Loading 150 embeddings into ChromaDB...
Adding embeddings to ChromaDB...
✓ Successfully loaded 150 embeddings into ChromaDB
  Collection: uplifted_mascot
  Database location: /path/to/chroma_db
  Total documents in collection: 150
```

### Step 3: Verify Setup

The ChromaDB database is now ready. The RAG service will automatically find and use it.

**Database location:**
- Default: `./chroma_db` (in workspace root)
- The RAG service will search common locations automatically

**Updating embeddings:**
- To update with new documents, just re-run `load_chromadb.py`
- ChromaDB will update the collection (you may want to delete the old collection first)

### Step 4: Configure RAG Service (Optional)

The RAG service uses ChromaDB by default. You can customize via environment variables:

```env
# Optional - defaults shown
CHROMA_COLLECTION_NAME=uplifted_mascot
CHROMA_PERSIST_DIR=./chroma_db
```

## Cost Comparison

| Approach | Monthly Cost | Best For |
|----------|-------------|----------|
| **ChromaDB (Self-hosted)** | **$0** | Development, small datasets (<10K docs) |
| Vertex AI Vector Search | ~$73-547/month | Large datasets, production scaling |

**Recommendation**: Start with ChromaDB. It's free, fast for small datasets, and runs locally. Only move to Vertex AI Vector Search if you need to scale beyond ChromaDB's capabilities.

## Troubleshooting

### Issue: Collection Not Found

**Error**: `ChromaDB collection 'uplifted_mascot' not found`

**Solution**: Run the load script with the correct file:
```bash
# Make sure you're using embeddings-array.json (JSON array format), not embeddings.json (JSONL format)
python scripts/load_chromadb.py scripts/embeddings-array.json
```

**If you get "JSONDecodeError"**: You're using the wrong file. Use `embeddings-array.json` (JSON array), not `embeddings.json` (JSONL).

### Issue: Database Location

The RAG service searches for ChromaDB in these locations (in order):
1. `./chroma_db` (workspace root)
2. `../chroma_db` (parent directory)
3. Path specified in `CHROMA_PERSIST_DIR` environment variable

Make sure your ChromaDB database is in one of these locations, or set `CHROMA_PERSIST_DIR` in your `.env` file.

### Issue: Updating Embeddings

To update with new documents:
1. Re-run the ingestion pipeline to create new embeddings
2. Delete the old ChromaDB collection (or use a new collection name)
3. Re-run `load_chromadb.py`

Or use ChromaDB's update API programmatically.

## Next Steps

Once ChromaDB is set up:
1. **Proceed to RAG Service** - See `04-rag-service.md` to build the API endpoint
2. The RAG service will automatically use ChromaDB - no additional configuration needed!

---

## Scaling with Vertex AI Vector Search

For large datasets (10K+ documents) or production deployments requiring high availability, you can use Google Cloud's Vertex AI Vector Search instead of ChromaDB.

**When to use Vertex AI Vector Search:**
- Very large datasets (100K+ documents)
- Need for managed, scalable infrastructure
- Multi-region deployment requirements
- High query throughput needs

**Cost**: ~$73-547/month depending on machine type (see cost management section)

### Setup Instructions

**Prerequisites**: Set these environment variables in your shell:
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_REGION` - Your region (e.g., `us-east1`)

**On Windows**: Set variables with `set VARIABLE=value` in Command Prompt, or use your `.env` file loader (see `04-rag-service.md`). The `gcloud` commands work the same on Windows.

1. **Create Cloud Storage Bucket**

   First, set a unique bucket name:
   ```bash
   # Linux/Mac: Generate unique name with date
   export BUCKET_NAME="um-embeddings-$(date +%Y%m%d)"
   
   # Windows: Set manually (replace YYYYMMDD with today's date)
   # set BUCKET_NAME=um-embeddings-20241114
   ```

   Then create the bucket:
   ```bash
   gsutil mb -p $GCP_PROJECT_ID -l $GCP_REGION gs://$BUCKET_NAME
   ```

2. **Convert Embeddings to JSONL Format**

   **Important**: Vertex AI requires the file to have a `.json` extension even though the content is JSONL format.

   ```bash
   python scripts/convert_to_jsonl.py embeddings-array.json embeddings.json
   ```

3. **Upload to Cloud Storage**
   ```bash
   gsutil cp embeddings.json gs://$BUCKET_NAME/
   ```

4. **Create Index Configuration**

   Copy the example file and edit it:
   ```bash
   cp config/index-config.yaml.example index-config.yaml
   # On Windows: copy config\index-config.yaml.example index-config.yaml
   ```

   Edit `index-config.yaml` and replace `YOUR_BUCKET_NAME` with your actual bucket name.

5. **Create Index**
   ```bash
   gcloud ai indexes create \
     --project=$GCP_PROJECT_ID \
     --region=$GCP_REGION \
     --display-name="uplifted-mascot-index" \
     --metadata-file=index-config.yaml
   ```

   **Note**: This takes 30-60 minutes. Save the operation ID from the output to check status later.

6. **Create Endpoint and Deploy**

   Create the endpoint:
   ```bash
   gcloud ai index-endpoints create \
     --project=$GCP_PROJECT_ID \
     --region=$GCP_REGION \
     --display-name="um-endpoint"
   ```

   Save the `ENDPOINT_ID` from the output to your `.env` file.

   Deploy the index (use `e2-standard-2` for development to minimize costs):
   ```bash
   gcloud ai index-endpoints deploy-index ENDPOINT_ID \
     --project=$GCP_PROJECT_ID \
     --region=$GCP_REGION \
     --deployed-index-id="um_deployed_index" \
     --display-name="um_deployed_index" \
     --index=INDEX_ID \
     --machine-type="e2-standard-2"
   ```

   Save the `INDEX_ID` from step 5 to your `.env` file.

7. **Configure RAG Service**

   Add to your `.env` file:
   ```env
   VECTOR_INDEX_ID=your-index-id
   VECTOR_ENDPOINT_ID=your-endpoint-id
   DEPLOYED_INDEX_ID=um_deployed_index
   ```

**Note**: The RAG service will automatically use Vertex AI Vector Search if these environment variables are set, otherwise it defaults to ChromaDB.

### Troubleshooting Vertex AI Vector Search

**Issue: `FAILED_PRECONDITION` error when creating index**

Check:
1. **Bucket exists and is accessible:**
   ```bash
   gsutil ls gs://$BUCKET_NAME
   ```

2. **JSON file is uploaded (must have `.json` extension):**
   ```bash
   gsutil ls gs://$BUCKET_NAME/embeddings.json
   ```

3. **Bucket region matches index region:**
   ```bash
   gsutil ls -L -b gs://$BUCKET_NAME | grep Location
   ```

4. **Grant Vertex AI service account access:**
   ```bash
   # Get your project number
   PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format="value(projectNumber)")
   
   # Grant access
   gsutil iam ch serviceAccount:service-$PROJECT_NUMBER@gcp-sa-aiplatform.iam.gserviceaccount.com:roles/storage.objectViewer gs://$BUCKET_NAME
   ```

**Issue: Long creation time**

Normal: Index creation takes 30-60 minutes for large datasets. Check status:
```bash
gcloud ai indexes list --project=$GCP_PROJECT_ID --region=$GCP_REGION
```

### Cost Management

**⚠️ Important: Deployed indexes run 24/7 and can be expensive!**

**Key Point**: The endpoint itself is just a container (no cost). The compute costs come from the deployed index. When you deploy an index to an endpoint, that's when the compute instance starts running. Costs depend on the machine type specified during deployment:
- **e2-standard-2**: ~$0.10/hour (~$73/month) - Recommended
- **e2-standard-16**: ~$0.75/hour (~$547/month) - ⚠️ Very expensive!

**To reduce costs:**

1. **Undeploy index** (stops compute costs, endpoint remains but costs nothing):
   ```bash
   # Undeploy the index (stops compute costs)
   gcloud ai index-endpoints undeploy-index ENDPOINT_ID \
     --project=$GCP_PROJECT_ID \
     --region=$GCP_REGION \
     --deployed-index-id="um_deployed_index"
   
   # When needed again, redeploy with smaller machine type
   gcloud ai index-endpoints deploy-index ENDPOINT_ID \
     --project=$GCP_PROJECT_ID \
     --region=$GCP_REGION \
     --deployed-index-id="um_deployed_index" \
     --display-name="um_deployed_index" \
     --index=INDEX_ID \
     --machine-type="e2-standard-2"
   ```

2. **Delete endpoint when not in use** (stops all costs):
   ```bash
   # Delete the entire endpoint (index data is preserved)
   gcloud ai index-endpoints delete ENDPOINT_ID \
     --project=$GCP_PROJECT_ID \
     --region=$GCP_REGION
   
   # When needed again, recreate endpoint and redeploy index
   ```

### Cost Considerations

- **Index Storage**: ~$0.10 per GB per month (cheap - data storage)
- **Deployed Index Compute**: ~$0.10-0.75/hour depending on machine type (runs 24/7) ⚠️
- **Empty Endpoint**: No cost (endpoint without deployed index costs nothing)
- **Query Operations**: ~$0.10 per 1K queries (very cheap)
- **Your $50 credit**: Will be consumed quickly by endpoint compute costs if using large machine types!

**Recommendation**: Use `e2-standard-2` for development, and undeploy when not actively testing.

# Vector Storage Setup (Windows)

## Overview

Vertex AI Vector Search stores the document embeddings created during ingestion. This is the "brain" of the Uplifted Mascot system - it enables semantic search across your knowledge base.

This guide uses Windows Command Prompt syntax. For PowerShell, most commands are the same, but you can use `$env:VARIABLE` instead of `%VARIABLE%`.

## Prerequisites

- GCP project with Vertex AI API enabled
- Embeddings JSON file from ingestion step (see `02-ingestion.md`)
- `gcloud` CLI configured
- Python environment with required packages

## Initial Setup

### Step 1: Enable Required APIs

**First, load your environment variables from `.env`** (see `04-rag-service.md` for how to load .env in Windows):

```cmd
REM Load environment variables from .env (use PowerShell script or manual set)
REM Or set them manually:
REM set GCP_PROJECT_ID=your-project-id
REM set GCP_REGION=us-east1

REM Set gcloud project
gcloud config set project %GCP_PROJECT_ID%

REM Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage-component.googleapis.com
```

### Step 2: Create Cloud Storage Bucket

Vector Search requires embeddings to be stored in Cloud Storage first.

```cmd
REM Set bucket name (adjust date suffix to make it unique - format: YYYYMMDD)
set BUCKET_NAME=um-embeddings-20251114

REM Create bucket (uses GCP_PROJECT_ID and GCP_REGION from .env)
gsutil mb -p %GCP_PROJECT_ID% -l %GCP_REGION% gs://%BUCKET_NAME%

REM Verify
gsutil ls gs://%BUCKET_NAME%
```

**Note**: Change `20251114` to today's date (YYYYMMDD format) or add a unique suffix to ensure the bucket name is unique. Cloud Storage bucket names must be globally unique across all GCP projects.

## Create Vector Search Index

### Step 3: Convert Embeddings to Vector Search Format

Vector Search requires JSONL format (one JSON object per line) but the file must have a `.json` extension. The conversion script is located at `scripts/convert_to_jsonl.py`.

**Convert embeddings to Vector Search format:**
```cmd
REM Convert to JSONL format with .json extension (Vector Search requires .json extension)
REM Input: embeddings-array.json (from create_embeddings.py)
REM Output: embeddings.json (final file for Vector Search)
python scripts\convert_to_jsonl.py embeddings-array.json embeddings.json
```

**Note:** 
- The input file (`embeddings-array.json`) is the JSON array format from `create_embeddings.py`
- The output file (`embeddings.json`) is JSONL format (one JSON object per line) but must have `.json` extension for Vertex AI
- If you used a different output name from `create_embeddings.py`, adjust the input filename accordingly

### Step 4: Upload Embeddings to Cloud Storage

```cmd
REM Upload JSON file (required for Vector Search - must have .json extension)
gsutil cp embeddings.json gs://%BUCKET_NAME%/

REM Verify upload
gsutil ls gs://%BUCKET_NAME%/
```

### Step 5: Prepare Index Configuration

Copy the example configuration file from `config/index-config.yaml.example` and update it with your bucket name:

```cmd
REM Copy example config
copy config\index-config.yaml.example index-config.yaml

REM Edit the file and replace YOUR_BUCKET_NAME with your actual bucket name
REM You can use notepad:
notepad index-config.yaml
```

**Update the file**: Change `YOUR_BUCKET_NAME` to your actual bucket name (e.g., `um-embeddings-1234567890`).

### Step 6: Create Index Script

The index creation script is located at `scripts/create_index.py` in this repository.

## Alternative: Simplified Approach (Manual Index Creation)

For initial testing, you can use the `gcloud` CLI:

### Step 7: Create Index Configuration File

Create `index-config.yaml` manually or use this PowerShell command:

```powershell
# PowerShell version
@"
config:
  dimensions: 768
  approximateNeighborsCount: 10
  distanceMeasureType: "DOT_PRODUCT_DISTANCE"
  algorithmConfig:
    treeAhConfig:
      leafNodeEmbeddingCount: 500
      fractionLeafNodesToSearch: 0.05
contentsDeltaUri: "gs://YOUR_BUCKET_NAME/"
"@ | Out-File -FilePath index-config.yaml -Encoding utf8
```

**Or create it manually** with notepad and paste this content (replace `YOUR_BUCKET_NAME`):

```yaml
config:
  dimensions: 768
  approximateNeighborsCount: 10
  distanceMeasureType: "DOT_PRODUCT_DISTANCE"
  algorithmConfig:
    treeAhConfig:
      leafNodeEmbeddingCount: 500
      fractionLeafNodesToSearch: 0.05
contentsDeltaUri: "gs://YOUR_BUCKET_NAME/"
```

**Note:** The `displayName` is specified via the `--display-name` flag in the `gcloud` command, not in this YAML file.

### Step 8: Create Index via gcloud

```cmd
REM Create index (this takes 30+ minutes)
gcloud ai indexes create ^
  --project=%GCP_PROJECT_ID% ^
  --region=%REGION% ^
  --display-name="uplifted-mascot-index" ^
  --metadata-file=index-config.yaml
```

**Note**: Index creation is asynchronous and can take 30-60 minutes for large datasets.

The command will return an operation ID. Save it to check status later.

### Step 9: Check Operation Status

After running the create command, you'll get an operation ID. Check its status:

```cmd
REM Check operation status (replace OPERATION_ID with value from create command)
REM INDEX_ID comes from %VECTOR_INDEX_ID% environment variable
gcloud ai operations describe OPERATION_ID ^
  --index=%VECTOR_INDEX_ID% ^
  --region=%GCP_REGION% ^
  --project=%GCP_PROJECT_ID% ^
  --format="json(done,error,response)"

REM Or get full operation details in JSON
gcloud ai operations describe OPERATION_ID ^
  --index=%VECTOR_INDEX_ID% ^
  --region=%GCP_REGION% ^
  --project=%GCP_PROJECT_ID% ^
  --format=json
```

**Status indicators:**
- `done: false` = Still in progress
- `done: true` with no `error` = Successfully completed
- `done: true` with `error` = Failed (check error details)

**Troubleshooting `FAILED_PRECONDITION` errors:**

If you see `FAILED_PRECONDITION` (error code 9), check:

1. **Verify bucket exists and is in the correct region:**
   ```cmd
   gsutil ls -b gs://%BUCKET_NAME%
   gsutil ls gs://%BUCKET_NAME%/
   ```

2. **Ensure JSON file is uploaded (must have .json extension):**
   ```cmd
   REM Check if embeddings.json exists in bucket
   gsutil ls gs://%BUCKET_NAME%/embeddings.json
   ```

3. **Verify bucket region matches index region:**
   ```cmd
   REM Check bucket location (should match your GCP_REGION)
   gsutil ls -L -b gs://%BUCKET_NAME% | findstr "Location"
   ```

4. **Grant Vertex AI service account access to bucket:**
   ```cmd
   REM Get your project number
   gcloud projects describe %GCP_PROJECT_ID% --format="value(projectNumber)"
   
   REM Grant storage.objectViewer role to Vertex AI service account
   REM Replace PROJECT_NUMBER with the number from above
   gsutil iam ch serviceAccount:service-PROJECT_NUMBER@gcp-sa-aiplatform.iam.gserviceaccount.com:roles/storage.objectViewer gs://%BUCKET_NAME%
   ```

5. **Common fixes:**
   - Create the bucket if it doesn't exist: `gsutil mb -l %GCP_REGION% gs://%BUCKET_NAME%`
   - Re-upload the JSON file with `.json` extension: `gsutil cp embeddings.json gs://%BUCKET_NAME%/`
   - **Important:** File must have `.json` extension even though content is JSONL format
   - Ensure bucket and index are in the same region (match %GCP_REGION%)
   - Grant Vertex AI service account permission to read the bucket (see step 4 above)

### Step 10: Check Index Status (After Creation Completes)

Once the operation completes, you can check the index:

```cmd
REM List indexes
gcloud ai indexes list --project=%GCP_PROJECT_ID% --region=%GCP_REGION%

REM Get index details (uses VECTOR_INDEX_ID from .env)
gcloud ai indexes describe %VECTOR_INDEX_ID% ^
  --project=%GCP_PROJECT_ID% ^
  --region=%GCP_REGION%
```

## Query the Index (Testing)

### Step 11: Test Query Script

The query script is located at `scripts/query_index.py` in this repository.

**Test query:**
```cmd
python scripts\query_index.py %GCP_PROJECT_ID% %GCP_REGION% %VECTOR_INDEX_ID% "What is the API?" 5
```

## Manual Workflow Summary

```cmd
REM 1. Setup (load variables from .env first - see 04-rag-service.md)
REM Variables needed: GCP_PROJECT_ID, GCP_REGION, VECTOR_INDEX_ID, VECTOR_ENDPOINT_ID
REM Set bucket name (adjust date suffix YYYYMMDD to make unique)
set BUCKET_NAME=um-embeddings-20241215

REM 2. Create bucket
gsutil mb -p %GCP_PROJECT_ID% -l %GCP_REGION% gs://%BUCKET_NAME%

REM 3. Convert to JSONL format (with .json extension - Vector AI requires .json extension)
REM Input: embeddings-array.json (from create_embeddings.py)
REM Output: embeddings.json (final file for Vector Search)
python scripts\convert_to_jsonl.py embeddings-array.json embeddings.json

REM 4. Upload JSON file to bucket (must have .json extension even though content is JSONL)
gsutil cp embeddings.json gs://%BUCKET_NAME%/

REM 5. Create index (takes 30+ minutes)
REM First, create/edit index-config.yaml with your bucket name
gcloud ai indexes create ^
  --project=%GCP_PROJECT_ID% ^
  --region=%GCP_REGION% ^
  --display-name="uplifted-mascot-index" ^
  --metadata-file=index-config.yaml

REM 6. Check status and save INDEX_ID to .env as VECTOR_INDEX_ID
gcloud ai indexes list --project=%GCP_PROJECT_ID% --region=%GCP_REGION%

REM 7. Save the INDEX_ID to your .env file as VECTOR_INDEX_ID
```

## Important Notes

### Index Deployment

After creating an index, you need to deploy it to an endpoint before querying. **This step is required before setting up the RAG service.**

#### Step 1: Create an Endpoint

```cmd
REM Create endpoint (this creates a new endpoint)
gcloud ai index-endpoints create ^
  --project=%GCP_PROJECT_ID% ^
  --region=%GCP_REGION% ^
  --display-name="um-endpoint"
```

**Save the ENDPOINT_ID** from the output to your `.env` file as `VECTOR_ENDPOINT_ID`. It will look like: `1234567890123456789`

#### Step 2: Deploy Index to Endpoint

```cmd
REM Uses VECTOR_ENDPOINT_ID and VECTOR_INDEX_ID from .env
REM Note: deployed-index-id must start with a letter and contain only letters, numbers, and underscores
gcloud ai index-endpoints deploy-index %VECTOR_ENDPOINT_ID% ^
  --project=%GCP_PROJECT_ID% ^
  --region=%GCP_REGION% ^
  --deployed-index-id="um_deployed_index" ^
  --display-name="um_deployed_index" ^
  --index=%VECTOR_INDEX_ID%
```

**Save the operation ID** from the output. The output will show something like:
```
The deploy index operation [projects/.../operations/3522546152555675648] was submitted successfully.
```

The operation ID is the last number in that path (e.g., `3522546152555675648`). Set it as a variable:

```cmd
REM Set the operation ID from the deploy command output
set DEPLOY_OPERATION_ID=3522546152555675648
```

**Note**: Deployment can take 10-30 minutes. 

Get full JSON output:

```cmd
gcloud ai operations describe %DEPLOY_OPERATION_ID% ^
  --index-endpoint=%VECTOR_ENDPOINT_ID% ^
  --region=%GCP_REGION% ^
  --project=%GCP_PROJECT_ID% ^
  --format=json
```

**Status indicators:**
- `done: false` = Still in progress
- `done: true` with no `error` = Successfully completed
- `done: true` with `error` = Failed (check error details)

#### Step 3: Verify Deployment

First, list your endpoints to get the endpoint ID:

```cmd
REM List your endpoints (this shows all endpoint IDs)
gcloud ai index-endpoints list ^
  --project=%GCP_PROJECT_ID% ^
  --region=%GCP_REGION%
```

**Get endpoint details** (uses VECTOR_ENDPOINT_ID from .env):

```cmd
gcloud ai index-endpoints describe %VECTOR_ENDPOINT_ID% ^
  --project=%GCP_PROJECT_ID% ^
  --region=%GCP_REGION%
```

**Verify your .env file has both IDs:**
- `VECTOR_INDEX_ID`: Your index ID
- `VECTOR_ENDPOINT_ID`: Your endpoint ID

### Cost Considerations

- **Index Storage**: ~$0.10 per GB per month
- **Query Operations**: ~$0.10 per 1K queries
- **Your $50 credit**: Should handle significant usage for development

## Troubleshooting

### Issue: Index Creation Fails

**Check**:
- Bucket exists and is accessible: `gsutil ls gs://%BUCKET_NAME%`
- JSON file with JSONL content format is correct (must have .json extension)
- Embedding dimensions match (768 for text-embedding-004)

### Issue: Long Creation Time

**Normal**: Index creation can take 30-60 minutes for large datasets. Check status periodically:
```cmd
gcloud ai indexes list --project=%GCP_PROJECT_ID% --region=%GCP_REGION%
```

### Issue: Query Errors

**Solution**: Ensure index is deployed to an endpoint before querying.

### Issue: Environment Variables Not Persisting

**Solution**: Load variables from `.env` file. See `04-rag-service.md` for methods to load `.env` in Windows (PowerShell script or batch file). Variables loaded from `.env` will persist for that command prompt session.

## Next Steps

Once your index is created and deployed:

1. **Note the Index ID and Endpoint ID** - You'll need these for the RAG service
2. **Proceed to RAG Service** - See `04-rag-service.md` to build the API endpoint

## Save Configuration

Create a config file with your setup using notepad or PowerShell:

**Using PowerShell:**
```powershell
@"
{
  "project_id": "$env:GCP_PROJECT_ID",
  "region": "$env:GCP_REGION",
  "bucket_name": "YOUR_BUCKET_NAME",
  "index_id": "$env:VECTOR_INDEX_ID",
  "endpoint_id": "$env:VECTOR_ENDPOINT_ID",
  "deployed_index_id": "um_deployed_index"
}
"@ | Out-File -FilePath vector-config.json -Encoding utf8
```

**Or create manually** with notepad and save as `vector-config.json` (replace with your actual values):
```json
{
  "project_id": "your-project-id",
  "region": "us-east1",
  "bucket_name": "your-bucket-name",
  "index_id": "your-index-id",
  "endpoint_id": "your-endpoint-id",
  "deployed_index_id": "um_deployed_index"
}
```

**Note**: Your `.env` file already contains these values, so this config file is optional.

## Quick Reference: Windows Command Equivalents

| Linux/Bash | Windows CMD |
|------------|-------------|
| `export VAR=value` | `set VAR=value` |
| `$VAR` | `%VAR%` |
| `~/path` | `%USERPROFILE%\path` |
| `cat > file` | `notepad file` (manual) or PowerShell `@""@ \| Out-File` |
| `cp file dest` | `copy file dest` |
| `\` (line continuation) | `^` (line continuation) |
| `$(date +%s)` | `powershell -Command "Get-Date -UFormat %%s"` |

## Working Directory

If you're working from the `scripts/` directory:

```cmd
REM If you're in scripts directory:
cd scripts
REM Convert: embeddings-array.json -> embeddings.json (JSONL format with .json extension)
python convert_to_jsonl.py embeddings-array.json embeddings.json
gsutil cp embeddings.json gs://%BUCKET_NAME%/
```

If you're working from the workspace root:
```cmd
REM From workspace root:
python scripts\convert_to_jsonl.py embeddings-array.json embeddings.json
gsutil cp embeddings.json gs://%BUCKET_NAME%/
copy config\index-config.yaml.example index-config.yaml
```


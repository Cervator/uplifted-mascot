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

```cmd
REM Set your project
set GCP_PROJECT_ID=teralivekubernetes
gcloud config set project %GCP_PROJECT_ID%

REM Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage-component.googleapis.com
```

### Step 2: Create Cloud Storage Bucket

Vector Search requires embeddings to be stored in Cloud Storage first.

```cmd
REM Set variables
REM Adjust the date suffix below to make it unique (format: YYYYMMDD)
set BUCKET_NAME=um-embeddings-20251114
set REGION=us-east1

REM Create bucket
gsutil mb -p %GCP_PROJECT_ID% -l %REGION% gs://%BUCKET_NAME%

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
REM Check operation status (replace OPERATION_ID and INDEX_ID with values from create command)
gcloud ai operations describe OPERATION_ID ^
  --index=INDEX_ID ^
  --region=%REGION% ^
  --project=%GCP_PROJECT_ID% ^
  --format="json(done,error,response)"

REM Or get full operation details in JSON
gcloud ai operations describe OPERATION_ID ^
  --index=INDEX_ID ^
  --region=%REGION% ^
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
   REM Check bucket location (should match your REGION, e.g., us-east1)
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
   - Create the bucket if it doesn't exist: `gsutil mb -l us-east1 gs://%BUCKET_NAME%`
   - Re-upload the JSON file with `.json` extension: `gsutil cp embeddings.json gs://%BUCKET_NAME%/`
   - **Important:** File must have `.json` extension even though content is JSONL format
   - Ensure bucket and index are in the same region (us-east1)
   - Grant Vertex AI service account permission to read the bucket (see step 4 above)

### Step 10: Check Index Status (After Creation Completes)

Once the operation completes, you can check the index:

```cmd
REM List indexes
gcloud ai indexes list --project=%GCP_PROJECT_ID% --region=%REGION%

REM Get index details (replace INDEX_ID with actual ID from list above)
gcloud ai indexes describe INDEX_ID ^
  --project=%GCP_PROJECT_ID% ^
  --region=%REGION%
```

## Query the Index (Testing)

### Step 11: Test Query Script

The query script is located at `scripts/query_index.py` in this repository.

**Test query:**
```cmd
python scripts\query_index.py teralivekubernetes us-east1 INDEX_ID "What is the API?" 5
```

## Manual Workflow Summary

```cmd
REM 1. Setup
set GCP_PROJECT_ID=teralivekubernetes
set REGION=us-east1
REM Adjust date suffix (YYYYMMDD format) to make unique
set BUCKET_NAME=um-embeddings-20241215

REM 2. Create bucket
gsutil mb -p %GCP_PROJECT_ID% -l %REGION% gs://%BUCKET_NAME%

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
  --region=%REGION% ^
  --display-name="uplifted-mascot-index" ^
  --metadata-file=index-config.yaml

REM 6. Check status
gcloud ai indexes list --project=%GCP_PROJECT_ID% --region=%REGION%

REM 7. Note the INDEX_ID for use in RAG service
```

## Important Notes

### Index Deployment

After creating an index, you need to deploy it to an endpoint before querying:

```cmd
REM Create endpoint
gcloud ai index-endpoints create ^
  --project=%GCP_PROJECT_ID% ^
  --region=%REGION% ^
  --display-name="um-endpoint"

REM Deploy index to endpoint (replace ENDPOINT_ID and INDEX_ID)
gcloud ai index-endpoints deploy-index ENDPOINT_ID ^
  --project=%GCP_PROJECT_ID% ^
  --region=%REGION% ^
  --deployed-index-id="um-deployed-index" ^
  --index=INDEX_ID
```

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
gcloud ai indexes list --project=%GCP_PROJECT_ID% --region=%REGION%
```

### Issue: Query Errors

**Solution**: Ensure index is deployed to an endpoint before querying.

### Issue: Environment Variables Not Persisting

**Solution**: In Command Prompt, variables only last for that session. To make them persistent:
```cmd
REM Use setx (note: requires new command prompt to take effect)
setx GCP_PROJECT_ID "teralivekubernetes"
setx REGION "us-east1"
```

Or create a batch file (`setup-env.bat`):
```cmd
@echo off
set GCP_PROJECT_ID=teralivekubernetes
set REGION=us-east1
set BUCKET_NAME=um-embeddings-teralivekubernetes
```

Then run: `setup-env.bat` before other commands.

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
  "project_id": "teralivekubernetes",
  "region": "us-east1",
  "bucket_name": "YOUR_BUCKET_NAME",
  "index_id": "YOUR_INDEX_ID",
  "endpoint_id": "YOUR_ENDPOINT_ID",
  "deployed_index_id": "um-deployed-index"
}
"@ | Out-File -FilePath vector-config.json -Encoding utf8
```

**Or create manually** with notepad and save as `vector-config.json`:
```json
{
  "project_id": "teralivekubernetes",
  "region": "us-east1",
  "bucket_name": "YOUR_BUCKET_NAME",
  "index_id": "YOUR_INDEX_ID",
  "endpoint_id": "YOUR_ENDPOINT_ID",
  "deployed_index_id": "um-deployed-index"
}
```

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


# Vertex AI Vector Search Index Creation - FAILED_PRECONDITION Error

## Context
Attempting to create a Vertex AI Vector Search index using `gcloud ai indexes create` command. The operation completes but fails with `FAILED_PRECONDITION` (error code 9).

## Configuration Details

**Project:** `teralivekubernetes`
**Region:** `us-east1`
**Index Display Name:** `uplifted-mascot-index`

**Index Configuration (index-config.yaml):**
```yaml
config:
  dimensions: 768
  approximateNeighborsCount: 10
  distanceMeasureType: "DOT_PRODUCT_DISTANCE"
  algorithmConfig:
    treeAhConfig:
      leafNodeEmbeddingCount: 500
      fractionLeafNodesToSearch: 0.05
contentsDeltaUri: "gs://um-embeddings-20251114/"
```

**Cloud Storage:**
- Bucket: `gs://um-embeddings-20251114/`
- Bucket Region: `US-EAST1` (confirmed - matches index region)
- File: `embeddings.jsonl` exists in bucket root
- File Format: Valid JSONL with structure:
  - `id`: string identifier
  - `embedding`: array of 768 floats
  - `metadata`: object with file_path, filename, chunk_index, text

**Authentication:**
- Using `gcloud` CLI with primary user account (not service account)
- Account: `cervator@gmail.com`
- Project set via: `gcloud config set project teralivekubernetes`

## Error Details

**Operation Status:**
```json
{
  "done": true,
  "error": {
    "code": 9,
    "message": "FAILED_PRECONDITION"
  }
}
```

**Command Used:**
```bash
gcloud ai indexes create \
  --project=teralivekubernetes \
  --region=us-east1 \
  --display-name="uplifted-mascot-index" \
  --metadata-file=index-config.yaml
```

## What's Verified
✅ Bucket exists and is accessible
✅ File `embeddings.jsonl` exists in bucket
✅ Bucket region (US-EAST1) matches index region (us-east1)
✅ JSONL file format appears correct (768-dim embeddings, proper structure)
✅ Index config YAML structure is correct (no metadata wrapper, config and contentsDeltaUri at top level)

## Potential Issues to Investigate

1. **IAM Permissions:**
   - Does the user account have `roles/aiplatform.admin` or `roles/aiplatform.user`?
   - Does the account have `storage.objects.get` permission on the bucket?
   - Are there any bucket-level IAM restrictions?

2. **File Format Validation:**
   - Does Vertex AI Vector Search validate the JSONL structure more strictly?
   - Are there any required fields missing in the metadata?
   - Is the embedding array length exactly 768 for all entries?

3. **Bucket Path:**
   - Should `contentsDeltaUri` point to a specific subdirectory?
   - Does Vector Search expect the file at a specific path pattern?

4. **Service Account vs User Account:**
   - Are there differences in how Vertex AI handles user accounts vs service accounts?
   - Does the operation require a service account even when using gcloud CLI?

5. **API Enablement:**
   - Is the Vertex AI API enabled for the project?
   - Is the Vector Search API specifically enabled?

## Questions for Gemini

1. What are the most common causes of `FAILED_PRECONDITION` (code 9) when creating Vertex AI Vector Search indexes?

2. Are there specific IAM permissions required beyond the standard Vertex AI roles when creating indexes that reference Cloud Storage buckets?

3. Does the `contentsDeltaUri` path format matter? Should it be:
   - `gs://bucket-name/` (directory)
   - `gs://bucket-name/embeddings.jsonl` (specific file)
   - Something else?

4. Are there any validation requirements for the JSONL file that might not be obvious from the documentation? (e.g., field names, data types, array lengths)

5. When using `gcloud` CLI with a user account (not service account), are there any additional steps or permissions needed for Vector Search index creation?

6. How can I get more detailed error information beyond just "FAILED_PRECONDITION"? Are there logs or additional error details available?


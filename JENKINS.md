# Jenkins CI/CD Setup

## Overview

This guide covers setting up Jenkins CI/CD for the Uplifted Mascot system, including building Docker images, pushing to GAR (Google Artifact Registry), and deploying to Kubernetes.

## Prerequisites

- Jenkins running in Kubernetes cluster
- Docker build agent with label `docker`
- kubectl agent with label `kubectl` and `utility` container
- **Python build agent with label `python` and `builder` container** (for ingestion pipeline)
- GCP credentials configured in Jenkins
- nginx ingress controller installed
- GAR (Google Artifact Registry) repository created

## Jenkins Configuration

### 1. Install Required Plugins

- Docker Pipeline
- Kubernetes CLI
- Credentials Binding

### 2. Configure Credentials

In Jenkins, add the following credentials:

**GCP Project ID** (Secret text):
- ID: `gcp-project-id`
- Secret: Your GCP project ID (e.g., `teralivekubernetes`)

**GAR Service Account** (Secret file):
- ID: `jenkins-gar-sa` (matches Jenkinsfile)
- File: GCP service account JSON key with permissions to push to GAR
- Grant roles: `Artifact Registry Writer`, `Storage Admin`
- Used for `withCredentials` authentication to push Docker images

**Kubernetes kubeconfig** (Secret file):
- ID: `utility-admin-kubeconfig-sa-token` (matches Jenkinsfile)
- File: Your kubeconfig file or service account token
- Used for `withKubeConfig` authentication

### 3. Configure Kubernetes Access

The Jenkinsfile uses `withKubeConfig` with credential ID `utility-admin-kubeconfig-sa-token`. 

**Setup kubeconfig credential:**
- In Jenkins: Credentials → Add → Secret file
- ID: `utility-admin-kubeconfig-sa-token`
- File: Your kubeconfig file or service account token

**Or use Workload Identity** (if Jenkins runs in GKE):
- No kubeconfig needed - uses service account automatically
- Update credential ID in Jenkinsfile if different

### 4. Configure Jenkins Agent Service Account (for Ingestion Pipeline)

**Important**: The ingestion pipeline (`ingestion.Jenkinsfile`) needs to authenticate to Vertex AI via Workload Identity. Configure the Jenkins agent pod template to use the `um-vertex-ai-sa` service account.

**In Jenkins Kubernetes Plugin configuration:**

1. Go to **Manage Jenkins** → **Configure System** → **Cloud** → **Kubernetes**
2. Find your pod template with label `python` (or create one)
3. Under **Pod Template** → **Service Account**, set: `um-vertex-ai-sa`
4. This allows the `builder` container to authenticate to Vertex AI APIs via Workload Identity

**Why this is needed:**
- The ingestion pipeline runs `create_embeddings.py` which calls Vertex AI Embeddings API
- Workload Identity allows the pod to authenticate as `um-vertex-ai-sa@teralivekubernetes.iam.gserviceaccount.com`
- No service account keys needed - authentication is automatic

**Note**: Make sure Workload Identity is enabled and the service account is properly bound (see `k8s/README.md` for setup steps).

## Pipeline Setup

### 1. Create Jenkins Pipeline

1. In Jenkins, create a new "Pipeline" job
2. Point it to your Git repository
3. Set branch: `main` or `master`
4. Pipeline script: `Jenkinsfile` (from repository root)

**Note**: The pipeline uses:
- Agent label: `docker` (for Docker build/push stages)
- Agent label: `kubectl` (for Kubernetes deployment stage - switches agents)
- Container: `utility` (for kubectl operations with `withKubeConfig`)
- Workspace persists between agent switches (Jenkins handles this)
- GAR (Google Artifact Registry) instead of GCR (more modern)
- Tag logic: `latest` for main/master branch, `BRANCH_NAME-BUILD_NUMBER` for others

### 2. Adjust Jenkinsfile

Edit `Jenkinsfile` and update:
- `K8S_NAMESPACE`: Your target namespace
- `GAR_REPOSITORY`: Your GAR repository name (default: `uplifted-mascot`)
- `GCP_REGION`: Your GCP region (default: `us-east1`)

**Note**: The pipeline uses GAR (Google Artifact Registry) format:
- `us-east1-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE:TAG`
- Make sure the GAR repository exists in your GCP project

### 3. First-Time Setup

Before the first pipeline run, you only need to do these one-time steps:

1. **Enable Workload Identity** (see `k8s/README.md` step 1):
   - Enable on cluster
   - Create and bind service accounts

2. **Create GAR repository** (if not exists):
   ```bash
   gcloud artifacts repositories create uplifted-mascot --repository-format=docker --location=us-east1 --project=teralivekubernetes
   ```

**That's it!** The Jenkins pipeline will automatically:
- Create namespace (if needed)
- Deploy ChromaDB (PVC, deployment, service)
- Build and deploy RAG service
- Create/update frontend ConfigMap
- Deploy frontend
- Deploy ingress

**Note**: ChromaDB data is populated by a separate Jenkins ingestion job (see ingestion documentation in the doc repo).

## Pipeline Stages

The Jenkinsfile includes these stages:

1. **Checkout**: Get code from Git
2. **Build Docker**: Build Docker image in `rag-service/` directory
3. **Push Docker**: Authenticate with GAR and push image to registry
4. **k8s deploy**: 
   - Switch to kubectl agent
   - Create namespace (if needed)
   - Update deployment YAML with actual image name
   - Create/update frontend ConfigMap (from `frontend/index.html` and `frontend/widget.html`)
   - Deploy ChromaDB (PVC, deployment, service)
   - Deploy RAG service
   - Deploy frontend
   - Deploy ingress
   - Wait for rollouts and show status

## Ingestion Pipeline Setup

The ingestion pipeline (`ingestion.Jenkinsfile`) runs in documentation repositories to automatically update ChromaDB when markdown files change.

### Setup Ingestion Pipeline

1. **Copy `ingestion.Jenkinsfile`** to your documentation repository
2. **Create a new Jenkins Pipeline job**:
   - Point to your documentation repository
   - Set branch: `main` or `master`
   - Pipeline script: `ingestion.Jenkinsfile`
   - Configure webhook or polling to trigger on git push

3. **Verify agent configuration**:
   - Agent label: `python`
   - Container: `builder`
   - Service account: `um-vertex-ai-sa` (configured in Jenkins pod template - see step 4 above)

**The pipeline will**:
- Clone the repository
- Process markdown files (`process_docs.py`)
- Create embeddings via Vertex AI (`create_embeddings.py`)
- Load embeddings into ChromaDB service (`load_chromadb.py`)

**Note**: The ingestion pipeline connects directly to the `chromadb` service at `chromadb:8000` since Jenkins runs in the same Kubernetes cluster. No kubectl or port-forwarding needed.

## Troubleshooting

### Build Fails: Python Version

If Python 3.9.6 has issues, you can:
- Use a different base image in Dockerfile
- Or update the Jenkins build agent image

### Push Fails: GAR Authentication

**Error**: `unauthorized: You don't have the required permissions`

**Solutions**:
1. Verify `jenkins-gar-sa` credential exists and contains valid service account JSON
2. Check service account has `Artifact Registry Writer` role:
   ```bash
   gcloud projects add-iam-policy-binding teralivekubernetes \
     --member="serviceAccount:YOUR_SA@teralivekubernetes.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"
   ```
3. Verify GAR repository exists:
   ```bash
   gcloud artifacts repositories list --location=us-east1 --project=teralivekubernetes
   ```

### Deployment Fails: Image Pull

- Verify image exists:
  ```bash
  gcloud artifacts docker images list us-east1-docker.pkg.dev/teralivekubernetes/uplifted-mascot/um-rag-service
  ```
- Check image pull secrets if using private registry
- Verify GKE nodes have access to GAR (usually automatic with Workload Identity)

### ChromaDB Not Found

- Verify PVC is created: `kubectl get pvc -n your-namespace`
- Check PVC is mounted: `kubectl describe pod -l app=um-rag-service`
- Verify ChromaDB data exists in PVC

## Continuous Updates

The pipeline will:
- Trigger on Git push (if configured)
- Build new Docker image
- Push to GAR with tag: `latest` for main/master branch, `BRANCH_NAME-BUILD_NUMBER` for others
- Update Kubernetes deployment YAML with actual image name
- Apply all Kubernetes manifests
- Roll out new version

**Image naming**:
- Main/master branch: `us-east1-docker.pkg.dev/teralivekubernetes/uplifted-mascot/um-rag-service:latest`
- Other branches: `us-east1-docker.pkg.dev/teralivekubernetes/uplifted-mascot/um-rag-service:BRANCH-BUILD_NUMBER`

To trigger manually: Click "Build Now" in Jenkins.

## Monitoring

Check deployment status:
```bash
kubectl get pods -l app=um-rag-service -n your-namespace
kubectl logs -l app=um-rag-service -n your-namespace
kubectl get ingress -n your-namespace
```


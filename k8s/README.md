# Kubernetes Deployment Guide

## Overview

This guide covers deploying the Uplifted Mascot system to Kubernetes. **Everything runs online independently from your local workspace** - you only need to create secrets once, then Jenkins handles all builds and deployments.

**Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                       │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  ChromaDB    │    │ RAG Service  │    │  Frontend    │   │
│  │  (Standalone │    │  (FastAPI)   │    │  (Nginx)     │   │
│  │   Pod)       │    │  (Pod)       │    │  (Pod)       │   │
│  │              │    │              │    │              │   │
│  │ Port: 8000   │◄───┤ Port: 8000   │◄───┤ Port: 80     │   │
│  │              │    │              │    │              │   │
│  │ PVC: 5Gi     │    │ Connects via │    │ Proxies /api │   │
│  │ (persistent) │    │ HTTP to      │    │ to RAG       │   │
│  └──────────────┘    │ ChromaDB     │    └──────┬───────┘   │
│         ▲            └──────────────┘           │           │
│         │                                       │           │
│         │ (Ingestion job loads embeddings)      │           │
│         │                                       │           │
│  ┌──────┴───────────────────────────────────-───┴─────────┐ │
│  │              Ingress (HTTPS)                           │ │
│  │         mascot.terasology.io                           │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────-┘
```

**Components**:
- **ChromaDB**: **Standalone service** in its own pod with persistent storage (PVC). Runs as a separate deployment with ClusterIP service accessible at `chromadb:8000` within the cluster.
- **RAG Service**: Separate pod running FastAPI. Connects to ChromaDB via HTTP (using `chromadb:8000` service name). Exposed as ClusterIP service `um-rag-service:80` (internal only).
- **Frontend**: Nginx pod serving static HTML. Proxies `/api/*` requests to the RAG service. Exposed via Ingress.
- **Ingress**: Exposes frontend via HTTPS to the internet. Routes `/` to frontend, which then proxies `/api/*` to RAG service.

**Data Flow**:
1. **Ingestion** (Jenkins job on git push): Creates embeddings → Loads into ChromaDB service via HTTP
2. **Query** (User): Browser → Ingress → Frontend → RAG Service → ChromaDB Service → Returns answer

## Prerequisites

- Kubernetes cluster with kubectl access
- nginx ingress controller installed
- cert-manager (optional, for TLS certificates)
- GAR (Google Artifact Registry) repository created
- Jenkins configured (see `JENKINS.md`)
- **One-time**: Create Kubernetes secrets (see below)

## Quick Setup

**The Jenkins pipeline handles all deployments automatically!** You only need to do one-time setup:

1. **Enable Workload Identity** (see step 1 below) - one-time cluster configuration
2. **Create GAR repository** (see step 4 below) - one-time
3. **Run Jenkins pipeline** - it will deploy everything:
   - ChromaDB (PVC, deployment, service)
   - RAG Service (with latest image)
   - Frontend (with ConfigMap)
   - Ingress

**Important**: ChromaDB data is populated by a separate Jenkins ingestion job (see ingestion documentation in the doc repo).

## Manual Setup Steps

### 1. Enable Workload Identity (One-Time Setup)

**Workload Identity allows pods to authenticate to GCP services without service account keys.**

**Step 1: Enable Workload Identity on your cluster:**
```bash
gcloud container clusters update ttf-cluster \
  --zone=us-east1-d \
  --workload-pool=teralivekubernetes.svc.id.goog \
  --project=teralivekubernetes
```

Looks like it may also need the following? Was "workload-pool" meant to be changed in the above command? It seemed like it worked, could even validate it somehow.

```bash
gcloud container node-pools update default-pool --cluster=ttf-cluster --zone=us-east1-d --project=teralivekubernetes --workload-metadata=GKE_METADATA
```

**Step 2: Draw the rest of the owl**:

Just all the commands used in a GCP cloud terminal, assuming `utility-admin` already existed in `kube-system`:

```bash
# This initial new SA is for running pods in the "um" namespace that need to talk to Vertex AI (Gemini API)
kubectl create serviceaccount um-vertex-ai-sa --namespace um
gcloud iam service-accounts create utility-admin-gsa --project=teralivekubernetes --display-name="Utility Admin GSA"
gcloud iam service-accounts create um-vertex-ai-gsa --project=teralivekubernetes --display-name="UM Vertex AI GSA"
gcloud projects add-iam-policy-binding teralivekubernetes --member="serviceAccount:utility-admin-gsa@teralivekubernetes.iam.gserviceaccount.com" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding teralivekubernetes --member="serviceAccount:utility-admin-gsa@teralivekubernetes.iam.gserviceaccount.com" --role="roles/storage.objectViewer"
gcloud projects add-iam-policy-binding teralivekubernetes --member="serviceAccount:um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding teralivekubernetes --member="serviceAccount:um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com" --role="roles/storage.objectViewer"
gcloud iam service-accounts add-iam-policy-binding "utility-admin-gsa@teralivekubernetes.iam.gserviceaccount.com" --role "roles/iam.workloadIdentityUser" --member "serviceAccount:teralivekubernetes.svc.id.goog[kube-system/utility-admin]" 
gcloud iam service-accounts add-iam-policy-binding "um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com" --role "roles/iam.workloadIdentityUser" --member "serviceAccount:teralivekubernetes.svc.id.goog[um/um-vertex-ai-sa]"
kubectl annotate serviceaccount utility-admin --namespace kube-system iam.gke.io/gcp-service-account=utility-admin-gsa@teralivekubernetes.iam.gserviceaccount.com 
kubectl annotate serviceaccount um-vertex-ai-sa --namespace um iam.gke.io/gcp-service-account=um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com 

# Create and annotate the vertex SA in the jenkins namespace so we can use it on build agents (for embeddings)
kubectl create serviceaccount um-vertex-ai-sa --namespace jenkins
kubectl annotate serviceaccount um-vertex-ai-sa --namespace jenkins iam.gke.io/gcp-service-account=um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com
gcloud iam service-accounts add-iam-policy-binding "um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com" --role "roles/iam.workloadIdentityUser" --member "serviceAccount:teralivekubernetes.svc.id.goog[jenkins/um-vertex-ai-sa]"
```

### 2. Deploy ChromaDB Service and PVC

**ChromaDB runs as a separate service** with its own persistent volume. The PVC is included in the same manifest:

```bash
kubectl apply -f k8s/chromadb.yaml -n your-namespace
```

This creates:
- ChromaDB PersistentVolumeClaim (5Gi storage)
- ChromaDB deployment (mounts the PVC at `/chroma/chroma`)
- ChromaDB service (ClusterIP, accessible at `chromadb:8000`)

**Verify PVC is created and bound:**
```bash
kubectl get pvc chromadb-pvc -n your-namespace
# Should show STATUS: Bound
```

**Verify ChromaDB pod has mounted the volume:**
```bash
kubectl describe pod -l app=chromadb -n your-namespace | grep -A 5 "Mounts:"
# Should show /chroma/chroma mounted from chromadb-data
```

**How embeddings get into ChromaDB:**

When your documentation repository receives a git push, a **separate Jenkins ingestion pipeline** (using `ingestion.Jenkinsfile` in the doc repo) automatically:

1. **Clones the repository** (markdown files) - via Jenkins checkout
2. **Runs `process_docs.py`** - Chunks the markdown into semantic paragraphs
3. **Runs `create_embeddings.py`** - Calls Vertex AI Embeddings API to convert chunks into vectors (uses `um-vertex-ai-sa` service account via Workload Identity)
4. **Runs `load_chromadb.py`** - Connects directly to the ChromaDB service at `chromadb:8000` via HTTP (Jenkins runs in the same cluster, so no port-forwarding needed) and loads the embeddings

**Setup**: Copy `ingestion.Jenkinsfile` to your documentation repository and configure Jenkins to use it. The pipeline runs in Jenkins using the `python` labeled agent (runs in the same Kubernetes cluster, so it can directly access the `chromadb` service).

### 4. Create GAR Repository (One-Time Setup)

**Note**: Jenkins pipeline handles image builds automatically. You only need to create the repository once:

```bash
gcloud artifacts repositories create uplifted-mascot --repository-format=docker --location=us-east1 --project=teralivekubernetes
```

### 5. Deploy RAG Service

**The Jenkins pipeline handles building and pushing images automatically**. For manual deployment:

```bash
# Build and push (if not using Jenkins)
cat service-account-key.json | docker login -u _json_key --password-stdin https://us-east1-docker.pkg.dev
cd rag-service
docker build -t us-east1-docker.pkg.dev/teralivekubernetes/uplifted-mascot/um-rag-service:latest .
docker push us-east1-docker.pkg.dev/teralivekubernetes/uplifted-mascot/um-rag-service:latest

# Deploy
kubectl apply -f rag-service/k8s-deployment.yaml -n your-namespace
```

**Note**: The RAG service connects to ChromaDB via the `chromadb` service (ClusterIP). Make sure ChromaDB is deployed first (step 3).

**Important**: The RAG service needs to be updated to use `HttpClient` to connect to the ChromaDB service instead of `PersistentClient`. This is a code change in `rag_service.py` (see TODO in troubleshooting section).

### 6. Deploy Frontend

First, create a ConfigMap with your frontend files, or use a proper build process:

```bash
# Option 1: Create ConfigMap from files
kubectl create configmap um-frontend-config \
  --from-file=index.html=frontend/index.html \
  --from-file=widget.html=frontend/widget.html \
  -n your-namespace

# Option 2: Update the ConfigMap in frontend-deployment.yaml manually
```

Then deploy:
```bash
kubectl apply -f k8s/frontend-deployment.yaml -n your-namespace
```

### 7. Configure Ingress

Edit `k8s/ingress.yaml` and update:
- Hostname: `mascot.terasology.io` (or your desired subdomain)
- cert-manager issuer (if using TLS)

Deploy:
```bash
kubectl apply -f k8s/ingress.yaml -n your-namespace
```

### 8. Verify Deployment

```bash
# Check pods
kubectl get pods -n your-namespace

# Check services
kubectl get services -n your-namespace

# Check ingress
kubectl get ingress -n your-namespace

# View logs
kubectl logs -l app=um-rag-service -n your-namespace
```

## ChromaDB Data Loading

**ChromaDB data is populated automatically by a Jenkins ingestion pipeline** that runs on Git push to the knowledge base repository.

**Setup**: Copy `ingestion.Jenkinsfile` from this repository to your documentation repository. Configure Jenkins to:
1. Point to your documentation repository
2. Use `ingestion.Jenkinsfile` as the pipeline script
3. Trigger on git push (webhook or polling)

**The pipeline**:
1. Clones the repository (Jenkins checkout)
2. Runs `process_docs.py` - Chunks markdown files
3. Runs `create_embeddings.py` - Creates embeddings using Vertex AI (uses `um-vertex-ai-sa` via Workload Identity)
4. Runs `load_chromadb.py` - Connects directly to ChromaDB service at `chromadb:8000` via HTTP and loads embeddings

**No manual data loading needed** - everything is automated!

**Note**: The ingestion pipeline runs in Jenkins using the `python` labeled agent. Since Jenkins runs in the same Kubernetes cluster, the Python container can directly access the `chromadb` ClusterIP service without port-forwarding or kubectl.

## Troubleshooting

### RAG Service can't connect to ChromaDB

- Verify ChromaDB service is running: `kubectl get pods -l app=chromadb -n your-namespace`
- Check ChromaDB service exists: `kubectl get svc chromadb -n your-namespace`
- Verify RAG service is using `HttpClient` to connect to `chromadb:8000` (not `PersistentClient`)
- Check RAG service logs: `kubectl logs -l app=um-rag-service -n your-namespace`
- Check ChromaDB logs: `kubectl logs -l app=chromadb -n your-namespace`

### ChromaDB PVC Not Bound

**Check PVC status:**
```bash
kubectl get pvc chromadb-pvc -n your-namespace
```

**If STATUS is Pending:**
- Check storage class: `kubectl get storageclass`
- Verify cluster has available storage
- Check PVC events: `kubectl describe pvc chromadb-pvc -n your-namespace`

**Verify PVC is mounted in ChromaDB pod:**
```bash
kubectl describe pod -l app=chromadb -n your-namespace | grep -A 10 "Mounts:"
```

### GCP Authentication / Workload Identity

**Verify Workload Identity is enabled:**
```bash
gcloud container clusters describe ttf-cluster \
  --zone=us-east1-d \
  --project=teralivekubernetes \
  --format="value(workloadIdentityConfig.workloadPool)"

# Should show: teralivekubernetes.svc.id.goog
```

**Verify Kubernetes service account annotation:**
```bash
kubectl get serviceaccount um-vertex-ai-sa -n um -o yaml
# Should show annotation: iam.gke.io/gcp-service-account: um-vertex-ai-sa@teralivekubernetes.iam.gserviceaccount.com
```

**Verify Workload Identity binding:**
```bash
gcloud iam service-accounts get-iam-policy um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com  --project=teralivekubernetes

# Should show a binding with:
# members: serviceAccount:teralivekubernetes.svc.id.goog[your-namespace/um-vertex-ai-sa]
# role: roles/iam.workloadIdentityUser
```

**Verify roles:**
```bash
gcloud projects get-iam-policy teralivekubernetes --flatten="bindings[].members" --filter="bindings.members:serviceAccount:um-vertex-ai-gsa@teralivekubernetes.iam.gserviceaccount.com" --format="table(bindings.role)"

# Should show something like the following:
# ROLE
# roles/aiplatform.user
# roles/storage.objectViewer
```

**Test authentication from a pod:**
```bash
# Apply the test pod (runs sleep infinity to keep it alive)
kubectl apply -f k8s/test-vertex-pod.yaml

# Wait for it to be ready
kubectl wait --for=condition=Ready pod/test-vertex -n um --timeout=60s

# Get an interactive shell to explore
kubectl exec -it test-vertex -n um -- /bin/bash

# Run the following script inside the pod 
python -c '
import vertexai
from vertexai.generative_models import GenerativeModel
print("--- Starting Gemini Validation ---")
try:
    vertexai.init(project="teralivekubernetes", location="us-east1")
    print("Vertex AI initialized.")
    model = GenerativeModel("gemini-2.5-flash")
    print("Model loaded. Sending prompt...")
    response = model.generate_content("test")
    print("Response received!")
    print("\n\n✅ ✅ ✅ SUCCESS! ✅ ✅ ✅")
    print("This pod is correctly authenticated and has permission to use Gemini models.")
except Exception as e:
    print(f"\n\n❌ ❌ ❌ FAILED ❌ ❌ ❌")
    print(f"An error occurred: {e}")
'

# Clean up when done
kubectl delete pod test-vertex -n um
```

### Ingress not working

- Verify nginx ingress controller is running: `kubectl get pods -n ingress-nginx`
- Check ingress status: `kubectl describe ingress um-ingress -n your-namespace`
- Verify DNS points to your ingress IP: `kubectl get ingress um-ingress -n your-namespace`

### TLS Certificate Issues

- Check cert-manager: `kubectl get certificates -n your-namespace`
- Verify issuer: `kubectl get clusterissuer` or `kubectl get issuer -n your-namespace`

### Image Pull Errors

- Verify image exists in GAR:
  ```bash
  gcloud artifacts docker images list us-east1-docker.pkg.dev/teralivekubernetes/uplifted-mascot/um-rag-service
  ```
- Check GKE nodes have access to GAR (usually automatic with Workload Identity)
- Verify image pull secrets if using private registry

## Deployment Order

For a fresh deployment, follow this order:

1. **One-time setup**:
   - Create secrets (step 1)
   - Create GAR repository (step 4)

2. **Deploy infrastructure**:
   - ChromaDB (PVC, deployment, and service) (step 2)
   - Frontend ConfigMap (step 6)
   - Ingress (step 7)

3. **Deploy applications**:
   - RAG service (step 5) - connects to ChromaDB service
   - Frontend (step 6)

4. **Populate data**:
   - Run ingestion Jenkins job (automated on Git push)

**Note**: The Jenkins pipeline (see `JENKINS.md`) automates steps 2-3. You only need to do the one-time setup manually.

pipeline {
    agent {
        label 'python-ai'  // Python build agent (runs in same k8s cluster)
    }
    
    environment {
        GCP_PROJECT_ID = 'teralivekubernetes'  // Hardcoded GCP project
        GCP_REGION = 'us-east1'
        CHROMA_HOST = 'chromadb.um.svc.cluster.local'  // FQDN for cross-namespace access
        CHROMA_PORT = '8000'
        CHROMA_COLLECTION_NAME = 'uplifted_mascot'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Install Dependencies') {
            steps {
                container('builder') {
                    script {
                        // Install from requirements.txt (fast if already in base image)
                        // This ensures we have all dependencies even if base image is slightly out of date
                        sh '''
                            cd scripts
                            
                            # Install dependencies and capture output
                            pip install --no-cache-dir -r requirements.txt 2>&1 | tee /tmp/pip-install.log
                            
                            # Check if any packages were actually installed (not just "already satisfied")
                            echo "Checking for dependencies that weren't in base image..."
                            NEW_PACKAGES=$(grep -E "Successfully installed|Collecting|Installing" /tmp/pip-install.log | grep -v "already satisfied" | grep -v "Requirement already satisfied" | head -20 || true)
                            
                            if [ -n "$NEW_PACKAGES" ]; then
                                echo ""
                                echo "⚠️  WARNING: The following packages were installed during build (not in base image):"
                                echo "$NEW_PACKAGES" | sed 's/^/   /'
                                echo ""
                                echo "⚠️  Consider adding these to jenkins-python-ai-agent/requirements.txt and rebuilding the base image"
                                echo "⚠️  This will speed up future builds. See: jenkins-agent/Jenkinsfile"
                                echo ""
                            else
                                echo "✓ All dependencies were already in base image - installation was fast!"
                            fi
                        '''
                    }
                }
            }
        }
        
        stage('Process Documents') {
            steps {
                container('builder') {
                    script {
                        // Process all markdown files in the repository
                        // Assumes markdown files are in the repo root or subdirectories
                        sh '''
                            python scripts/process_docs.py . scripts/chunks.json
                        '''
                    }
                }
            }
        }
        
        stage('Create Embeddings') {
            steps {
                container('builder') {
                    script {
                        // Uses Workload Identity via um-vertex-ai-sa service account
                        // Service account must be configured on the Jenkins agent pod template
                        sh '''
                            python scripts/create_embeddings.py scripts/chunks.json scripts/embeddings-array.json
                        '''
                    }
                }
            }
        }
        
        stage('Load into ChromaDB') {
            steps {
                container('builder') {
                    script {
                        // Connect directly to ChromaDB service using FQDN (cross-namespace)
                        // Jenkins agent runs in 'jenkins' namespace, ChromaDB is in 'um' namespace
                        sh """
                            export CHROMA_HOST=${CHROMA_HOST}
                            export CHROMA_PORT=${CHROMA_PORT}
                            python scripts/load_chromadb.py scripts/embeddings-array.json ${CHROMA_COLLECTION_NAME} http://${CHROMA_HOST}:${CHROMA_PORT}
                        """
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo "Ingestion successful! Embeddings loaded into ChromaDB at ${CHROMA_HOST}:${CHROMA_PORT}"
        }
        failure {
            echo "Ingestion failed. Check logs above for details."
        }
    }
}


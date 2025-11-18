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


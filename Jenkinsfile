String deduceDockerTag() {
    String dockerTag = env.BRANCH_NAME
    if (dockerTag.equals("main") || dockerTag.equals("master")) {
        echo "Building the 'main' branch so we'll publish a Docker tag starting with 'latest'"
        dockerTag = "latest"
    } else {
        dockerTag += "-${env.BUILD_NUMBER}"
        echo "Building a branch other than 'main' so will publish a Docker tag starting with '$dockerTag', not 'latest'"
    }
    return dockerTag
}

pipeline {
    agent {
        label 'docker'  // Agent with Docker capability for build/push
    }
    
    environment {
        GCP_PROJECT_ID = credentials('gcp-project-id')
        GCP_REGION = 'us-east1'
        GAR_BASE_URL = "${GCP_REGION}-docker.pkg.dev"
        GAR_REPOSITORY = "uplifted-mascot"
        DOCKER_TAG = deduceDockerTag()
        FULL_IMAGE_NAME = "${GAR_BASE_URL}/${GCP_PROJECT_ID}/${GAR_REPOSITORY}/um-rag-service:${DOCKER_TAG}"
        K8S_NAMESPACE = 'um'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build Docker') {
            steps {
                dir('rag-service') {
                    sh "docker build -f Dockerfile -t ${FULL_IMAGE_NAME} ."
                }
            }
        }
        
        stage('Push Docker') {
            steps {
                script {
                    // Authenticate with GAR using the service account key then push
                    withCredentials([file(credentialsId: 'jenkins-gar-sa', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                        sh """
                            cat \${GOOGLE_APPLICATION_CREDENTIALS} | docker login -u _json_key --password-stdin https://${GAR_BASE_URL}
                            docker push ${FULL_IMAGE_NAME}
                        """
                    }
                }
            }
        }
        
        stage('k8s deploy') {
            agent {
                label 'kubectl'  // Switch to kubectl agent for deployment
            }
            steps {
                container('utility') {  // Utility container for kubectl
                    withKubeConfig(credentialsId: 'utility-admin-kubeconfig-sa-token') {
                        script {
                            // Ensure namespace exists
                            sh """
                                kubectl get ns ${K8S_NAMESPACE} || kubectl create ns ${K8S_NAMESPACE}
                            """
                            
                            // Update deployment YAML with actual image name
                            sh """
                                sed -i 's|us-east1-docker.pkg.dev/teralivekubernetes/uplifted-mascot/um-rag-service:latest|${FULL_IMAGE_NAME}|g' rag-service/k8s-deployment.yaml
                            """
                            
                            // Create/update frontend ConfigMap (idempotent via dry run trick - creates if missing, updates if exists)
                            sh """
                                kubectl create configmap um-frontend-html \
                                    --from-file=index.html=frontend/index.html \
                                    --from-file=widget.html=frontend/widget.html \
                                    -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                            """
                            
                            // Deploy ChromaDB (includes PVC, deployment, and service)
                            sh """
                                kubectl apply -f k8s/chromadb.yaml -n ${K8S_NAMESPACE}
                            """
                            
                            // Deploy RAG service
                            sh """
                                kubectl apply -f rag-service/k8s-deployment.yaml -n ${K8S_NAMESPACE}
                            """
                            
                            // Deploy frontend
                            sh """
                                kubectl apply -f k8s/frontend-deployment.yaml -n ${K8S_NAMESPACE}
                            """
                            
                            // Deploy ingress
                            sh """
                                kubectl apply -f k8s/ingress.yaml -n ${K8S_NAMESPACE}
                            """
                            /*
                            // Wait for rollouts
                            sh """
                                kubectl rollout status deployment/chromadb -n ${K8S_NAMESPACE} --timeout=2m || true
                                kubectl rollout status deployment/um-rag-service -n ${K8S_NAMESPACE} --timeout=5m
                                kubectl rollout status deployment/um-frontend -n ${K8S_NAMESPACE} --timeout=2m || true
                            """
                            
                            // Show deployment status
                            sh """
                                echo "=== Deployment Status ==="
                                kubectl get pods -n ${K8S_NAMESPACE}
                                kubectl get svc -n ${K8S_NAMESPACE}
                                kubectl get ingress -n ${K8S_NAMESPACE}
                            """
                            */
                        }
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo "Deployment successful! RAG service available at configured ingress URL"
        }
        failure {
            echo "Deployment failed. Check logs: kubectl logs -l app=um-rag-service -n ${K8S_NAMESPACE}"
        }
    }
}


// Quick test pipeline to validate Vertex AI authentication on a Python build agent
// See the k8s readme for steps needed to prepare the service account and GSA binding
pipeline {
    agent {
        label 'python'  // Uses the python build agent (builder container)
    }

    stages {
        stage('Check Python Environment') {
            steps {
                container('builder') {
                    sh '''
                        echo "Python version:"
                        python --version
                        echo ""

                        echo "Upgrading pip and installing baseline deps..."
                        python -m pip install --upgrade pip
                        pip install vertexai chromadb --quiet
                        echo "Dependencies installed successfully."
                    '''
                }
            }
        }

        stage('Validate Vertex AI Auth') {
            steps {
                container('builder') {
                    sh '''python - <<'PY'
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
    print("\\n\\n✅ ✅ ✅ SUCCESS! ✅ ✅ ✅")
    print("This agent is correctly authenticated and has permission to use Gemini models.")
except Exception as e:
    print("\\n\\n❌ ❌ ❌ FAILED ❌ ❌ ❌")
    print(f"An error occurred: {e}")
    raise
PY'''
                }
            }
        }
    }
}


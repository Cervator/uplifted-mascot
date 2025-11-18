# Use the shared Python AI base image with all dependencies pre-installed
FROM us-east1-docker.pkg.dev/teralivekubernetes/logistics/jenkins-python-ai-agent:latest

WORKDIR /app

# Dependencies are already installed in the base image, just copy application code
COPY rag_service.py .

# Expose port
EXPOSE 8000

# Run service with uvicorn (already installed in base image)
CMD ["uvicorn", "rag_service:app", "--host", "0.0.0.0", "--port", "8000"]


# Use the shared Python AI base image with all dependencies pre-installed
FROM us-east1-docker.pkg.dev/teralivekubernetes/logistics/jenkins-python-ai-agent:latest

WORKDIR /app

# Copy requirements and install (will be fast if already in base image)
# This ensures we have all dependencies even if base image is slightly out of date
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY rag_service.py .

# Expose port
EXPOSE 8000

# Run service with uvicorn (already installed in base image)
CMD ["uvicorn", "rag_service:app", "--host", "0.0.0.0", "--port", "8000"]


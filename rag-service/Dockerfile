FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY rag_service.py .

# Expose port
EXPOSE 8000

# Run service
CMD ["python", "rag_service.py"]


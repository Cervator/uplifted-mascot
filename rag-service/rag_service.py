#!/usr/bin/env python3
"""
RAG Service for Uplifted Mascot.
Provides API endpoint for querying the knowledge base.
"""

import os
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import aiplatform
from vertexai.preview import vector_search
from vertexai.language_models import TextEmbeddingModel, ChatModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Uplifted Mascot RAG Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration (set via environment variables)
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
REGION = os.getenv("GCP_REGION", "us-east1")
INDEX_ID = os.getenv("VECTOR_INDEX_ID")
ENDPOINT_ID = os.getenv("VECTOR_ENDPOINT_ID")
DEPLOYED_INDEX_ID = os.getenv("DEPLOYED_INDEX_ID", "um_deployed_index")

# Initialize Vertex AI
if PROJECT_ID:
    aiplatform.init(project=PROJECT_ID, location=REGION)

# Initialize models (lazy loading)
_embedding_model = None
_chat_model = None
_vector_index = None

def get_embedding_model():
    """Get or create embedding model."""
    global _embedding_model
    if _embedding_model is None:
        # Try text-embedding-004 first (available in us-east1), fall back to gecko models
        try:
            _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        except Exception:
            try:
                _embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
            except Exception:
                _embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
    return _embedding_model

def get_chat_model():
    """Get or create chat model."""
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatModel.from_pretrained("gemini-pro")
    return _chat_model

def get_vector_index():
    """Get or create vector index connection."""
    global _vector_index
    if _vector_index is None:
        endpoint = vector_search.get_index_endpoint(ENDPOINT_ID)
        _vector_index = endpoint
    return _vector_index

# Mascot personalities
MASCOT_PERSONALITIES = {
    "gooey": """You are Gooey, a friendly and helpful gelatinous cube mascot for Terasology. 
You're enthusiastic about helping players and modders. You speak in a slightly quirky, 
encouraging way. You love giving "cold hugs" (acidic embraces) to warm hearts. 
Keep responses concise, helpful, and friendly.""",
    
    "bill": """You are Bill, a pragmatic and governance-focused pig mascot for Demicracy. 
You're knowledgeable about community governance, decision-making processes, and platform 
democracy. You speak clearly and helpfully, focusing on practical solutions. 
Keep responses concise and actionable."""
}

# Request/Response models
class AskRequest(BaseModel):
    project: str
    mascot: str
    question: str
    context: Optional[str] = "web"
    top_k: Optional[int] = 5

class AskResponse(BaseModel):
    response: str
    sources: List[str]
    confidence: Optional[float] = None

def retrieve_context(query_text: str, top_k: int = 5) -> List[Dict]:
    """
    Retrieve relevant context from Vector Search.
    
    Args:
        query_text: User's question
        top_k: Number of results to retrieve
    
    Returns:
        List of relevant document chunks with metadata
    """
    try:
        # Create query embedding
        embedding_model = get_embedding_model()
        query_embedding = embedding_model.get_embeddings([query_text])[0]
        
        # Get vector index
        index_endpoint = get_vector_index()
        
        # Query the index
        # Note: This requires the index to be deployed
        results = index_endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[query_embedding.values],
            num_neighbors=top_k
        )
        
        # Format results
        context_chunks = []
        for result in results[0]:
            context_chunks.append({
                "text": result.metadata.get("text", ""),
                "file_path": result.metadata.get("file_path", ""),
                "filename": result.metadata.get("filename", ""),
                "distance": result.distance
            })
        
        return context_chunks
    
    except Exception as e:
        print(f"Error retrieving context: {e}")
        return []

def generate_response(question: str, context_chunks: List[Dict], mascot: str) -> str:
    """
    Generate response using Gemini with retrieved context.
    
    Args:
        question: User's question
        context_chunks: Retrieved context from vector search
        mascot: Mascot personality to use
    
    Returns:
        Generated response text
    """
    try:
        # Get personality prompt
        personality = MASCOT_PERSONALITIES.get(mascot, MASCOT_PERSONALITIES["gooey"])
        
        # Build context text
        context_text = "\n\n".join([
            f"From {chunk['filename']}:\n{chunk['text']}"
            for chunk in context_chunks
        ])
        
        # Build full prompt
        prompt = f"""{personality}

Use the following context from the project documentation to answer the user's question.
If the context doesn't contain enough information, say so honestly.

Context:
{context_text}

Question: {question}

Answer:"""
        
        # Generate response
        chat_model = get_chat_model()
        chat = chat_model.start_chat()
        response = chat.send_message(prompt)
        
        return response.text
    
    except Exception as e:
        print(f"Error generating response: {e}")
        return f"I apologize, but I encountered an error: {str(e)}"

@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "service": "Uplifted Mascot RAG Service",
        "status": "running",
        "project": PROJECT_ID
    }

@app.get("/health")
def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "vector_index_configured": INDEX_ID is not None,
        "endpoint_configured": ENDPOINT_ID is not None
    }

@app.post("/ask-mascot", response_model=AskResponse)
def ask_mascot(request: AskRequest):
    """
    Main endpoint for asking the mascot a question.
    
    Args:
        request: AskRequest with project, mascot, and question
    
    Returns:
        AskResponse with generated answer and sources
    """
    # Validate mascot
    if request.mascot not in MASCOT_PERSONALITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mascot: {request.mascot}. Available: {list(MASCOT_PERSONALITIES.keys())}"
        )
    
    # Retrieve relevant context
    context_chunks = retrieve_context(request.question, request.top_k)
    
    if not context_chunks:
        return AskResponse(
            response="I couldn't find relevant information in the knowledge base. Please try rephrasing your question.",
            sources=[],
            confidence=0.0
        )
    
    # Generate response
    response_text = generate_response(
        request.question,
        context_chunks,
        request.mascot
    )
    
    # Extract sources
    sources = [
        chunk["file_path"] for chunk in context_chunks
    ]
    
    # Calculate confidence (simple: based on average distance)
    avg_distance = sum(chunk["distance"] for chunk in context_chunks) / len(context_chunks)
    confidence = max(0.0, min(1.0, 1.0 - avg_distance))  # Convert distance to confidence
    
    return AskResponse(
        response=response_text,
        sources=sources,
        confidence=confidence
    )

if __name__ == "__main__":
    import uvicorn
    
    # Validate configuration
    if not PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID environment variable not set")
    if not INDEX_ID:
        raise ValueError("VECTOR_INDEX_ID environment variable not set")
    if not ENDPOINT_ID:
        raise ValueError("VECTOR_ENDPOINT_ID environment variable not set")
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)


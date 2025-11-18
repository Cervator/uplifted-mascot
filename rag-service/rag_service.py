#!/usr/bin/env python3
"""
RAG Service for Uplifted Mascot.
Provides API endpoint for querying the knowledge base.
"""

import logging
import os
import time
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv
import chromadb
from pathlib import Path
from chromadb.config import Settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Uplifted Mascot RAG Service")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag_service")

# Rate limiting configuration (requests per minute per IP)
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

# Token limits for Vertex AI (cost control)
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))  # Max tokens in response
MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "4096"))    # Max tokens in prompt (Gemini default is higher, but we cap it for cost control)

# Initialize rate limiter (in-memory, per IP)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

# ChromaDB configuration
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "uplifted_mascot")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_HOST = os.getenv("CHROMA_HOST")  # If set, use HTTP client to connect to ChromaDB service
CHROMA_PORT = os.getenv("CHROMA_PORT", "8000")

# Legacy Vertex AI Vector Search (optional, for scaling)
INDEX_ID = os.getenv("VECTOR_INDEX_ID")  # Optional - only if using Vertex AI Vector Search
ENDPOINT_ID = os.getenv("VECTOR_ENDPOINT_ID")  # Optional
DEPLOYED_INDEX_ID = os.getenv("DEPLOYED_INDEX_ID", "um_deployed_index")  # Optional

# Initialize Vertex AI
if PROJECT_ID:
    aiplatform.init(project=PROJECT_ID, location=REGION)

# Initialize models (lazy loading)
_embedding_model = None
_chat_model = None
_chroma_collection = None  # ChromaDB collection
_vector_index = None  # Legacy Vertex AI Vector Search (optional)

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
    """Get or create chat model using modern GenerativeModel API."""
    global _chat_model
    if _chat_model is None:
        # Try Model Garden model names (simple names, no "google/" prefix needed)
        # Using the modern GenerativeModel API
        # Prioritize Flash models - faster, cheaper, perfect for RAG/document Q&A
        model_names = [
            "gemini-2.5-flash",          # Latest Flash - balance speed/quality for RAG  <-- top entry gets used
            "gemini-2.5-flash-lite",     # Fastest model - great for simple Q&A (may be more concise?)
            "gemini-2.0-flash-001",      # Stable Flash - reliable fallback
            "gemini-2.0-flash-lite-001", # Stable Flash-Lite - fastest fallback
            "gemini-2.5-pro",            # Pro model - only if Flash models don't work
        ]
        
        last_error = None
        for model_name in model_names:
            try:
                print(f"Trying to load model: {model_name}")
                _chat_model = GenerativeModel(model_name)
                print(f"✓ Successfully loaded model: {model_name}")
                break
            except Exception as e:
                last_error = e
                error_msg = str(e)
                if "404" in error_msg or "not found" in error_msg.lower():
                    print(f"  ✗ Not found")
                else:
                    print(f"  ✗ Error: {error_msg[:80]}")
                continue
        
        if _chat_model is None:
            raise Exception(
                f"Could not load any Gemini model. Last error: {last_error}\n\n"
                "Run this to check available models:\n"
                "  python scripts/check_gemini_models.py\n\n"
                "Or check Model Garden in GCP Console for available model shortnames."
            )
    
    return _chat_model

def get_chroma_collection():
    """Get or create ChromaDB collection."""
    global _chroma_collection
    if _chroma_collection is None:
        # Check if we should use HTTP client (Kubernetes service) or persistent client (local dev)
        if CHROMA_HOST:
            # Use HTTP client to connect to ChromaDB service (Kubernetes deployment)
            try:
                client = chromadb.HttpClient(
                    host=CHROMA_HOST,
                    port=int(CHROMA_PORT),
                    settings=Settings(anonymized_telemetry=False)
                )
                print(f"✓ Connecting to ChromaDB service at {CHROMA_HOST}:{CHROMA_PORT}")
            except Exception as e:
                raise Exception(
                    f"Failed to connect to ChromaDB service at {CHROMA_HOST}:{CHROMA_PORT}. "
                    f"Make sure the ChromaDB service is running and accessible.\n"
                    f"Error: {e}"
                )
        else:
            # Use persistent client for local development
            # Try multiple paths for the database - prioritize workspace root
            # Path(__file__) is rag-service/rag_service.py, so parent.parent is workspace root
            workspace_root = Path(__file__).parent.parent
            
            persist_paths = [
                workspace_root / "chroma_db",  # Workspace root (most likely location)
                workspace_root / CHROMA_PERSIST_DIR.lstrip("./"),  # If CHROMA_PERSIST_DIR is relative
                Path(CHROMA_PERSIST_DIR).resolve(),  # Absolute or resolved path from env
                Path("chroma_db").resolve(),  # Current directory
                Path("../chroma_db").resolve(),  # Parent directory
            ]
            
            client = None
            found_path = None
            
            # Try each path - check if it exists AND has the collection
            for persist_path in persist_paths:
                # Only try paths that actually exist
                if persist_path.exists() and persist_path.is_dir():
                    try:
                        test_client = chromadb.PersistentClient(
                            path=str(persist_path),
                            settings=Settings(anonymized_telemetry=False)
                        )
                        # Check if collection exists in this database
                        try:
                            test_collection = test_client.get_collection(name=CHROMA_COLLECTION_NAME)
                            # Collection exists! Use this client
                            client = test_client
                            found_path = persist_path
                            print(f"✓ Found ChromaDB at: {persist_path.absolute()}")
                            break
                        except Exception:
                            # Collection doesn't exist in this database, try next path
                            continue
                    except Exception as e:
                        # Could not connect to this path, try next
                        continue
            
            if client is None:
                # No existing database found, create in workspace root
                default_path = workspace_root / "chroma_db"
                default_path.mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(
                    path=str(default_path),
                    settings=Settings(anonymized_telemetry=False)
                )
                found_path = default_path
                print(f"Created new ChromaDB at: {default_path.absolute()}")
            else:
                print(f"Using ChromaDB at: {found_path.absolute()}")
        
        # Get collection
        try:
            _chroma_collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
            print(f"✓ Loaded ChromaDB collection: {CHROMA_COLLECTION_NAME} ({_chroma_collection.count()} documents)")
        except Exception as e:
            if CHROMA_HOST:
                raise Exception(
                    f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' not found in service at {CHROMA_HOST}:{CHROMA_PORT}. "
                    f"Make sure the ingestion job has loaded the embeddings.\n"
                    f"Error: {e}"
                )
            else:
                raise Exception(
                    f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' not found in {found_path.absolute()}. "
                    f"Please run: python scripts/load_chromadb.py scripts/embeddings-array.json\n"
                    f"Error: {e}"
                )
    
    return _chroma_collection

def get_vector_index():
    """Get or create Vertex AI Vector Search index connection (legacy, optional)."""
    global _vector_index
    if _vector_index is None and ENDPOINT_ID:
        # Use MatchingEngineIndexEndpoint from aiplatform
        # Format: projects/{project}/locations/{location}/indexEndpoints/{endpoint_id}
        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{REGION}/indexEndpoints/{ENDPOINT_ID}"
        endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_resource_name
        )
        _vector_index = endpoint
    return _vector_index

# Mascot personalities
MASCOT_PERSONALITIES = {
    "gooey": """You are Gooey, a friendly and helpful gelatinous cube mascot for Terasology. 
You're enthusiastic about helping players and modders. You speak in a slightly quirky, 
encouraging way. Keep responses concise, helpful, and friendly.""",
    
    "bill": """You are Bill, a pragmatic and governance-focused pig mascot for Demicracy. 
You're knowledgeable about community governance, decision-making processes, and platform 
democracy. You speak clearly and helpfully, focusing on practical solutions. 
Keep responses concise and actionable."""
}

# Request/Response models
class AskRequest(BaseModel):
    project: str
    mascot: str
    question: str = Field(..., min_length=1, max_length=1000, description="Question to ask (max 1000 characters)")
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve (1-20)")
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate question is not empty and not too long."""
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) > 1000:
            raise ValueError("Question cannot exceed 1000 characters")
        return v

class AskResponse(BaseModel):
    response: str
    sources: List[str]
    confidence: Optional[float] = None

def retrieve_context(query_text: str, top_k: int = 5) -> List[Dict]:
    """
    Retrieve relevant context from ChromaDB (or Vertex AI Vector Search if configured).
    
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
        
        # Use ChromaDB (primary approach)
        collection = get_chroma_collection()
        
        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding.values],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        context_chunks = []
        if results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                text = results["documents"][0][i] if results["documents"] else ""
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0
                
                file_path = metadata.get("file_path", "")
                filename = metadata.get("filename", file_path.replace("\\", "/").split("/")[-1])
                chunk_index = metadata.get("chunk_index", "")
                
                context_chunks.append({
                    "text": text,
                    "file_path": file_path,
                    "filename": filename,
                    "distance": distance,
                    "id": doc_id,
                    "chunk_index": chunk_index
                })
        
        return context_chunks
    
    except Exception as e:
        print(f"Error retrieving context: {e}")
        import traceback
        traceback.print_exc()
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
        
        # Truncate prompt if it exceeds MAX_INPUT_TOKENS (rough estimate: 1 token ≈ 4 characters)
        # This is a conservative estimate to stay under token limits
        max_input_chars = MAX_INPUT_TOKENS * 4
        if len(prompt) > max_input_chars:
            print(f"Warning: Prompt length ({len(prompt)} chars) exceeds estimated token limit. Truncating...")
            # Keep the personality and question, truncate context
            personality_and_question = f"""{personality}

Use the following context from the project documentation to answer the user's question.
If the context doesn't contain enough information, say so honestly.

Context:
"""
            question_part = f"\n\nQuestion: {question}\n\nAnswer:"
            available_chars = max_input_chars - len(personality_and_question) - len(question_part)
            # Truncate context text to fit
            if len(context_text) > available_chars:
                context_text = context_text[:available_chars] + "\n\n[Context truncated due to length limits]"
            prompt = personality_and_question + context_text + question_part
        
        # Generate response
        chat_model = get_chat_model()
        
        # Configure generation parameters (token limits, temperature, etc.)
        generation_config = GenerationConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.7,  # Balanced creativity/consistency for Q&A
            top_p=0.95,       # Nucleus sampling
            top_k=40          # Top-K sampling
        )
        
        # Use generate_content for single-turn (simpler, may avoid deprecation warnings)
        # Or start_chat for multi-turn conversations
        try:
            # Try direct generate_content first (simpler API) with generation config
            response = chat_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            return response.text
        except AttributeError:
            # Fallback to chat API if generate_content doesn't work
            chat = chat_model.start_chat()
            response = chat.send_message(prompt, generation_config=generation_config)
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
    try:
        collection = get_chroma_collection()
        chroma_status = {
            "configured": True,
            "collection": CHROMA_COLLECTION_NAME,
            "document_count": collection.count()
        }
    except Exception as e:
        chroma_status = {
            "configured": False,
            "error": str(e)
        }
    
    return {
        "status": "healthy",
        "chromadb": chroma_status,
        "vertex_ai_vector_search": {
            "configured": INDEX_ID is not None and ENDPOINT_ID is not None,
            "index_id": INDEX_ID,
            "endpoint_id": ENDPOINT_ID
        }
    }

@app.post("/ask-mascot", response_model=AskResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")  # Rate limit: configurable requests per minute per IP
def ask_mascot(request: Request, request_body: AskRequest):
    """
    Main endpoint for asking the mascot a question.
    
    Rate limited to 10 requests per minute per IP address to prevent abuse.
    
    Args:
        request: FastAPI Request object (for rate limiting)
        request_body: AskRequest with project, mascot, and question
    
    Returns:
        AskResponse with generated answer and sources
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "ask-mascot request ip=%s mascot=%s top_k=%s question=\"%s\"",
        client_ip,
        request_body.mascot,
        request_body.top_k,
        request_body.question.strip(),
    )
    
    # Validate mascot
    if request_body.mascot not in MASCOT_PERSONALITIES:
        logger.warning("ask-mascot invalid mascot ip=%s mascot=%s", client_ip, request_body.mascot)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mascot: {request_body.mascot}. Available: {list(MASCOT_PERSONALITIES.keys())}"
        )
    
    # Retrieve relevant context
    context_chunks = retrieve_context(request_body.question, request_body.top_k)
    logger.info(
        "ask-mascot context ip=%s chunks=%d",
        client_ip,
        len(context_chunks),
    )
    
    if not context_chunks:
        logger.info("ask-mascot no-context ip=%s question=\"%s\"", client_ip, request_body.question.strip())
        return AskResponse(
            response="I couldn't find relevant information in the knowledge base. Please try rephrasing your question.",
            sources=[],
            confidence=0.0
        )
    
    # Generate response
    response_text = generate_response(
        request_body.question,
        context_chunks,
        request_body.mascot
    )
    
    # Extract sources
    sources = [
        chunk["file_path"] for chunk in context_chunks
    ]
    
    # Calculate confidence (simple: based on average distance)
    avg_distance = sum(chunk["distance"] for chunk in context_chunks) / len(context_chunks)
    confidence = max(0.0, min(1.0, 1.0 - avg_distance))  # Convert distance to confidence
    
    preview = response_text.replace("\n", " ")[:200]
    logger.info(
        "ask-mascot response ip=%s mascot=%s top_k=%s chunks=%d confidence=%.2f preview=\"%s%s\"",
        client_ip,
        request_body.mascot,
        request_body.top_k,
        len(context_chunks),
        confidence,
        preview,
        "..." if len(response_text) > 200 else "",
    )
    
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
    
    # Validate ChromaDB is available
    try:
        get_chroma_collection()
    except Exception as e:
        print(f"\n⚠️  Warning: ChromaDB not configured: {e}")
        print("\nTo set up ChromaDB:")
        print("  1. Run: python scripts/create_embeddings.py scripts/chunks.json scripts/embeddings-array.json")
        print("  2. Run: python scripts/load_chromadb.py scripts/embeddings-array.json")
        print("\nOr set up Vertex AI Vector Search (see 03-vector-storage.md for scaling)")
        raise
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)


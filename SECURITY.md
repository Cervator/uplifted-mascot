# Security & Rate Limiting

The Uplifted Mascot RAG service is publicly accessible and includes several guardrails to prevent abuse.

## Rate Limiting

**Default**: 10 requests per minute per IP address

The service uses [slowapi](https://github.com/laurents/sizeof) for rate limiting, which tracks requests per IP address in-memory. This prevents:

- **Cost abuse**: Excessive API calls to Vertex AI (Gemini) and Embeddings API
- **Resource exhaustion**: Overloading the ChromaDB service or RAG service
- **DDoS attacks**: Basic protection against request flooding

### Configuration

Rate limits can be configured via the `RATE_LIMIT_PER_MINUTE` environment variable:

```yaml
# In k8s-deployment.yaml
env:
  - name: RATE_LIMIT_PER_MINUTE
    value: "20"  # 20 requests per minute instead
```

### Rate Limit Response

When a user exceeds the rate limit, they receive a `429 Too Many Requests` response:

```json
{
  "detail": "Rate limit exceeded: 10 per 1 minute"
}
```

The response includes standard rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `Retry-After`: Seconds until the rate limit resets

## Input Validation

### Question Length

- **Minimum**: 1 character (after trimming whitespace)
- **Maximum**: 1000 characters
- **Validation**: Automatic via Pydantic model validation

### Top-K Parameter

- **Minimum**: 1
- **Maximum**: 20
- **Default**: 5
- **Purpose**: Limits the number of context chunks retrieved, preventing excessive ChromaDB queries

### Mascot Validation

Only known mascot personalities are accepted. Unknown mascots return a `400 Bad Request` error.

## Additional Protections

### Request Timeouts

FastAPI/Uvicorn has default request timeouts. For long-running requests, consider:

1. **Uvicorn timeout**: Configure in deployment
2. **Vertex AI timeout**: Handled by the SDK (default: 60 seconds)
3. **ChromaDB timeout**: Handled by the client library

### CORS Configuration

Currently, CORS allows all origins (`allow_origins=["*"]`). For production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mascot.terasology.io", "https://terasology.org"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Monitoring

Monitor the following metrics:

1. **Rate limit hits**: Check logs for `429` responses
2. **Request volume**: Monitor total requests per hour/day
3. **Error rates**: Track `400`, `429`, `500` responses
4. **Response times**: Monitor Vertex AI and ChromaDB latency

## Future Enhancements

Consider adding:

1. **Redis-based rate limiting**: For distributed rate limiting across multiple pods
2. **API keys**: For authenticated users with higher limits
3. **IP whitelisting**: For trusted sources
4. **Request size limits**: Additional protection against large payloads
5. **WAF integration**: Cloud Armor or similar for advanced DDoS protection

## Token Limits

**Understanding the Different Limits:**

The system has three separate limits that work together:

1. **User Question Limit**: 1000 characters (enforced in API)
   - This is just the user's question text
   - Prevents extremely long questions that would be hard to process

2. **Total Input Token Limit**: 4096 tokens (~16,000 characters)
   - This applies to the **entire prompt** sent to Gemini, which includes:
     - **Personality prompt**: ~500-1000 characters (fixed)
     - **Context chunks**: Variable size, up to `top_k` chunks (default: 5)
       - Each chunk is up to **1000 characters** (from `process_docs.py` chunking)
       - With 5 chunks (default): ~2000-5000 characters
       - With 20 chunks (max): ~8000-20,000 characters
     - **User question**: Up to 1000 characters
     - **Prompt template**: ~200 characters (instructions, formatting)

3. **Output Token Limit**: 1024 tokens (~4000 characters)
   - Maximum tokens in the AI's response
   - Prevents excessively long responses

**Why the Question Limit is Lower:**

The 1000-character question limit is separate from the 4096-token input limit because:
- The question is just **one component** of the total prompt
- Most of the input tokens come from **context chunks** retrieved from ChromaDB
- Each context chunk can be up to 1000 characters (same as question limit)
- With `top_k=5` (default), you might have ~2000-5000 characters of context
- With `top_k=20` (max), you could have ~8000-20,000 characters of context
- The 4096-token limit protects against expensive API calls when many/large context chunks are retrieved

**Example Breakdown** (typical request with `top_k=5`):
- Personality: ~800 chars (~200 tokens)
- Context (5 chunks, ~400 chars each): ~2000 chars (~500 tokens)
- Question: ~200 chars (~50 tokens)
- Template: ~200 chars (~50 tokens)
- **Total**: ~3200 chars (~800 tokens) - well under 4096 limit

**Example Breakdown** (worst case with `top_k=20`):
- Personality: ~800 chars (~200 tokens)
- Context (20 chunks, ~1000 chars each): ~20,000 chars (~5000 tokens)
- Question: ~1000 chars (~250 tokens)
- Template: ~200 chars (~50 tokens)
- **Total**: ~22,000 chars (~5500 tokens) - **exceeds 4096 limit, so context gets truncated**

**Token Estimation**: Roughly 1 token ≈ 4 characters (conservative estimate)

**Example Costs** (Gemini 2.5 Flash pricing, approximate):
- Input: ~$0.075 per 1M tokens
- Output: ~$0.30 per 1M tokens
- With defaults (1024 output tokens): ~$0.0003 per response
- With rate limit (10/min): Max ~$0.003/min per IP = ~$4.32/day per IP

## Cost Protection

Rate limiting and token limits work together to protect against:

- **Vertex AI costs**: Each request uses Gemini API (charged per token)
  - Input tokens: Personality prompt + context chunks + question
  - Output tokens: Generated response
- **Embeddings API costs**: Each question creates an embedding vector (~$0.0001 per request)
- **Compute costs**: ChromaDB queries and response generation

**With default limits**:
- **Rate limit**: 10 requests/minute per IP
- **Output tokens**: 1024 max per response
- **Input tokens**: 4096 max per request (context truncated if needed)

**Maximum cost per IP**:
- **Per minute**: 10 requests × $0.0003 = $0.003/min
- **Per hour**: 600 requests × $0.0003 = $0.18/hour
- **Per day**: 14,400 requests × $0.0003 = $4.32/day

**Adjust limits** based on your budget:
- `RATE_LIMIT_PER_MINUTE`: Lower = less cost, higher = more user-friendly
- `MAX_OUTPUT_TOKENS`: Lower = shorter responses, higher = more detailed (but expensive)
- `MAX_INPUT_TOKENS`: Lower = less context, higher = more context (but expensive)


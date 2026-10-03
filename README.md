# PactMind AI Engine 🤖

FastAPI-based AI engine for contract analysis, powered by Groq LLMs and Pinecone vector search.

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys

# Run server
uvicorn main:app --reload --port 8000
```

Access API docs at: http://localhost:8000/docs

---

## 📦 Tech Stack

- **FastAPI**: High-performance Python API framework
- **Groq**: LLM inference (LLaMA 3.1)
- **Voyage AI**: Lightweight embedding API (replaces sentence-transformers)
- **Pinecone**: Vector database for semantic search
- **PostgreSQL**: Document metadata storage (Neon)
- **Supabase**: Document file storage

---

## 🔑 Required API Keys

| Service | Purpose | Free Tier | Get Key |
|---------|---------|-----------|---------|
| **Groq** | LLM inference | Yes | https://console.groq.com/ |
| **Voyage AI** | Embeddings | 100M tokens/mo | https://www.voyageai.com/ |
| **Pinecone** | Vector search | Yes | https://www.pinecone.io/ |
| **Neon** | PostgreSQL | Yes | https://neon.tech/ |
| **Supabase** | File storage | Yes | https://supabase.com/ |

---

## 🌍 Environment Variables

See `.env.example` for full configuration. Key variables:

```bash
# Database
DATABASE_URL=postgresql://...

# Auth (shared with Next.js app)
ENGINE_API_SECRET=your-secret-here

# Supabase
SUPABASE_URL=https://your-project.supabase.co

# LLM (Groq)
GROQ_API_KEY=gsk_...

# Embeddings (Voyage AI)
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=voyage-3-lite

# Vector DB (Pinecone)
PINECONE_API_KEY=pcsk_...
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=pactmind

# Rate Limiting
ENGINE_RATE_LIMIT_MAX=120
ENGINE_RATE_LIMIT_WINDOW_SEC=60

# CORS (leave empty in production)
ENGINE_CORS_ORIGINS=http://localhost:3000
```

---

## 🔌 API Endpoints

### Health Check
```bash
GET /health
```

### Process Document
```bash
POST /process
Authorization: Bearer {ENGINE_API_SECRET}

{
  "user_id": "uuid",
  "document_id": "uuid",
  "text": "contract text...",
  "file_url": "https://..."
}
```

### Query (RAG Chat)
```bash
POST /query
Authorization: Bearer {ENGINE_API_SECRET}

{
  "user_id": "uuid",
  "document_id": "uuid",
  "question": "What is the liability cap?"
}
```

### Analyze Contract
```bash
POST /analyze
Authorization: Bearer {ENGINE_API_SECRET}

{
  "text": "contract text..."
}
```

### Run Agent Team
```bash
POST /agents
Authorization: Bearer {ENGINE_API_SECRET}

{
  "text": "contract text..."
}
```

### Portfolio Search
```bash
POST /portfolio
Authorization: Bearer {ENGINE_API_SECRET}

{
  "user_id": "uuid",
  "question": "Which contracts expire in 60 days?"
}
```

Full API documentation: http://localhost:8000/docs

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   Next.js App       │
│   (pactmind)        │
└──────────┬──────────┘
           │
           │ HTTP + Bearer Auth
           ▼
┌─────────────────────┐
│   FastAPI Engine    │
│   (pactmind-engine) │
├─────────────────────┤
│ • Document parsing  │
│ • Text chunking     │
│ • Embeddings        │
│ • Vector storage    │
│ • LLM analysis      │
│ • Agent team        │
│ • RAG retrieval     │
└──────────┬──────────┘
           │
           ├─────► Groq (LLM)
           ├─────► Voyage AI (Embeddings)
           ├─────► Pinecone (Vectors)
           ├─────► PostgreSQL (Metadata)
           └─────► Supabase (Files)
```

---

## 📁 Project Structure

```
pactmind-engine/
├── main.py              # FastAPI app + middleware
├── auth.py              # Bearer token authentication
├── rate_limit.py        # Request rate limiting
├── job_limits.py        # Concurrent job limiting
├── requirements.txt     # Python dependencies
├── vercel.json          # Vercel deployment config
├── .vercelignore        # Exclude files from deployment
├── routers/             # API endpoints
│   ├── process.py       # Document processing
│   ├── query.py         # RAG chat
│   ├── analyze.py       # Contract analysis
│   ├── agents.py        # Agent team
│   ├── portfolio.py     # Cross-document search
│   ├── compare.py       # Document comparison
│   └── validate.py      # Content validation
├── services/            # Business logic
│   ├── parser.py        # PDF/DOCX parsing
│   ├── chunker.py       # Text splitting
│   ├── embedder.py      # Voyage AI embeddings
│   ├── pinecone_service.py  # Vector operations
│   ├── groq_service.py  # LLM calls
│   ├── analyzer.py      # Contract analysis
│   ├── agents.py        # Specialist agents
│   ├── retrieval.py     # RAG retrieval
│   ├── comparer.py      # Document comparison
│   └── content_guard.py # Security validation
├── db/                  # Database
│   ├── neon.py          # PostgreSQL queries
│   ├── ownership.py     # Document ownership
│   └── billing.py       # Usage tracking
└── models/              # Data models
    └── schemas.py       # Pydantic schemas
```

---

## 🚀 Deployment

### Vercel (Recommended for Serverless)

**Important**: We use **Voyage AI** instead of `sentence-transformers` to keep bundle size under 500MB.

See [VERCEL_DEPLOY.md](./VERCEL_DEPLOY.md) for detailed instructions.

**Quick Deploy:**
```bash
# 1. Get Voyage AI API key: https://www.voyageai.com/
# 2. Set environment variables in Vercel dashboard
# 3. Push to GitHub
git push origin main
```

Bundle size: **~50MB** ✅ (down from 5.7GB)

### Railway (Alternative - No Size Limits)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Deploy
railway up
```

Railway allows larger dependencies (can use sentence-transformers if preferred).

### Docker

```bash
docker build -t pactmind-engine .
docker run -p 8000:8000 --env-file .env pactmind-engine
```

---

## 🔧 Development

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
pytest
```

### Format Code
```bash
black .
ruff check .
```

### Type Checking
```bash
mypy .
```

---

## 📊 Performance

### Embedding Options

| Method | Bundle Size | Speed | Quality | Cost |
|--------|-------------|-------|---------|------|
| **Voyage AI** | 50MB | Fast | High | Free* |
| OpenAI | 50MB | Fast | High | $0.02/1M |
| sentence-transformers | 5.7GB | Medium | High | Free |
| Hash fallback | 50MB | Very fast | Low | Free |

*Free tier: 100M tokens/month

### Typical Processing Times
- **Document upload**: 5-10s (1000 chunks)
- **Contract analysis**: 2-3s
- **Agent team**: 3-5s (4 agents in parallel)
- **RAG query**: 1-2s
- **Portfolio search**: 2-4s

---

## 🔐 Security

### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer {ENGINE_API_SECRET}
```

### Rate Limiting
- 120 requests per 60 seconds per IP
- Configurable via `ENGINE_RATE_LIMIT_MAX`

### Content Validation
- URL validation to prevent SSRF
- Supabase host allowlist
- Text content scanning

### CORS
- Disabled in production (server-to-server only)
- Enable for local browser testing only

---

## 🐛 Troubleshooting

### "Voyage API error"
**Cause**: Missing or invalid `VOYAGE_API_KEY`  
**Fix**: Get free key from https://www.voyageai.com/  
**Fallback**: Hash-based embeddings used automatically

### "Database connection error"
**Cause**: Invalid `DATABASE_URL`  
**Fix**: Check Neon PostgreSQL connection string

### "Pinecone index not found"
**Cause**: Index doesn't exist  
**Fix**: Create index in Pinecone dashboard (dimension: 384 for Voyage, 384 for all-MiniLM)

### "Bundle too large on Vercel"
**Cause**: Added heavy dependencies  
**Fix**: Keep `sentence-transformers` removed, use API-based embeddings

---

## 📚 Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Groq API**: https://console.groq.com/docs
- **Voyage AI**: https://docs.voyageai.com/
- **Pinecone**: https://docs.pinecone.io/
- **Vercel Python**: https://vercel.com/docs/functions/runtimes/python

---

## 🤝 Integration with Next.js App

The engine is called by the Next.js app (`pactmind/`) via server-side API routes:

```typescript
// Example: Call engine from Next.js
const response = await fetch(`${AI_ENGINE_URL}/query`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${ENGINE_API_SECRET}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: userId,
    document_id: docId,
    question: userQuestion
  })
})
```

---

## 📄 License

Private project - All rights reserved

---

## 👨‍💻 Author

Built for PactMind contract intelligence platform

---

**Ready to deploy!** See [VERCEL_DEPLOY.md](./VERCEL_DEPLOY.md) for step-by-step instructions. 🚀

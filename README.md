# AI Resume & Portfolio Builder

Production-ready AI-powered resume builder using OpenRouter's Llama 3.3-70B, FastAPI, React, and MongoDB Atlas.

## Architecture

- **Frontend**: React + TypeScript + Vite + Tailwind CSS (deployed on Vercel)
- **Backend**: FastAPI + Python 3.11 (deployed on Render)
- **Database**: MongoDB Atlas with Vector Search
- **LLM**: Llama 3.3-70B via OpenRouter API
- **Storage**: S3-compatible storage for files
- **Auth**: JWT with RS256, refresh token rotation, HTTP-only cookies

## Features

- Secure authentication with JWT access/refresh tokens
- AI-powered resume generation tailored to job descriptions
- OCR for uploaded resume images/PDFs
- RAG-based recommendations using vector search
- PDF export functionality
- Rate limiting and security headers
- Observability with Sentry and structured logging

## Implementation Status

### ✅ Fully Implemented Features

| Feature | Implementation | Location |
|---------|---------------|----------|
| **S3 Storage** | Complete with upload/download/delete/presigned URLs | `backend/app/services/storage.py` |
| **Embeddings** | OpenAI, Cohere, and local sentence-transformers support | `backend/app/services/embeddings.py` |
| **Vector Stores** | MongoDB Atlas, Pinecone, and Qdrant adapters with upsert/query/delete | `backend/app/services/vector_store/` |
| **OCR Service** | Tesseract, Google Vision, AWS Textract, Azure Vision with graceful fallback | `backend/app/services/ocr.py` |
| **Authentication** | RS256 JWT, refresh token rotation, HTTP-only cookies | `backend/app/core/security.py` |
| **PDF Generation** | Playwright-based PDF export (cross-platform) | `backend/app/services/pdf_generator.py` |

### 🚧 Partially Implemented / Enhancement Opportunities

| Feature | Status | Notes |
|---------|--------|-------|
| **OCR Image Preprocessing** | Basic OCR only | No advanced preprocessing (contrast, deskew, noise reduction) |
| **PDF Page-Specific Extraction** | All pages only | Cannot extract specific page ranges |
| **Archive Extraction** | Not implemented | ZIP/TAR.GZ extraction for bulk document ingestion |

### 📝 Documentation Notes

- **response.md** contains historical TODO comments that reference placeholder implementations
- These TODOs are now **outdated** - the actual implementations exist in the codebase
- Refer to the source code files listed above for current implementations
- If you see `raise NotImplementedError()` in documentation, check the actual service files first
- **📖 See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for detailed status of all features**

## Security

- TLS-only communication
- HTTP-only, Secure, SameSite=strict cookies for refresh tokens
- Short-lived access tokens (5 minutes)
- Server-side HTML sanitization with bleach
- NoSQL injection prevention
- Content Security Policy headers
- Rate limiting on sensitive endpoints

## Quick Start

### Backend

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright for PDF generation (recommended)
pip install playwright
playwright install chromium

# Start the application
uvicorn app.main:app --reload
```

**Note:** For automated Playwright installation, run:
- Linux/Mac: `bash INSTALL_PLAYWRIGHT.sh`
- Windows: `.\INSTALL_PLAYWRIGHT.ps1`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend
- `OPENROUTER_API_KEY`: OpenRouter API key
- `MONGO_URI`: MongoDB Atlas connection string (required)
- `RS_PRIVATE_KEY`: RS256 private key for JWT signing
- `RS_PUBLIC_KEY`: RS256 public key for JWT verification
- `JWT_SECRET`: Fallback secret for HS256
- `S3_*`: S3-compatible storage credentials (or `USE_LOCAL_STORAGE=true` for dev)
- `PDF_ENGINE`: PDF generation engine (default: `playwright`)
- `PDF_UPLOAD_TO_S3`: Upload PDFs to S3 (default: `true`)
- `CELERY_BROKER_URL`: Celery broker URL (or `CELERY_TASK_ALWAYS_EAGER=true` for dev)
- `REDIS_URL`: Redis URL for rate limiting and Celery (optional)

### Frontend
- `VITE_API_BASE_URL`: Backend API URL
- `VITE_SENTRY_DSN`: Sentry DSN for error tracking

## Deployment

- Frontend: Vercel (automatic deployment from main branch)
- Backend: Render (Docker-based deployment)
- CI/CD: GitHub Actions

## License

MIT

# 🚀 Quick Start Guide - AI Resume Builder

Get your AI Resume Builder up and running in minutes!

---

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 7.0+
- Redis (optional, but recommended)
- Docker & Docker Compose (optional)

---

## ⚡ Quick Setup (5 minutes)

### 1. Clone and Navigate
```bash
cd Downloads/resume-builder
```

### 2. Start Services with Docker
```bash
docker-compose up -d
```

This starts:
- MongoDB on `localhost:27017`
- Redis on `localhost:6379`
- Backend on `localhost:8000`
- Frontend on `localhost:5173`

### 3. Configure Environment
```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
```

**Minimum required:**
```env
OPENROUTER_API_KEY=your-key-here
MONGO_URI=mongodb://admin:password@localhost:27017/resume_builder?authSource=admin
OPENAI_API_KEY=your-key-here
```

### 4. Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 5. Install Frontend Dependencies
```bash
cd ../frontend
npm install
```

### 6. Start Development Servers

**Option A: With Docker Compose (Recommended)**
```bash
docker-compose up
```

**Option B: Manual**
```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev

# Terminal 3 - Celery Worker (optional)
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

---

## 🎯 Test Your Setup

### 1. Check Health
```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "ai-resume-builder"
}
```

### 2. View API Docs
Open: http://localhost:8000/docs

### 3. Access Frontend
Open: http://localhost:5173

---

## 🧪 Test the Full Flow

### 1. Register a User
```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "full_name": "Test User"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

Save the `access_token` from the response.

### 3. Generate Resume
```bash
curl -X POST http://localhost:8000/api/v1/generate-resume \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "job_description": "Senior Software Engineer role requiring Python, FastAPI, React, and cloud expertise.",
    "template_preferences": {
      "tone": "professional",
      "bullets_per_section": 3
    },
    "format": "json"
  }'
```

---

## 📁 Project Structure

```
resume-builder/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── core/           # Config, security, logging
│   │   ├── db/             # Database connections
│   │   ├── middleware/     # Auth, rate limiting
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   └── workers/        # Background tasks
│   ├── tests/              # Test suite
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/         # Page components
│   │   ├── hooks/         # React hooks
│   │   └── services/      # API client
│   └── package.json       # Node dependencies
├── docker-compose.yml     # Docker setup
├── IMPLEMENTATION_SUMMARY.md
├── TESTING_GUIDE.md
└── QUICK_START.md (this file)
```

---

## 🔑 Required API Keys

### OpenRouter (Required)
Get from: https://openrouter.ai/keys
- Used for: LLM-powered resume generation

### OpenAI (Required for embeddings)
Get from: https://platform.openai.com/api-keys
- Used for: Text embeddings for RAG

### AWS S3 (Required for file storage)
Get from: AWS Console
- Used for: File storage (resumes, uploads)

---

## 🎨 Available Endpoints

### Authentication
- `POST /api/v1/register` - Register user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout

### Resumes
- `POST /api/v1/generate-resume` - Generate resume
- `GET /api/v1/resumes` - List resumes
- `GET /api/v1/resumes/{id}` - Get resume
- `DELETE /api/v1/resumes/{id}` - Delete resume

### File Upload
- `POST /api/v1/upload` - Upload file
- `GET /api/v1/uploads` - List uploads
- `DELETE /api/v1/uploads/{id}` - Delete upload

### RAG/Search
- `POST /api/v1/ingest` - Ingest document
- `POST /api/v1/search` - Search documents
- `DELETE /api/v1/documents` - Delete documents

---

## 🛠️ Common Commands

### Backend
```bash
# Run backend
uvicorn app.main:app --reload

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Start Celery beat
celery -A app.workers.celery_app beat --loglevel=info
```

### Frontend
```bash
# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint
```

### Docker
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild services
docker-compose up --build
```

---

## 🐛 Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
docker-compose ps mongodb

# View MongoDB logs
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb
```

### Redis Connection Issues
Redis is optional. The app will fall back to in-memory rate limiting if Redis is unavailable.

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Module Not Found
Make sure you're in the correct directory and have activated your virtual environment.

---

## 📚 Documentation

- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Testing Guide**: `TESTING_GUIDE.md`
- **Architecture**: `architecture_full.md`

---

## 🚀 Production Deployment

### Backend (Render)
1. Push to GitHub
2. Create new Web Service on Render
3. Connect GitHub repo
4. Set environment variables
5. Deploy

### Frontend (Vercel)
1. Push to GitHub
2. Import project to Vercel
3. Set environment variables
4. Deploy

See `SETUP_GUIDE.md` for detailed deployment instructions.

---

## 💡 Tips

1. **Use Docker Compose** for easiest setup
2. **Start with minimal config** - only set required API keys
3. **Check logs** if something doesn't work
4. **Read error messages** - they're helpful!
5. **Test endpoints** using Swagger UI at `/docs`

---

## 🎉 You're Ready!

Your AI Resume Builder is now running. Visit http://localhost:5173 to start building resumes!

**Next Steps:**
1. Create an account
2. Upload your existing resume (optional)
3. Generate a tailored resume for a job posting
4. Download as PDF

---

**Need Help?** Check the full documentation in `IMPLEMENTATION_SUMMARY.md` and `TESTING_GUIDE.md`

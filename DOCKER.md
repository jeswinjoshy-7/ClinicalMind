# ClinicalMind - Docker Deployment Guide

## 🐋 Quick Start

### Prerequisites
- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- Groq API Key ([Get it here](https://console.groq.com/))

### 1. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Groq API Key
nano .env  # or use your preferred editor
```

### 2. Build and Run

**Option A: Using the startup script (Recommended)**
```bash
./docker-start.sh
```

**Option B: Manual Docker Compose commands**
```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main UI dashboard |
| **Backend API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Swagger/OpenAPI docs |
| **Redis** | localhost:6379 | Cache layer (optional) |

---

## 📋 Docker Commands Reference

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Stop Services
```bash
# Stop without removing volumes
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

### Rebuild
```bash
# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

### Execute Commands Inside Container
```bash
# Backend container
docker exec -it clinicalmind-backend bash

# Frontend container
docker exec -it clinicalmind-frontend sh

# Redis CLI
docker exec -it clinicalmind-redis redis-cli
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Service | Description | Required |
|----------|---------|-------------|----------|
| `GROQ_API_KEY` | Backend | Groq LLM API key | ✅ Yes |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API URL | ❌ No (default: http://backend:8000) |
| `PYTHONUNBUFFERED` | Backend | Python output | ❌ No |
| `NODE_ENV` | Frontend | Node environment | ❌ No |

### Ports

| Port | Service | Can Change |
|------|---------|------------|
| 8000 | Backend API | ✅ Yes (edit docker-compose.yml) |
| 3000 | Frontend | ✅ Yes |
| 6379 | Redis | ✅ Yes |

---

## 💾 Data Persistence

Data is stored in Docker volumes:

| Volume | Purpose | Location |
|--------|---------|----------|
| `vectorstore_data` | FAISS vector databases | /app/data/vectorstore |
| `uploaded_docs` | Uploaded documents | /app/data/raw |
| `redis_data` | Redis cache | /data |

### Backup Data
```bash
# Create backup directory
mkdir -p ./backups

# Backup vector store
docker run --rm \
  -v clinicalmind_vectorstore_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/vectorstore-$(date +%Y%m%d).tar.gz /data
```

### Restore Data
```bash
docker run --rm \
  -v clinicalmind_vectorstore_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/vectorstore-20240101.tar.gz -C /
```

---

## 🏥 Production Deployment

### Kubernetes

```bash
# Generate Kubernetes manifests
docker-compose convert > k8s-deployment.yaml

# Or use kompose
kompose convert
```

### Environment-Specific Builds

```bash
# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Development (with hot reload)
docker-compose -f docker-compose.dev.yml up -d
```

### Scaling

```bash
# Scale backend to 3 replicas (requires load balancer)
docker-compose up -d --scale backend=3
```

---

## 🔍 Monitoring & Debugging

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Backend readiness
curl http://localhost:8000/ready

# Frontend health
curl http://localhost:3000
```

### Container Stats
```bash
docker stats clinicalmind-backend clinicalmind-frontend
```

### Inspect Container
```bash
docker inspect clinicalmind-backend
```

---

## ⚠️ Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Verify .env file exists and has GROQ_API_KEY
cat .env
```

### Frontend can't connect to backend
```bash
# Ensure both services are on the same network
docker-compose logs frontend

# Check NEXT_PUBLIC_API_URL in docker-compose.yml
```

### Vector store data lost after restart
```bash
# Ensure volumes are defined in docker-compose.yml
# Data persists in named volumes, not bind mounts
docker volume ls
```

### Port already in use
```bash
# Find process using port 8000 or 3000
lsof -i :8000
lsof -i :3000

# Or change ports in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 externally
```

---

## 🧹 Cleanup

### Remove all containers and volumes
```bash
docker-compose down -v
docker system prune -a
```

### Remove specific volume
```bash
docker volume rm clinicalmind_vectorstore_data
```

---

## 📚 Architecture

```
┌─────────────────┐
│   User Browser  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Frontend      │  Port 3000
│   (Next.js)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────┐
│   Backend       │─────▶│   Redis     │
│   (FastAPI)     │      │  (Cache)    │
└────────┬────────┘      └─────────────┘
         │
         ▼
┌─────────────────┐
│   FAISS         │
│   (Vector DB)   │
└─────────────────┘
```

---

## 🚀 Next Steps

1. **Upload Documents** - Use the Knowledge Base panel at http://localhost:3000
2. **Test Queries** - Try clinical questions in the chat interface
3. **Monitor Logs** - `docker-compose logs -f`
4. **Read API Docs** - http://localhost:8000/docs

For production deployment, see `DEPLOYMENT.md` for Kubernetes, AWS, and GCP guides.

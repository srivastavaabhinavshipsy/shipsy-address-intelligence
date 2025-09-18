# Docker Setup for Address Validation System

## Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- Make (optional, for using Makefile commands)

## Quick Start

### 1. Clone and Setup Environment
```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your GEMINI_API_KEY
nano .env
```

### 2. Build and Run with Docker Compose

#### Production Mode
```bash
# Build the images
docker-compose build

# Start the containers
docker-compose up -d

# View logs
docker-compose logs -f
```

#### Development Mode (with hot-reload)
```bash
# Build development images
docker-compose -f docker-compose.dev.yml build

# Start development containers
docker-compose -f docker-compose.dev.yml up
```

### 3. Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- Health Check: http://localhost:5000/health

## Using Make Commands

If you have `make` installed, you can use these shortcuts:

```bash
make build          # Build Docker images
make up             # Start containers in detached mode
make down           # Stop containers
make restart        # Restart containers
make logs           # View all logs
make logs-backend   # View backend logs only
make logs-frontend  # View frontend logs only
make clean          # Remove containers and images
make shell-backend  # Access backend container shell
make shell-frontend # Access frontend container shell
make reset-db       # Reset the database
```

## Project Structure

```
.
├── docker-compose.yml          # Production orchestration
├── docker-compose.dev.yml      # Development orchestration
├── Makefile                    # Convenience commands
├── .env.example                # Environment template
├── .dockerignore              # Global Docker ignore
├── backend/
│   ├── Dockerfile             # Backend container config
│   ├── .dockerignore         # Backend-specific ignores
│   ├── requirements.txt      # Python dependencies
│   ├── app.py                # Flask application
│   ├── database.py           # Database operations
│   ├── llm_validator.py     # AI validation logic
│   ├── validator.py         # Rule-based validation
│   └── virtual_numbers.json  # Virtual number pool
├── frontend/
│   ├── Dockerfile            # Frontend production container
│   ├── Dockerfile.dev        # Frontend development container
│   ├── .dockerignore        # Frontend-specific ignores
│   ├── package.json         # Node dependencies
│   └── src/                 # React source code
└── data/                    # Persistent data (created by Docker)
```

## Container Architecture

### Services
1. **backend**: Flask API server
   - Port: 5000
   - Persistent volumes: database, virtual_numbers.json
   - Environment: GEMINI_API_KEY required

2. **frontend**: React application
   - Port: 3000
   - Connects to backend via REACT_APP_API_URL
   - Production: Served with `serve`
   - Development: Uses React dev server

### Networks
- `app-network`: Internal bridge network for container communication

### Volumes
- `backend-data`: Persists SQLite database
- `virtual_numbers.json`: Mounted for virtual number persistence

## Environment Variables

### Required
- `GEMINI_API_KEY`: Your Google Gemini API key for AI validation

### Optional
- `REACT_APP_API_URL`: Backend URL (default: http://localhost:5000)
- `FLASK_ENV`: Flask environment (production/development)
- `PORT`: Backend port (default: 5000)

## Database Management

### Reset Database
```bash
# Using make
make reset-db

# Using docker exec
docker exec -it address-validation-backend python reset_database.py
```

### Backup Database
```bash
# Backup
docker cp address-validation-backend:/app/data/address_validation.db ./backup.db

# Restore
docker cp ./backup.db address-validation-backend:/app/data/address_validation.db
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild images
docker-compose build --no-cache
```

### Permission issues
```bash
# Fix volume permissions
docker exec -it address-validation-backend chown -R 1000:1000 /app/data
```

### Port conflicts
```bash
# Check if ports are in use
lsof -i :3000
lsof -i :5000

# Change ports in docker-compose.yml
# Example: "3001:3000" for frontend
```

### Database locked
```bash
# Restart backend container
docker-compose restart backend
```

## Production Deployment

### Using Docker Hub
```bash
# Build and tag images
docker build -t yourusername/address-validation-backend:latest ./backend
docker build -t yourusername/address-validation-frontend:latest ./frontend

# Push to registry
docker push yourusername/address-validation-backend:latest
docker push yourusername/address-validation-frontend:latest
```

### Using docker-compose in production
```bash
# Use production compose file with external images
docker-compose -f docker-compose.prod.yml up -d
```

## Security Notes

1. **Never commit `.env` file** - Use `.env.example` as template
2. **Use secrets management** in production (Docker Swarm secrets, Kubernetes secrets, etc.)
3. **Enable HTTPS** with reverse proxy (nginx, traefik) in production
4. **Limit container resources** in production:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 512M
   ```

## Monitoring

### Health Checks
Both containers have built-in health checks:
- Backend: `http://localhost:5000/health`
- Frontend: `http://localhost:3000`

### View resource usage
```bash
docker stats
```

### Container logs
```bash
# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

## Support

For issues or questions:
1. Check container logs: `docker-compose logs`
2. Verify environment variables: `docker-compose config`
3. Ensure Docker daemon is running: `docker info`
4. Check network connectivity: `docker network ls`
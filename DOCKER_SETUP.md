# Docker Setup for Bits and Bots

This guide explains how to run the Bits and Bots application in Docker.

## Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop) installed and running
- [Docker Compose](https://docs.docker.com/compose/) (usually included with Docker Desktop)

## Quick Start

### Using Docker Compose (Recommended)

1. **Prepare your environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials and other configuration
   ```

2. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

   The app will be available at `http://localhost:8000`

3. **Stop the container:**
   ```bash
   docker-compose down
   ```

### Using Docker Directly

1. **Build the image:**
   ```bash
   docker build -t bits-and-bots:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8000:8000 \
     --env-file .env \
     -v $(pwd)/src:/app/src \
     bits-and-bots:latest
   ```

## Configuration

### Environment Variables

The application requires a `.env` file with Supabase credentials. Create it from the template:

```bash
cp .env.example .env
```

Required variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase API key
- `BASE_URL`: The URL where your app will be accessed (e.g., `http://localhost:8000`)

### Volume Mounts

The `docker-compose.yml` includes volume mounts for:
- `./src:/app/src` - Application code (for development with auto-reload)
- `./static:/app/static` - Static files

For production, remove these volumes or make them read-only.

## Development

### Hot Reload

The docker-compose configuration mounts the `src` directory, allowing for hot-reload during development:

```bash
docker-compose up
# Edit files in src/ and changes will be reflected automatically
```

### Running Tests

```bash
docker-compose exec app pytest
```

### Linting

```bash
docker-compose exec app djlint src/bits_and_bots/web_templates/
```

## Production Deployment

For production, consider:

1. **Use specific Python version** - Currently using `python:3.14-slim`
2. **Remove volume mounts** - Remove the `volumes` section from docker-compose.yml
3. **Add reverse proxy** - Use Nginx or similar
4. **Health checks** - Included in Dockerfile
5. **Resource limits** - Add `deploy` section to docker-compose.yml:

```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

6. **Use a process manager** - Consider using `gunicorn` for production:

```dockerfile
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", \
     "bits_and_bots.main:app", "--bind", "0.0.0.0:8000"]
```

## Troubleshooting

### Container won't start
Check logs:
```bash
docker-compose logs -f app
```

### Port already in use
Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Access at localhost:8080
```

### Database connection errors
Verify `.env` file contains correct Supabase credentials:
```bash
docker-compose exec app python -c "from bits_and_bots.database import db; db()"
```

### File permissions issues
Ensure files in `src/` have correct permissions:
```bash
chmod -R 755 src/
```

## Useful Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f app

# Execute a command in the container
docker-compose exec app python -c "print('Hello')"

# Rebuild the image
docker-compose build --no-cache

# Remove all containers and volumes
docker-compose down -v
```

## Architecture

The setup uses a multi-stage build to:
1. Build stage: Install dependencies using `uv`
2. Runtime stage: Copy only necessary files and venv for smaller images

This keeps the final image size minimal while ensuring all dependencies are properly installed.

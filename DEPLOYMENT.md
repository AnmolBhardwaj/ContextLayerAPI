# Deployment Guide

## Development vs Production

### Development

```bash
python run.py
```

Default config uses `localhost:8000` with hot-reload enabled. Perfect for local development.

### Production

Use environment variables to override `config.yaml` settings. Follows the **12-factor app** methodology.

#### Environment Variables

```bash
# Server configuration
export CONTEXT_API_HOST="0.0.0.0"          # Listen on all interfaces
export CONTEXT_API_PORT="8000"             # Custom port
export CONTEXT_API_RELOAD="false"          # Disable hot-reload

# Run with Gunicorn (production ASGI server)
gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Docker Example

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CONTEXT_API_HOST="0.0.0.0"
ENV CONTEXT_API_RELOAD="false"

CMD ["gunicorn", "src.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

## CORS Configuration

By default, CORS is open (`allow_origins=["*"]`). For production, restrict to your domain:

**src/main.py:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Knowledge Base Updates

Knowledge files in `context/domains/` and `context/mappings/intent_map.yaml` can be updated **without restarting the server**.

### Update Workflow

1. Edit markdown files: `context/domains/{domain}/*.md`
2. Update intent map: `context/mappings/intent_map.yaml`
3. New requests automatically use updated content

No restart required. This enables:
- Real-time compliance rule updates
- A/B testing different context versions
- Rolling policy changes without downtime

## Monitoring

The API exposes a health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

Response includes version and live count of domains/intents:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "domains_available": 2,
  "intents_available": 5
}
```

Use this for Kubernetes liveness probes or ECS health checks.

## Security Best Practices

1. **Input Validation**: Domain and intent parameters are validated at the Pydantic layer
   - Only alphanumeric, underscore, and hyphen characters allowed
   - Max 100 characters (configurable)
   - Blocks path traversal attempts (e.g., `../../etc/passwd`)

2. **YAML Safety**: Uses `yaml.safe_load()`, not `load()` — prevents arbitrary code execution

3. **File Extension Filtering**: Only `.md` files are read from context directories

4. **CORS**: Review and restrict `allow_origins` in production

5. **Logging**: All operations are logged. Configure log aggregation (ELK, Datadog, etc.)

## Performance Considerations

- **Caching**: Intent map is loaded once per request (small YAML file)
- **File I/O**: Markdown files are read on demand (no caching layer)
  - For high-traffic scenarios, consider adding Redis caching
- **Concurrent Requests**: FastAPI/Uvicorn handle concurrent requests natively

## Scaling

1. **Horizontal**: Run multiple instances behind a load balancer
   - Each instance has independent access to the knowledge base
   - No shared state or sessions

2. **Knowledge Base**: Store in shared storage (S3, NFS) if adding a cache layer

3. **Worker Processes**: Use Gunicorn with multiple workers for CPU-bound workloads
   - Example: `gunicorn --workers 8 src.main:app`

## Troubleshooting

**"Domain not found" error:**
- Verify domain folder exists in `context/domains/`
- Domain names are case-sensitive

**Sections not appearing in response:**
- Check `context/mappings/intent_map.yaml` has correct section keys
- Section keys are lowercase with spaces replaced by underscores
- Example: `## Key Features` → `key_features`

**Intent not falling back to default:**
- Ensure `default` intent exists in `intent_map.yaml`
- Check `DEFAULT_INTENT` config value

## Logging

Logs are emitted to stdout (compatible with Docker/Kubernetes):

```
2025-04-10 10:23:45,123 - context_layer - INFO - Context Layer 1.0.0 started — 2 domain(s): [banking, ecommerce] | 5 intent(s): [...]
```

Configure log level via environment or settings.py.

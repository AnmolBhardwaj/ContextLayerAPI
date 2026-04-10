# Architecture & Design Decisions

## Core Philosophy

**Separation of Concerns**: Each layer has a single responsibility.

```
Controller (HTTP) → Resolver (Orchestration) → Builder (Filtering) → Response
                ↓                           ↓
              Models                  Sources + Parser
```

This ensures:
- Easy testing (each layer can be tested in isolation)
- Easy to understand (read top-to-bottom)
- Easy to modify (change one layer without touching others)

---

## Layer Responsibilities

### Controller (`src/api/context_controller.py`)

**What it does**: HTTP request/response handling only.

**What it does NOT do**:
- Never reads files directly
- Never parses markdown
- Never filters data

**Why this matters**: Controller code is boilerplate and changes rarely. Keeping it thin means your business logic is elsewhere.

```python
# ✅ GOOD: Delegates to resolver and builder
@router.post("/context", response_model=ContextResponse)
def get_context(request: ContextRequest) -> ContextResponse:
    all_sections, source_files, active_intent, include_keys = resolve_context(
        domain=request.domain,
        intent=request.intent,
    )
    context = build_context(all_sections=all_sections, include_keys=include_keys)
    return ContextResponse(...)
```

### Resolver (`src/core/resolver.py`)

**What it does**: Orchestration — coordinates file loading, parsing, and intent resolution.

**Returns**: A 4-tuple `(all_sections, source_files, active_intent, include_keys)`

**Key design decision**: Resolver returns `include_keys` so the builder never needs to reload the intent map.

```python
# ❌ BAD: Builder would have to reload YAML
def build_context(domain: str, intent: str) -> Dict[str, str]:
    intent_map = load_yaml_file(INTENT_MAP_PATH)  # Redundant!
    include_keys = intent_map[intent]["include"]
    ...

# ✅ GOOD: Builder just filters, resolver handles all logic
def build_context(all_sections: Dict[str, str], include_keys: List[str]) -> Dict[str, str]:
    return {key: all_sections[key] for key in include_keys if key in all_sections}
```

**Impact**: One YAML read per request, not two. Scales better.

### Builder (`src/core/builder.py`)

**What it does**: Filters sections by intent.

**Why a separate layer?**: 
- Resolver focuses on "what data exists"
- Builder focuses on "what data do we need"
- This separation makes intent logic testable independently

### Sources (`src/sources/`)

**What they do**: File I/O only. No parsing, no filtering.

```python
# ✅ GOOD: Just reads and returns raw content
def load_markdown_files(directory_path: Path) -> List[Dict[str, str]]:
    return [{"file": filename, "content": raw_content} for filename in files]

# ❌ BAD: Would be a "do-everything" layer
def load_markdown_files(directory_path: Path) -> Dict[str, str]:
    # parse
    # normalize keys
    # filter by intent
    # ...
```

### Parser (`src/utils/parser.py`)

**What it does**: Converts markdown to dict of sections.

**What it does NOT do**: Apply business logic (that's the resolver's job)

```python
# ✅ GOOD: Pure function, no side effects
def parse_markdown_sections(raw_content: str) -> Dict[str, str]:
    # regex split, extract sections
    return {key: content for key, content in sections}

# Test is trivial:
def test_parse():
    result = parse_markdown_sections("## Foo\nBar")
    assert result == {"foo": "Bar"}
```

---

## Security Architecture

### Input Validation Strategy

**Defense in depth**: Validate at the earliest opportunity.

1. **Pydantic Layer** (src/core/models.py)
   - Validates domain and intent BEFORE any file I/O
   - Regex pattern: `^[a-zA-Z0-9_-]{1,100}$`
   - Blocks path traversal (`../../etc/passwd`) immediately
   - No exception handling needed downstream

```python
@field_validator("domain", "intent")
@classmethod
def validate_identifier(cls, v: str) -> str:
    pattern = rf"^[a-zA-Z0-9_-]{{1,{MAX_IDENTIFIER_LENGTH}}}$"
    if not re.match(pattern, v):
        raise ValueError("invalid characters")
    return v
```

2. **File Extension Filter** (src/sources/markdown_source.py)
   - Only reads `.md` files
   - Prevents reading arbitrary files

3. **YAML Parsing** (src/sources/config_source.py)
   - Uses `yaml.safe_load()`, not `yaml.load()`
   - Prevents arbitrary code execution

### Why This Matters

An attacker cannot:
- Read arbitrary files (inputs sanitized + extension filtered)
- Execute code (YAML safely loaded)
- Exhaust resources (max identifier length imposed)

---

## Configuration Management

### The 12-Factor App Principle

> "Store config in the environment"

**src/core/settings.py** implements this:

1. **Defaults**: Start with `config.yaml` (git-tracked)
2. **Overrides**: Environment variables take precedence for production

```python
# config.yaml has dev defaults
SERVER_HOST: str = os.getenv("CONTEXT_API_HOST", _cfg["server"]["host"])

# Production:
export CONTEXT_API_HOST=0.0.0.0
export CONTEXT_API_PORT=443
# Now running on 0.0.0.0:443 without code changes
```

**Benefits**:
- Same code runs in dev, staging, and production
- No "dev vs prod" branches
- Secrets never in version control (env vars are injected by deployment system)

### No Hardcoded Values

Every `.md` file path, every config value, flows through `settings.py`.

```python
# ✅ GOOD
from src.core.settings import DOMAINS_PATH
domain_dir = DOMAINS_PATH / domain

# ❌ BAD: Someone will forget to update it
domain_dir = Path("context/domains") / domain
```

This is why changing file locations requires ONE change in `config.yaml`, not grep-and-replacing through 10 files.

---

## Testing Strategy

### Unit Tests

**What they test**: Logic in isolation.

```python
# src/utils/parser.py is a pure function — easy to test
def test_key_normalisation():
    raw = "## Tone And Style\nBe friendly."
    result = parse_markdown_sections(raw)
    assert "tone_and_style" in result
```

### Integration Tests

**What they test**: Components working together.

```python
# src/core/resolver.py coordinates multiple layers
def test_known_domain_and_intent():
    all_sections, source_files, active_intent, include_keys = resolve_context(
        domain="banking",
        intent="summarise",
    )
    assert active_intent == "summarise"
    assert "summarise_guidelines" in include_keys
```

### Why No API Tests in This Repo?

This is intentional. The FastAPI layer is boilerplate — all logic is in resolver/builder/parser, which are unit-tested. If resolver tests pass, API tests would be redundant.

In production, you'd add:
- E2E tests (hit the real endpoint)
- Performance tests (load testing)
- Contract tests (API schema verification)

But at this stage, unit + integration tests are sufficient to verify architecture.

---

## Data Flow Example

### Request: `POST /api/v1/context?domain=banking&intent=support&explain=true`

```
1. FastAPI validates input → ContextRequest (Pydantic validates domain/intent)

2. Controller calls resolver
   resolver_context(domain="banking", intent="support")

3. Resolver:
   a. Loads intent_map.yaml
   b. Finds intent "support" exists → active_intent = "support"
   c. Extracts include_keys = ["product_overview", "tone_and_style", ...]
   d. Loads banking_context.md + writing_guidelines.md (via markdown_source)
   e. Parses each file into sections (via parser)
   f. Returns (all_sections={9 keys}, source_files=[...], active_intent="support", include_keys=[...])

4. Controller calls builder
   builder_context(all_sections={...}, include_keys=[...])

5. Builder:
   a. Filters all_sections to keep only keys in include_keys
   b. Returns {5 key: value pairs}

6. Controller builds response
   ContextResponse(intent="support", domain="banking", context={...}, meta={...})

7. FastAPI serializes to JSON + sends to client
```

**Why this is clean**:
- Each layer has one job
- Easy to trace a bug
- Easy to measure performance (which layer is slow?)
- Easy to unit-test each layer independently

---

## Deployment Considerations

### Production-Ready Features

1. **Logging**: Structured logging with timestamps
2. **Health Check**: `/api/v1/health` for Kubernetes probes
3. **CORS**: Middleware enabled, configurable
4. **Modern FastAPI**: Uses `lifespan` context manager (not deprecated `@app.on_event`)
5. **Environment Variables**: Follows 12-factor app
6. **Error Handling**: Graceful startup failures with logging

### What to Add Later

- API rate limiting (Redis-backed)
- Request tracing (OpenTelemetry)
- Schema validation for knowledge base (JSONSchema)
- Cache layer for intent map (Redis)
- Metrics (Prometheus)

These are orthogonal to the core architecture and can be added without changing core logic.

---

## Key Takeaways

| Principle | Implementation |
|---|---|
| **Single Responsibility** | Controller, Resolver, Builder, Parser are separate |
| **Dependency Injection** | Constants flow from settings.py; functions take parameters |
| **Security by Default** | Validation at Pydantic layer before any I/O |
| **Testability** | Pure functions (parser), isolated layers (each testable alone) |
| **Configuration Management** | YAML + env vars (12-factor app) |
| **Deployment Ready** | Logging, health checks, CORS, modern FastAPI |
| **Zero Magic** | No metaclasses, no decorators, no implicit behavior |

This is an architecture you can scale: 100 requests/sec or 100k requests/sec, it runs the same way.

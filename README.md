# Context Layer API

A domain-agnostic context retrieval service. Drop a folder of Markdown files, define which sections belong to which intent in one YAML file, and the API handles the rest.

Built with **FastAPI**, **Pydantic v2**, and **PyYAML**. Zero database. Zero ORM. One config file.

---

## Architecture

```
POST /context  ──►  controller
                    │
                    ▼
resolver  ──►  markdown_source  ──►  .md files
│       └►  config_source    ──►  intent_map.yaml
│       └►  parser
▼
builder   (filters sections by intent)
│
▼
ContextResponse
```

| Layer | File | Responsibility |
|---|---|---|
| Router | `src/api/context_controller.py` | HTTP in/out, error mapping |
| Resolver | `src/core/resolver.py` | Domain lookup, intent resolution, section parsing |
| Builder | `src/core/builder.py` | Section filtering by intent |
| Sources | `src/sources/` | File I/O (markdown + YAML) |
| Parser | `src/utils/parser.py` | `## Heading` → `{key: content}` |
| Models | `src/core/models.py` | Pydantic request/response contracts |
| Settings | `src/core/settings.py` | Single config loader; all constants flow from here |

**Rules enforced by the architecture:**
- The controller only calls the resolver and builder — never sources or parser directly.
- The resolver returns a 4-tuple so the builder never needs to reload the intent map.
- All file paths derive from `settings.py`; no hardcoded strings anywhere else.

---

## Quick Start

```bash
# 1. Enter the project folder
cd context-layer

# 2. Create and activate a virtualenv
py -3 -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python run.py
# → http://127.0.0.1:8000
# → Docs: http://127.0.0.1:8000/docs
```

---

## Architecture Highlights

### Design Principles

**Layer Separation**: Each layer has a single responsibility and clear boundaries.
- Controller never reads files directly — it calls resolver & builder only
- Resolver never filters — it returns all data; builder does filtering
- Sources never parse — they return raw content; parser does parsing

**Configuration-Driven**: Every setting flows from `config.yaml` via `settings.py`. No hardcoded values anywhere else.

**Security by Default**: 
- Input validation at Pydantic layer (blocks path traversal before file I/O)
- YAML safely loaded (not `load()`, uses `safe_load()`)
- File paths restricted to `.md` files only

**12-Factor App**: Environment variables override config for production deployments.

### Deployment Ready

- Full logging with startup/shutdown hooks
- CORS middleware enabled (configurable)
- Modern FastAPI lifespan events (not deprecated `@app.on_event`)
- Environment variable support for production
- Health check endpoint for Kubernetes/ECS probes

See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup, Docker examples, and security best practices.

---

## Configuration

Everything is in config.yaml at the project root. No Python changes needed.

```yaml
api:
  title: "Context Layer API"
  version: "1.0.0"
  prefix: "/api/v1"        # Change the URL prefix here

server:
  host: "127.0.0.1"
  port: 8000
  reload: true             # Set false in production

context:
  base_path: "context"          # Where your knowledge lives
  default_intent: "default"     # Fallback when intent is unknown

validation:
  max_identifier_length: 100    # Max chars for domain/intent params
```

## Adding a New Domain

- Create a folder under `context/domains/your_domain/`
- Add one or more `.md` files using `## Section Name` headings
- Add sections to `context/mappings/intent_map.yaml` under the relevant intent keys

That's it. No code changes. The new domain appears instantly in `GET /domains`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Status, version, domain + intent counts |
| GET | `/api/v1/domains` | All domains with file + section counts |
| GET | `/api/v1/intents` | All intent keys from intent_map.yaml |
| GET | `/api/v1/domains/{domain}/sections` | Section keys available for a domain |
| POST | `/api/v1/context` | Retrieve filtered context |

### POST /api/v1/context

**Request**

```json
{
  "domain": "banking",
  "intent": "summarise",
  "explain": true
}
```

**Response**

```json
{
  "intent": "summarise",
  "domain": "banking",
  "context": {
    "product_overview": "...",
    "tone_and_style": "...",
    "summarise_guidelines": "..."
  },
  "meta": {
    "intent_requested": "summarise",
    "intent_matched": "summarise",
    "sources_loaded": ["banking_context.md", "writing_guidelines.md"],
    "sections_found": 9,
    "sections_returned": 4
  }
}
```

- `explain: false` (default) omits the `meta` block entirely.
- An unknown intent falls back to the default intent — no error.
- An unknown domain returns 404.
- Invalid characters in domain or intent return 422.

## Intent Map

`context/mappings/intent_map.yaml` controls what each intent returns:

```yaml
summarise:
  include:
    - product_overview
    - tone_and_style
    - summarise_guidelines

full:
  include: []   # empty = return all available sections
```

Section keys are derived from `## Heading` lines — lowercased, spaces replaced with underscores.

---

## Real-World Use Case: Banking Compliance

### The Problem

Your AI support bot answers customer questions inconsistently:
- One response says "30-day return window"
- Another says "14-day window"
- No audit trail of what guidelines were consulted
- Compliance team updates a Notion doc, but developers don't know

### The Solution

```bash
# Compliance team updates context (no code change, no restart)
context/domains/banking/compliance.md         # KYC steps
context/domains/banking/fraud_detection.md    # Fraud rules
context/mappings/intent_map.yaml              # Maps "support" intent to these sections
```

When your bot receives a customer question, it calls:

```bash
POST /api/v1/context
{
  "domain": "banking",
  "intent": "support",
  "explain": true  # ← audit trail
}
```

Response includes:
```json
{
  "context": {
    "kyc_verification": "Verify ID before disclosing...",
    "fraud_detection": "Flag transactions that...",
    "tone_and_style": "Use professional tone..."
  },
  "meta": {
    "sources_loaded": ["compliance.md", "fraud_detection.md", "writing_guidelines.md"],
    "sections_returned": 3
  }
}
```

### Why This Matters

✅ **Compliance team owns knowledge**, developers own code (no merge conflicts)  
✅ **Updates take effect immediately** (no code deploy, no restart)  
✅ **Audit trail**: `sources_loaded` proves which guidelines were consulted  
✅ **Deterministic**: No hallucination, no semantic search randomness  
✅ **Cost**: No LLM calls for document retrieval (just Markdown parsing)

---

## How It Scales

| Scale | Workflow | Benefit |
|---|---|---|
| **Solo Dev** | Stop embedding guidelines in prompts. Version them in Markdown. | One source of truth. Free. No prompt bloat. |
| **Small Team** | Product, support, and dev teams edit their own `.md` files. Git is the audit trail. | Non-developers manage knowledge. No code reviews needed. |
| **Medium Team** | Compliance owns `compliance.md`, Product owns `messaging.md`. Push = instant deploy. | Cross-team collaboration without code coordination. Auditable. Instant rollback. |
| **Enterprise** | 12 product lines, 50 agents, 3 regions. Teams manage domains independently. | Scale to 100 concurrent chats. Regional A/B testing. Zero deployment risk. |

**See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed scaling examples at each stage.**

---

## When to Use This

**Use Context Layer if:**
- You have structured domain knowledge (policies, guidelines, rules)
- Outputs must be consistent and auditable
- Non-developers manage the knowledge (compliance, product, legal teams)
- You want deterministic behavior (no LLM-based retrieval)
- You need fast, cheap context delivery (no vector DB, no embeddings)

**Use RAG / LangChain instead if:**
- Your knowledge base is unstructured documents (PDFs, blogs, news)
- Fuzzy semantic matching is important (find similar documents)
- You're building complex pipelines (tool use, memory, agents)
- You want the LLM to reason over retrieved content (semantic search + reasoning)

---

## Why Not Just [Alternative]?

### vs. Embedding Guidelines in the System Prompt

| Aspect | System Prompt | Context Layer |
|---|---|---|
| **Update strategy** | Recompile prompt, redeploy code | Update Markdown file |
| **Audit trail** | None—prompt is embedded in code | Full trail—`sources_loaded` in response |
| **Team collaboration** | Developers must update; merges; CI/CD | Non-developers can update; no deployment |
| **Consistency** | Hard to verify which version is running | API returns exact version consulted |
| **Scaling** | Prompt bloats quickly | Scales to thousands of sections |

### vs. RAG Systems (LangChain, LlamaIndex)

| Aspect | RAG | Context Layer |
|---|---|---|
| **What it does** | Semantic search + document retrieval | Intent-driven context filtering |
| **Determinism** | Non-deterministic (rankings vary) | Completely deterministic |
| **Setup** | Vector DB, embeddings, infrastructure | Just Markdown files |
| **Cost** | Embedding API calls + LLM calls | File reads only |
| **Audit trail** | "Retrieved docs X, Y, Z" (fuzzy) | "Sections rule1, rule2, rule3" (exact) |
| **When to use** | Find *similar* documents | Guarantee *specific* sections |

### vs. LLM-Based Context Routing

*"Why not let an LLM decide what context to load?"*

Because:
- ❌ Expensive (LLM call for every request)
- ❌ Non-deterministic (different inference = different routing)
- ❌ Harder to audit (LLM reasoning is a black box)
- ✅ Use rule-based routing if output consistency matters (finance, healthcare, legal)
- ✅ Use LLM routing if your rules are too complex to encode (general reasoning)

---

## Tests

```bash
pytest tests/ -v
```

| Test file | Covers |
|---|---|
| `tests/test_parser.py` | Section parsing, key normalisation, edge cases |
| `tests/test_resolver.py` | Domain resolution, intent fallback, unknown domain error |

## Project Structure

```
context-layer/
├── config.yaml                  ← the only file you need to edit
├── run.py                       ← entry point
├── requirements.txt
├── README.md
├── src/
│   ├── main.py                  ← FastAPI app factory
│   ├── api/
│   │   └── context_controller.py
│   ├── core/
│   │   ├── settings.py          ← loads config.yaml; all constants live here
│   │   ├── models.py            ← Pydantic contracts
│   │   ├── resolver.py          ← domain + intent resolution
│   │   └── builder.py           ← section filtering
│   ├── sources/
│   │   ├── markdown_source.py   ← reads .md files
│   │   └── config_source.py     ← reads .yaml files
│   └── utils/
│       └── parser.py            ← ## heading parser
├── context/
│   ├── domains/
│   │   ├── banking/
│   │   └── ecommerce/
│   ├── global/                  ← sections injected into every domain
│   └── mappings/
│       └── intent_map.yaml
├── examples/                    ← sample request bodies
└── tests/
```

---

## AI-Assisted Setup Guide

You don't need to manually write context files. Use AI (Claude, ChatGPT, or GitHub Copilot) to generate them.

### Method 1: Using Claude/ChatGPT

**Prompt Template:**
```
Generate a markdown knowledge base for a [DOMAIN/USE_CASE] with clear sections.

Use this exact format — ONLY ## headings (not ### or #):

## Section Name
Content here. Be concise, 2–3 sentences max per section.

## Another Section
More content.

Requirements:
- 5–8 sections total
- Each section 1–3 sentences only
- Use ## heading level ONLY
- Focus on: [KEY_TOPICS, GUIDELINES, RULES]
```

**Example prompts:**

**For Banking:**
```
Generate a markdown knowledge base for a retail banking AI assistant.

Sections to include:
- Account Security Best Practices
- KYC Verification Steps
- Transaction Limits by Account Type
- Common Fraud Patterns to Flag
- Escalation Procedures

Use the exact ## heading format shown above. Keep each section to 2–3 sentences.
```

**For Healthcare:**
```
Generate a markdown knowledge base for a patient support chatbot.

Sections to include:
- HIPAA Compliance Checklist
- Symptom Triaging Guidelines
- When to Escalate to Doctor
- Appointment Booking Rules
- Prescription Information Sharing

Keep content brief and authoritative.
```

**For E-Commerce:**
```
Generate a markdown knowledge base for a customer support AI.

Sections to include:
- Return and Refund Policy
- Shipping Times by Region
- How to Handle Angry Customers
- Discount Code Redemption Rules
- Order Cancellation Window

Format as ## sections, 2–3 sentences each.
```

### Method 2: Using GitHub Copilot

1. Create a new `.md` file in your domain folder  
2. Type a comment explaining what you need:
   ```markdown
   # Banking Support Guidelines
   <!-- Generate sections for: customer verification, fraud detection, tone requirements, writing standards -->
   ```
3. Press `Ctrl+Shift+A` (Copilot Chat) or click the Copilot icon
4. Ask: _"Generate sections for this file as ## headings"_
5. Copilot will suggest content → Accept/edit → Copy the output → Paste into the file

### Method 3: Paste Generated Content

1. Get AI output (from Claude, ChatGPT, Copilot)
2. Create a new file: `context/domains/your_domain/your_topic.md`
3. Paste the markdown directly
4. Update `context/mappings/intent_map.yaml` to reference the new section keys

### Registering New Sections in intent_map.yaml

After adding a `.md` file with new sections, update `intent_map.yaml`:

```yaml
# Extract section keys from your markdown (lowercase, spaces → underscores)
# Example: "## KYC Verification Steps" → "kyc_verification_steps"

your_intent:
  include:
    - existing_section
    - kyc_verification_steps      # newly added
    - fraud_detection_guidelines   # newly added
```

Then restart the server — new sections appear immediately in API responses.

### Example: Add a New Domain in 3 Steps

**Step 1: Use AI to generate content**
```
Generate a markdown knowledge base for credit lending decisions.

Sections:
- Credit Score Interpretation
- Debt-to-Income Ratio Rules  
- Red Flags for Rejection
- Documentation Requirements
- Appeal Process

Format as ## sections.
```

**Step 2: Create file structure**
```
context/domains/lending/lending_policy.md  ← paste AI output here
```

**Step 3: Register in intent map**
```yaml
# context/mappings/intent_map.yaml

lending_approval:
  include:
    - credit_score_interpretation
    - debt_to_income_ratio_rules
    - documentation_requirements

lending_denial:
  include:
    - red_flags_for_rejection
    - appeal_process
    - documentation_requirements
```

**Done.** Call the API:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/context \
  -H "Content-Type: application/json" \
  -d '{"domain":"lending","intent":"lending_approval","explain":true}'
```

---

## Content Best Practices

| Do | Don't |
|---|---|
| Use ## headings only | Use #### or other heading levels |
| Keep sections concise (2–3 sentences) | Write walls of text |
| Use bullet points for lists | Use paragraph form for multiple items |
| Spell out acronyms on first use (KYC) | Use acronyms without explanation |
| Include examples when helpful | Make sections too theoretical |
| Update frequently via easy copy/paste | Keep outdated hardcoded prompts |

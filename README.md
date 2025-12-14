# Cavepedia v2

* A RBAC managed cave information system with document processing, semantic search, and an AI chat interface. Email paul@bigcavemaps.com for access. Only about 60% vibe coded.
* URL: https://chat.caving.dev

## Architecture

```
                                    +------------------+
                                    |     Auth0        |
                                    |   (RBAC roles)   |
                                    +--------+---------+
                                             |
                                             v
+------------------+              +----------+----------+
|                  |   WebSocket  |                     |
|     Browser      +------------->+    web/ (Next.js)   |
|                  |              |    - CopilotKit UI  |
+------------------+              |    - Auth0 SSO      |
                                  +----------+----------+
                                             |
                                             | AG-UI Protocol
                                             v
                                  +----------+----------+
                                  |   web/agent/        |
                                  |   (PydanticAI)      |
                                  |   - Google Gemini   |
                                  |   - x-user-roles    |
                                  +----------+----------+
                                             |
                                             | Streamable HTTP
                                             v
                                  +----------+----------+
                                  |      mcp/           |
                                  |   (FastMCP Server)  |
                                  |   - Semantic search |
                                  |   - Role filtering  |
                                  +----------+----------+
                                             |
                        +--------------------+--------------------+
                        |                                         |
                        v                                         v
             +----------+----------+                   +----------+----------+
             |     PostgreSQL      |                   |       Cohere        |
             |     (pgvector)      |                   |    (Embeddings)     |
             |   - embeddings      |                   +---------------------+
             |   - metadata        |
             |   - batches         |
             +----------+----------+
                        ^
                        |
             +----------+----------+
             |      poller/        |
             |  (Document Pipeline)|
             |   - PDF splitting   |
             |   - OCR (Claude)    |
             |   - Embeddings      |
             +----------+----------+
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
   +------+------+ +----+----+ +------+------+
   | S3: import  | | S3: files| | S3: pages  |
   +-------------+ +----------+ +-------------+
```

## Components

| Component | Description | Tech Stack |
|-----------|-------------|------------|
| **web/** | Frontend application with chat UI | Next.js, CopilotKit, Auth0 |
| **web/agent/** | AI agent for answering cave questions | PydanticAI, AG-UI, Google Gemini |
| **mcp/** | MCP server exposing semantic search tools | FastMCP, Starlette, Cohere |
| **poller/** | Document ingestion and processing pipeline | Python, Claude API, Cohere |

## Data Flow

1. **Document Ingestion** (poller)
   - PDFs uploaded to `s3://cavepediav2-import`
   - Poller moves to `s3://cavepediav2-files`, splits into pages
   - Pages stored in `s3://cavepediav2-pages`
   - Claude extracts text via OCR
   - Cohere generates embeddings
   - Stored in PostgreSQL with pgvector

2. **Search & Chat** (mcp + agent)
   - User authenticates via Auth0 (roles assigned)
   - User asks question via web UI
   - Web API extracts user roles from session, passes to agent
   - Agent creates MCP connection with `x-user-roles` header
   - MCP queries pgvector, filtering by user's roles
   - Agent synthesizes response with citations

## Getting Started

See individual component READMEs:
- [web/README.md](web/README.md) - Frontend and agent setup
- [poller/README.md](poller/README.md) - Document processing pipeline

## Environment Variables

Each component requires its own environment variables. See the respective READMEs for details.

| Component | Key Variables |
|-----------|---------------|
| **web/** | `AUTH0_*`, `AGENT_URL` |
| **web/agent/** | `GOOGLE_API_KEY`, `CAVE_MCP_URL` |
| **mcp/** | `COHERE_API_KEY`, `DB_*` |
| **poller/** | `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, `AWS_*`, `DB_*` |

**Never commit `.env` files** - they are gitignored.

## CI/CD

Gitea Actions workflows build and push Docker images on changes to `main`:

| Workflow | Trigger Path | Image |
|----------|--------------|-------|
| build-push-web | `web/**` (excluding agent) | `cavepediav2-web:latest` |
| build-push-agent | `web/agent/**` | `cavepediav2-agent:latest` |
| build-push-poller | `poller/**` | `cavepediav2-poller:latest` |
| build-push-mcp | `mcp/**` | `cavepediav2-mcp:latest` |

## License

MIT

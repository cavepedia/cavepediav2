# Cavepedia v2

* A RBAC managed cave information system with document processing, semantic search, and an AI chat interface. Email paul@bigcavemaps.com for access. Only about 60% vibe coded.
* URL: https://chat.caving.dev

## Architecture

```
                                    +------------------+
                                    |     Auth0        |
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
                                             v
                                  +----------+----------+
                                  |   web/agent/        |
                                  |   (LangGraph)       |
                                  |   - Google Gemini   |
                                  +----------+----------+
                                             |
                                             v
                                  +----------+----------+
                                  |      mcp/           |
                                  |   (FastMCP Server)  |
                                  |   - Semantic search |
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
| **web/agent/** | AI agent for answering cave questions | LangGraph, Google Gemini |
| **mcp/** | MCP server exposing semantic search tools | FastMCP, Cohere |
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
   - User asks question via web UI
   - Agent calls MCP tools for semantic search
   - MCP queries pgvector for relevant documents
   - Agent synthesizes response with citations

## Getting Started

See individual component READMEs:
- [web/README.md](web/README.md) - Frontend and agent setup
- [poller/README.md](poller/README.md) - Document processing pipeline

## Environment Variables

Each component requires its own environment variables. See the respective READMEs for details.

**Never commit `.env` files** - they are gitignored.

## CI/CD

Gitea Actions workflows build and push Docker images on changes to `main`:

| Workflow | Trigger Path | Image |
|----------|--------------|-------|
| build-push-web | `web/**` (excluding agent) | `cavepediav2-web:latest` |
| build-push-agent | `web/agent/**` | `cavepediav2-agent:latest` |
| build-push-poller | `poller/**` | `cavepediav2-poller:latest` |

## License

MIT

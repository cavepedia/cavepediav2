# Cavepedia Web

Next.js frontend with integrated LangGraph agent for Cavepedia.

## Project Structure

```
web/
├── src/              # Next.js application
├── agent/            # LangGraph agent (Python)
│   ├── main.py       # Agent graph definition
│   ├── langgraph.json
│   ├── pyproject.toml
│   └── Dockerfile    # Production container
└── ...
```

## Prerequisites

- Node.js 18+
- Python 3.12+
- [pnpm](https://pnpm.io/installation) (recommended) or npm/yarn/bun
- Google AI API Key (for the LangGraph agent)

## Development

### 1. Install dependencies

```bash
pnpm install
```

This also installs the agent's Python dependencies via the `install:agent` script.

### 2. Set up environment variables

```bash
# Agent environment
cp agent/.env.example agent/.env
# Edit agent/.env with your API keys
```

### 3. Start development servers

```bash
pnpm dev
```

This starts both the Next.js UI and LangGraph agent servers concurrently.

## Agent Deployment

The agent is containerized for production deployment using the official LangGraph API server image.

### Building the Docker image

```bash
cd agent
docker build -t cavepediav2-agent .
```

### Running in production

The agent requires PostgreSQL and Redis for persistence and pub/sub:

```bash
docker run \
  -p 8123:8000 \
  -e REDIS_URI="redis://redis:6379" \
  -e DATABASE_URI="postgres://user:pass@postgres:5432/langgraph" \
  -e GOOGLE_API_KEY="your-key" \
  -e LANGSMITH_API_KEY="your-key" \
  cavepediav2-agent
```

Or use Docker Compose with the required services:

```yaml
services:
  redis:
    image: redis:7

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: langgraph
      POSTGRES_USER: langgraph
      POSTGRES_PASSWORD: langgraph

  agent:
    image: git.seaturtle.pw/cavepedia/cavepediav2-agent:latest
    ports:
      - "8123:8000"
    environment:
      REDIS_URI: redis://redis:6379
      DATABASE_URI: postgres://langgraph:langgraph@postgres:5432/langgraph
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    depends_on:
      - redis
      - postgres
```

### CI/CD

The agent image is automatically built and pushed to `git.seaturtle.pw/cavepedia/cavepediav2-agent:latest` on push to `main` via Gitea Actions.

## Available Scripts

- `dev` - Start both UI and agent servers
- `dev:ui` - Start only Next.js
- `dev:agent` - Start only LangGraph agent
- `build` - Build Next.js for production
- `start` - Start production server
- `lint` - Run ESLint
- `install:agent` - Install agent Python dependencies

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [CopilotKit Documentation](https://docs.copilotkit.ai)
- [Next.js Documentation](https://nextjs.org/docs)
- [Auth0 Next.js SDK Examples](https://github.com/auth0/nextjs-auth0/blob/main/EXAMPLES.md)

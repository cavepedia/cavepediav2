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

- Node.js 24+
- Python 3.13
- npm
- Google AI API Key (for the LangGraph agent)

## Development

### 1. Install dependencies

```bash
npm install
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
npm run dev
```

This starts both the Next.js UI and LangGraph agent servers concurrently.

## Agent Deployment

The agent is containerized for production deployment.

### Building the Docker image

```bash
cd agent
docker build -t cavepediav2-agent .
```

### Running in production

The agent requires PostgreSQL and Valkey for persistence and pub/sub:

```bash
docker run \
  -p 8123:8000 \
  -e REDIS_URI="redis://valkey:6379" \
  -e DATABASE_URI="postgres://user:pass@postgres:5432/langgraph" \
  -e GOOGLE_API_KEY="your-key" \
  -e LANGSMITH_API_KEY="your-key" \
  cavepediav2-agent
```

Or use Docker Compose with the required services:

```yaml
services:
  valkey:
    image: valkey/valkey:9

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
      REDIS_URI: redis://valkey:6379
      DATABASE_URI: postgres://langgraph:langgraph@postgres:5432/langgraph
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    depends_on:
      - valkey
      - postgres
```

### CI/CD

The agent image is automatically built and pushed to `git.seaturtle.pw/cavepedia/cavepediav2-agent:latest` on push to `main` via Gitea Actions.

## Web Deployment

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGGRAPH_DEPLOYMENT_URL` | Yes | `http://localhost:8000` | URL to the LangGraph agent |
| `AUTH0_SECRET` | Yes | - | Session encryption key (`openssl rand -hex 32`) |
| `AUTH0_DOMAIN` | Yes | - | Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | Yes | - | Auth0 application client ID |
| `AUTH0_CLIENT_SECRET` | Yes | - | Auth0 application client secret |
| `APP_BASE_URL` | Yes | - | Public URL of the app |
| `LANGSMITH_API_KEY` | No | - | LangSmith API key for tracing |

### Docker Compose (Full Stack)

```yaml
services:
  web:
    image: git.seaturtle.pw/cavepedia/cavepediav2-web:latest
    ports:
      - "3000:3000"
    environment:
      LANGGRAPH_DEPLOYMENT_URL: http://agent:8000
      AUTH0_SECRET: ${AUTH0_SECRET}
      AUTH0_DOMAIN: ${AUTH0_DOMAIN}
      AUTH0_CLIENT_ID: ${AUTH0_CLIENT_ID}
      AUTH0_CLIENT_SECRET: ${AUTH0_CLIENT_SECRET}
      APP_BASE_URL: ${APP_BASE_URL}
    depends_on:
      - agent

  agent:
    image: git.seaturtle.pw/cavepedia/cavepediav2-agent:latest
    environment:
      REDIS_URI: redis://valkey:6379
      DATABASE_URI: postgres://langgraph:langgraph@postgres:5432/langgraph
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    depends_on:
      - valkey
      - postgres

  valkey:
    image: valkey/valkey:9

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: langgraph
      POSTGRES_USER: langgraph
      POSTGRES_PASSWORD: langgraph
```

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

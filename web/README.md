# Cavepedia Web

Next.js frontend with integrated PydanticAI agent for Cavepedia.

## Project Structure

```
web/
├── src/              # Next.js application
├── agent/            # PydanticAI agent (Python)
│   ├── main.py       # Agent definition
│   ├── server.py     # FastAPI server with AG-UI
│   └── pyproject.toml
└── ...
```

## Prerequisites

- Node.js 24+
- Python 3.13
- npm
- Google AI API Key (for the PydanticAI agent)

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

This starts both the Next.js UI and PydanticAI agent servers concurrently.

## Agent Deployment

The agent can be containerized for production deployment.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google AI API key for Gemini |

### Running in production

```bash
cd agent
uv run uvicorn server:app --host 0.0.0.0 --port 8000
```

## Web Deployment

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGGRAPH_DEPLOYMENT_URL` | Yes | `http://localhost:8000` | URL to the agent |
| `AUTH0_SECRET` | Yes | - | Session encryption key (`openssl rand -hex 32`) |
| `AUTH0_DOMAIN` | Yes | - | Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | Yes | - | Auth0 application client ID |
| `AUTH0_CLIENT_SECRET` | Yes | - | Auth0 application client secret |
| `APP_BASE_URL` | Yes | - | Public URL of the app |

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
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
```

## Available Scripts

- `dev` - Start both UI and agent servers
- `dev:ui` - Start only Next.js
- `dev:agent` - Start only PydanticAI agent
- `build` - Build Next.js for production
- `start` - Start production server
- `lint` - Run ESLint
- `install:agent` - Install agent Python dependencies

## References

- [PydanticAI Documentation](https://ai.pydantic.dev/)
- [CopilotKit Documentation](https://docs.copilotkit.ai)
- [Next.js Documentation](https://nextjs.org/docs)
- [Auth0 Next.js SDK Examples](https://github.com/auth0/nextjs-auth0/blob/main/EXAMPLES.md)

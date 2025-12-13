# Cavepedia

A caving assistant built with [PydanticAI](https://ai.pydantic.dev/), [CopilotKit](https://copilotkit.ai), and Gemini.

## Prerequisites

- Google API Key (for Gemini)
- Auth0 account with application configured
- Python 3.13+
- uv
- Node.js 24+
- npm

## Environment Variables

### Web App (.env)

```
AUTH0_SECRET=<random-secret>
AUTH0_DOMAIN=<your-auth0-domain>
AUTH0_CLIENT_ID=<your-client-id>
AUTH0_CLIENT_SECRET=<your-client-secret>
APP_BASE_URL=https://your-domain.com
AGENT_URL=http://localhost:8000/
```

### Agent (agent/.env)

```
GOOGLE_API_KEY=<your-google-api-key>
```

## Development

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

This starts both the UI and agent servers concurrently.

## Production

### Docker Build

**Web (Next.js):**
```bash
docker build -t cavepedia-web .
docker run -p 3000:3000 \
  -e AUTH0_SECRET=<secret> \
  -e AUTH0_DOMAIN=<domain> \
  -e AUTH0_CLIENT_ID=<client-id> \
  -e AUTH0_CLIENT_SECRET=<client-secret> \
  -e APP_BASE_URL=https://your-domain.com \
  -e AGENT_URL=http://agent:8000/ \
  cavepedia-web
```

**Agent (PydanticAI):**
```bash
cd agent
docker build -t cavepedia-agent .
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=<api-key> \
  cavepedia-agent
```

### Without Docker

```bash
npm run build
npm run start:all
```

## Available Scripts

- `dev` - Starts both UI and agent servers in development mode
- `dev:ui` - Starts only the Next.js UI server
- `dev:agent` - Starts only the PydanticAI agent server
- `build` - Builds the Next.js application for production
- `start` - Starts the production Next.js server
- `start:agent` - Starts the production agent server
- `start:all` - Starts both servers in production mode
- `lint` - Runs ESLint

## Troubleshooting

### Agent Connection Issues
If you see connection errors:
1. Ensure the agent is running on port 8000
2. Check that GOOGLE_API_KEY is set correctly
3. Verify AGENT_URL has a trailing slash

### Python Dependencies
```bash
cd agent
uv sync
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

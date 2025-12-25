from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from psycopg.rows import dict_row
import cohere
import dotenv
import psycopg
import os
import json

# Load .env file if it exists (for local dev)
dotenv.load_dotenv()

# Required environment variables
COHERE_API_KEY = os.environ["COHERE_API_KEY"]

# Database config
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "cavepediav2_db")
DB_USER = os.environ.get("DB_USER", "cavepediav2_user")
DB_PASSWORD = os.environ["DB_PASSWORD"]

co = cohere.ClientV2(COHERE_API_KEY)
conn = psycopg.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    row_factory=dict_row,
)

mcp = FastMCP("Cavepedia MCP")

def get_user_roles() -> list[str]:
    """Extract user roles from the X-User-Roles header."""
    headers = get_http_headers()
    print(f"DEBUG: All headers received: {dict(headers)}")
    roles_header = headers.get("x-user-roles", "")
    print(f"DEBUG: x-user-roles header value: '{roles_header}'")
    if roles_header:
        try:
            roles = json.loads(roles_header)
            print(f"DEBUG: Parsed roles: {roles}")
            return roles
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decode error: {e}")
            return []
    print("DEBUG: No roles header found, returning empty list")
    return []

def embed(text, input_type):
    resp = co.embed(
        texts=[text],
        model='embed-v4.0',
        input_type=input_type,
        embedding_types=['float'],
    )
    assert resp.embeddings.float_ is not None
    return resp.embeddings.float_[0]

def search(query, roles: list[str], top_n: int = 3, max_content_length: int = 1500, priority_prefixes: list[str] | None = None) -> list[dict]:
    """Search with vector similarity, then rerank with Cohere for better relevance."""
    query_embedding = embed(query, 'search_query')

    if not roles:
        return []

    # Fetch more candidates for reranking
    candidate_limit = top_n * 4
    rows = conn.execute(
        'SELECT * FROM embeddings WHERE embedding IS NOT NULL AND role = ANY(%s) ORDER BY embedding <=> %s::vector LIMIT %s',
        (roles, query_embedding, candidate_limit)
    ).fetchall()

    if not rows:
        return []

    # Rerank with Cohere for better relevance
    rerank_resp = co.rerank(
        query=query,
        documents=[row['content'] or '' for row in rows],
        model='rerank-v3.5',
        top_n=min(top_n * 2, len(rows)),  # Get more for re-sorting after boost
    )

    # Build results with optional priority boost
    docs = []
    for result in rerank_resp.results:
        row = rows[result.index]
        score = result.relevance_score

        # Boost score if key starts with any priority prefix (e.g., 'nss/aca')
        if priority_prefixes:
            key = row['key'] or ''
            if any(key.startswith(prefix) for prefix in priority_prefixes):
                score = min(1.0, score * 1.3)  # 30% boost, capped at 1.0

        content = row['content'] or ''
        if len(content) > max_content_length:
            content = content[:max_content_length] + '...[truncated, use get_document_page for full text]'
        docs.append({'key': row['key'], 'content': content, 'relevance': round(score, 3)})

    # Re-sort by boosted score and return top_n
    docs.sort(key=lambda x: x['relevance'], reverse=True)
    return docs[:top_n]

@mcp.tool
def get_cave_location(cave: str, state: str, county: str) -> list[dict]:
    """Lookup cave location as coordinates."""
    roles = get_user_roles()
    return search(f'{cave} Location, latitude, Longitude. Located in {state} and {county} county.', roles)

@mcp.tool
def general_caving_information(query: str, priority_prefixes: list[str] | None = None) -> list[dict]:
    """General purpose search for any topic related to caves.

    Args:
        query: Search query
        priority_prefixes: Optional list of key prefixes to prioritize in results (e.g., ['nss/aca'] for rescue topics)
    """
    roles = get_user_roles()
    return search(query, roles, priority_prefixes=priority_prefixes)

@mcp.tool
def get_document_page(key: str) -> dict:
    """Fetch full content for a document page. Pass the exact 'key' value from search results."""
    roles = get_user_roles()
    if not roles:
        return {"error": "No roles assigned"}

    row = conn.execute(
        'SELECT key, content FROM embeddings WHERE key = %s AND role = ANY(%s)',
        (key, roles)
    ).fetchone()

    if row:
        return {"key": row["key"], "content": row["content"]}
    return {"error": f"Page not found: {key}"}

@mcp.tool
def get_user_info() -> dict:
    """Get information about the current user's roles."""
    roles = get_user_roles()
    return {
        "roles": roles,
    }

from starlette.responses import JSONResponse
from starlette.routing import Route

async def health(request):
    return JSONResponse({"status": "ok"})

app = mcp.http_app()
app.routes.append(Route("/health", health))

if __name__ == "__main__":
    mcp.run(transport='http', host='::1', port=9031)

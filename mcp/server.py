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
    roles_header = headers.get("x-user-roles", "")
    if roles_header:
        try:
            return json.loads(roles_header)
        except json.JSONDecodeError:
            return []
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

def search(query, roles: list[str]) -> list[dict]:
    query_embedding = embed(query, 'search_query')

    if not roles:
        # No roles = no results
        return []

    rows = conn.execute(
        'SELECT * FROM embeddings WHERE embedding IS NOT NULL AND role = ANY(%s) ORDER BY embedding <=> %s::vector LIMIT 5',
        (roles, query_embedding)
    ).fetchall()
    docs = []
    for row in rows:
        docs.append({ 'key': row['key'], 'content': row['content']})
    return docs

@mcp.tool
def get_cave_location(cave: str, state: str, county: str) -> list[dict]:
    """Lookup cave location as coordinates. Returns up to 5 matches, ordered by most to least relevant."""
    roles = get_user_roles()
    return search(f'{cave} Location, latitude, Longitude. Located in {state} and {county} county.', roles)

@mcp.tool
def general_caving_information(query: str) -> list[dict]:
    """General purpose endpoint for any topic related to caves. Returns up to 5 matches, ordered by most to least relevant."""
    roles = get_user_roles()
    return search(query, roles)

@mcp.tool
def get_document_page(document: str, page: int) -> dict:
    """Lookup a specific page of a document by its path and page number. Document should be the path like 'nss/compasstape/issue_20.pdf'."""
    roles = get_user_roles()
    if not roles:
        return {"error": "No roles assigned"}

    key = f"{document}/page-{page}.pdf"
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

if __name__ == "__main__":
    mcp.run(transport='http', host='::1', port=9031)
